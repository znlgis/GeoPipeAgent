<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, Delete } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useChatStore } from '@/stores/chatStore'
import ChatWindow from '@/components/chat/ChatWindow.vue'

const router = useRouter()
const chatStore = useChatStore()

const searchQuery = ref('')

const filteredConversations = computed(() => {
  const q = searchQuery.value.toLowerCase().trim()
  if (!q) return chatStore.conversations
  return chatStore.conversations.filter((c) =>
    c.title.toLowerCase().includes(q),
  )
})

onMounted(() => {
  chatStore.fetchConversations()
})

async function createConversation() {
  try {
    // Create a new conversation via the backend
    const res = await import('axios').then((m) =>
      m.default.post('/api/v1/conversations', { title: '新对话' }),
    )
    const newConv = res.data
    await chatStore.fetchConversations()
    await chatStore.loadConversation(newConv.id)
  } catch {
    // Fallback: set an empty current conversation locally
    chatStore.currentConversation = {
      id: `local-${Date.now()}`,
      title: '新对话',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      config: {},
      messages: [],
    }
    ElMessage.info('已创建本地对话')
  }
}

function selectConversation(id: string) {
  chatStore.loadConversation(id)
}

async function handleDelete(id: string, event: Event) {
  event.stopPropagation()
  try {
    await ElMessageBox.confirm('确定要删除此对话吗？', '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await chatStore.deleteConversation(id)
    ElMessage.success('已删除')
  } catch {
    // User cancelled
  }
}

function handleLoadPipeline(yaml: string) {
  // Navigate to the editor and load the YAML
  router.push('/').then(() => {
    // The pipeline store is shared; import it and load
    import('@/stores/pipelineStore').then(({ usePipelineStore }) => {
      const pipelineStore = usePipelineStore()
      pipelineStore.loadFromYaml(yaml)
      ElMessage.success('流水线已加载到编辑器')
    })
  })
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<template>
  <el-container class="llm-chat">
    <!-- Left sidebar: conversation list -->
    <el-aside width="280px" class="conversation-sidebar">
      <div class="sidebar-header">
        <el-button type="primary" :icon="Plus" @click="createConversation">
          新建对话
        </el-button>
      </div>
      <el-input
        v-model="searchQuery"
        placeholder="搜索对话…"
        clearable
        size="small"
        class="sidebar-search"
      />
      <div v-if="filteredConversations.length > 0" class="conversation-list">
        <div
          v-for="conv in filteredConversations"
          :key="conv.id"
          class="conversation-item"
          :class="{ active: chatStore.currentConversation?.id === conv.id }"
          @click="selectConversation(conv.id)"
        >
          <div class="conv-title">{{ conv.title }}</div>
          <div class="conv-meta">
            <span>{{ conv.message_count }} 条消息</span>
            <span>{{ formatDate(conv.updated_at) }}</span>
          </div>
          <el-button
            class="conv-delete"
            :icon="Delete"
            size="small"
            text
            type="danger"
            @click="handleDelete(conv.id, $event)"
          />
        </div>
      </div>
      <el-empty v-else description="暂无对话" :image-size="60" />
    </el-aside>

    <!-- Main area: chat window -->
    <el-main class="chat-main">
      <ChatWindow @load-pipeline="handleLoadPipeline" />
    </el-main>
  </el-container>
</template>

<style scoped>
.llm-chat {
  height: calc(100vh - 100px);
}

.conversation-sidebar {
  background: #fff;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
  overflow: hidden;
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

.conversation-item {
  position: relative;
  padding: 10px 12px;
  margin-bottom: 4px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
}

.conversation-item:hover {
  background: #f5f7fa;
}

.conversation-item.active {
  background: #ecf5ff;
}

.conv-title {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  padding-right: 28px;
}

.conv-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.conv-delete {
  position: absolute;
  top: 8px;
  right: 4px;
  opacity: 0;
  transition: opacity 0.15s;
}

.conversation-item:hover .conv-delete {
  opacity: 1;
}

.chat-main {
  padding: 0;
  overflow: hidden;
}
</style>
