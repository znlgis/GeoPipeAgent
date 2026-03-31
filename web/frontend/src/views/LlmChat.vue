<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Plus, Delete, Edit } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useChatStore } from '@/stores/chatStore'
import { formatDate } from '@/utils/format'
import ChatWindow from '@/components/chat/ChatWindow.vue'
import axios from 'axios'

const router = useRouter()
const route = useRoute()
const chatStore = useChatStore()
const { t } = useI18n()

const searchQuery = ref('')
const pendingPrompt = ref('')
const pendingMode = ref<'chat' | 'pipeline'>('chat')

const filteredConversations = computed(() => {
  const q = searchQuery.value.toLowerCase().trim()
  if (!q) return chatStore.conversations
  return chatStore.conversations.filter((c) =>
    c.title.toLowerCase().includes(q),
  )
})

onMounted(async () => {
  await chatStore.fetchConversations()

  // Handle query params from template "Try with AI" navigation
  const queryPrompt = route.query.prompt as string | undefined
  const queryMode = route.query.mode as string | undefined
  if (queryPrompt) {
    // Create a new conversation and pre-fill the prompt
    await createConversation()
    if (chatStore.currentConversation) {
      // Set mode and auto-send via ChatWindow ref
      pendingPrompt.value = queryPrompt
      pendingMode.value = queryMode === 'generate' ? 'pipeline' : 'chat'
    }
    // Clean query params from URL to avoid re-trigger on navigation
    router.replace({ path: '/chat' })
  }
})

async function createConversation() {
  try {
    const res = await axios.post('/api/llm/conversations', { title: t('chat.newConversation') })
    const newConv = res.data
    await chatStore.fetchConversations()
    await chatStore.loadConversation(newConv.id)
  } catch {
    chatStore.currentConversation = {
      id: `local-${Date.now()}`,
      title: t('chat.newConversation'),
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      config: {},
      messages: [],
    }
    ElMessage.info(t('chat.localCreated'))
  }
}

function selectConversation(id: string) {
  chatStore.loadConversation(id)
}

async function handleDelete(id: string, event: Event) {
  event.stopPropagation()
  try {
    await ElMessageBox.confirm(t('chat.confirmDelete'), t('chat.confirmDeleteTitle'), {
      confirmButtonText: t('common.delete'),
      cancelButtonText: t('common.cancel'),
      type: 'warning',
    })
    await chatStore.deleteConversation(id)
    ElMessage.success(t('chat.deleted'))
  } catch {
    // User cancelled
  }
}

async function handleRename(id: string, currentTitle: string, event: Event) {
  event.stopPropagation()
  try {
    const { value } = await ElMessageBox.prompt(t('chat.enterTitle'), t('chat.renameConversation'), {
      confirmButtonText: t('common.confirm'),
      cancelButtonText: t('common.cancel'),
      inputValue: currentTitle,
      inputPattern: /\S+/,
      inputErrorMessage: t('chat.enterTitle'),
    })
    if (value && value.trim()) {
      await axios.patch(`/api/llm/conversations/${id}`, { title: value.trim() })
      await chatStore.fetchConversations()
      if (chatStore.currentConversation?.id === id) {
        chatStore.currentConversation.title = value.trim()
      }
      ElMessage.success(t('chat.renameSuccess'))
    }
  } catch {
    // User cancelled or API error
  }
}

function handleLoadPipeline(yaml: string) {
  router.push('/').then(() => {
    import('@/stores/pipelineStore').then(({ usePipelineStore }) => {
      const pipelineStore = usePipelineStore()
      pipelineStore.loadFromYaml(yaml)
      ElMessage.success(t('pipeline.loadedSuccess'))
    })
  })
}
</script>

<template>
  <el-container class="llm-chat">
    <!-- Left sidebar: conversation list -->
    <el-aside width="280px" class="conversation-sidebar">
      <div class="sidebar-header">
        <el-button type="primary" :icon="Plus" @click="createConversation">
          {{ t('chat.newConversation') }}
        </el-button>
      </div>
      <el-input
        v-model="searchQuery"
        :placeholder="t('chat.searchConversations')"
        clearable
        size="small"
        class="sidebar-search"
      />
      <div v-if="filteredConversations.length > 0" class="conversation-list">
        <TransitionGroup name="list-fade">
          <div
            v-for="conv in filteredConversations"
            :key="conv.id"
            class="conversation-item"
            :class="{ active: chatStore.currentConversation?.id === conv.id }"
            @click="selectConversation(conv.id)"
          >
            <div class="conv-title">{{ conv.title }}</div>
            <div class="conv-meta">
              <span>{{ conv.message_count }} {{ t('chat.messages') }}</span>
              <span>{{ formatDate(conv.updated_at) }}</span>
            </div>
            <div class="conv-actions">
              <el-button
                class="conv-action-btn"
                :icon="Edit"
                size="small"
                text
                @click="handleRename(conv.id, conv.title, $event)"
              />
              <el-button
                class="conv-action-btn conv-delete"
                :icon="Delete"
                size="small"
                text
                type="danger"
                @click="handleDelete(conv.id, $event)"
              />
            </div>
          </div>
        </TransitionGroup>
      </div>
      <el-empty v-else :description="t('chat.noConversations')" :image-size="60" />
    </el-aside>

    <!-- Main area: chat window -->
    <el-main class="chat-main">
      <ChatWindow
        :initial-prompt="pendingPrompt"
        :initial-mode="pendingMode"
        @load-pipeline="handleLoadPipeline"
      />
    </el-main>
  </el-container>
</template>

<style scoped>
.llm-chat {
  height: calc(100vh - 88px);
}

.conversation-sidebar {
  background: var(--gp-bg-primary);
  border-right: 1px solid var(--gp-border-color);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: background var(--gp-transition), border-color var(--gp-transition);
}

.sidebar-header {
  padding: 12px;
  flex-shrink: 0;
}

.sidebar-header .el-button {
  width: 100%;
}

.sidebar-search {
  padding: 0 12px 8px;
  flex-shrink: 0;
}

.conversation-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 8px;
}

/* List transition */
.list-fade-enter-active,
.list-fade-leave-active {
  transition: all 0.25s ease;
}
.list-fade-enter-from,
.list-fade-leave-to {
  opacity: 0;
  transform: translateX(-12px);
}

.conversation-item {
  position: relative;
  padding: 10px 12px;
  margin-bottom: 4px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
}

.conversation-item:hover {
  background: var(--gp-hover-bg);
}

.conversation-item.active {
  background: var(--gp-active-bg);
}

.conv-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--gp-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  padding-right: 56px;
}

.conv-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--gp-text-muted);
  margin-top: 4px;
}

.conv-actions {
  position: absolute;
  top: 8px;
  right: 4px;
  display: flex;
  gap: 0;
  opacity: 0;
  transition: opacity 0.15s;
}

.conversation-item:hover .conv-actions {
  opacity: 1;
}

.conv-action-btn {
  padding: 4px;
}

.chat-main {
  padding: 0;
  overflow: hidden;
}
</style>
