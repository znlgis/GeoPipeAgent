<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Search, View, Download, Delete } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'
import { useChatStore } from '@/stores/chatStore'
import { formatDate } from '@/utils/format'
import type { ConversationSummary, Conversation } from '@/types/chat'

const chatStore = useChatStore()
const router = useRouter()
const { t } = useI18n()

const searchQuery = ref('')
const loading = ref(false)

const filteredConversations = computed(() => {
  const q = searchQuery.value.toLowerCase().trim()
  if (!q) return chatStore.conversations
  return chatStore.conversations.filter((c) =>
    c.title.toLowerCase().includes(q),
  )
})

onMounted(async () => {
  loading.value = true
  await chatStore.fetchConversations()
  loading.value = false
})

function openConversation(row: ConversationSummary) {
  chatStore.loadConversation(row.id)
  router.push('/chat')
}

async function handleDelete(id: string) {
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

async function exportConversation(
  id: string,
  format: 'json' | 'markdown',
) {
  try {
    const res = await axios.get<Conversation>(`/api/llm/conversations/${id}`)
    const conv = res.data
    let content: string
    let mimeType: string
    let ext: string

    if (format === 'json') {
      content = JSON.stringify(conv, null, 2)
      mimeType = 'application/json;charset=utf-8'
      ext = 'json'
    } else {
      const lines: string[] = [
        `# ${conv.title}`,
        '',
        `> ${t('history.markdownCreatedAt')}: ${formatDate(conv.created_at)}`,
        `> ${t('history.markdownUpdatedAt')}: ${formatDate(conv.updated_at)}`,
        '',
        '---',
        '',
      ]
      for (const msg of conv.messages) {
        const roleLabel = msg.role === 'user' ? t('history.userLabel') : t('history.assistantLabel')
        lines.push(`### ${roleLabel}`)
        lines.push('')
        lines.push(msg.content)
        lines.push('')
      }
      content = lines.join('\n')
      mimeType = 'text/markdown;charset=utf-8'
      ext = 'md'
    }

    const blob = new Blob([content], { type: mimeType })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${conv.title || 'conversation'}.${ext}`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success(t('history.exportSuccess'))
  } catch {
    ElMessage.error(t('history.exportFailed'))
  }
}

function handleRowClick(row: ConversationSummary) {
  openConversation(row)
}

async function handleRefresh() {
  loading.value = true
  await chatStore.fetchConversations()
  loading.value = false
}
</script>

<template>
  <div class="conversation-history">
    <el-card shadow="never">
      <template #header>
        <div class="header">
          <span class="header-title">{{ t('history.title') }}</span>
          <div class="header-actions">
            <el-input
              v-model="searchQuery"
              :placeholder="t('chat.searchConversations')"
              clearable
              size="small"
              style="width: 240px"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-button size="small" @click="handleRefresh">
              {{ t('common.refresh') }}
            </el-button>
          </div>
        </div>
      </template>

      <el-table
        v-if="filteredConversations.length > 0"
        v-loading="loading"
        :data="filteredConversations"
        stripe
        style="width: 100%"
        @row-click="handleRowClick"
        class="clickable-table"
      >
        <el-table-column prop="title" :label="t('history.tableTitle')" min-width="200">
          <template #default="{ row }">
            <span class="conv-title-text">{{ row.title }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="t('history.createdAt')" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column :label="t('history.updatedAt')" width="180">
          <template #default="{ row }">
            {{ formatDate(row.updated_at) }}
          </template>
        </el-table-column>
        <el-table-column
          prop="message_count"
          :label="t('history.messageCount')"
          width="100"
          align="center"
        >
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.message_count }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('history.actions')" width="240" align="center">
          <template #default="{ row }">
            <el-space>
              <el-button
                size="small"
                type="primary"
                :icon="View"
                link
                @click.stop="openConversation(row)"
              >
                {{ t('common.view') }}
              </el-button>
              <el-dropdown
                trigger="click"
                @command="(cmd: string) => exportConversation(row.id, cmd as 'json' | 'markdown')"
              >
                <el-button
                  size="small"
                  :icon="Download"
                  link
                  @click.stop
                >
                  {{ t('common.export') }}
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="json">JSON</el-dropdown-item>
                    <el-dropdown-item command="markdown">
                      Markdown
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
              <el-button
                size="small"
                type="danger"
                :icon="Delete"
                link
                @click.stop="handleDelete(row.id)"
              >
                {{ t('common.delete') }}
              </el-button>
            </el-space>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else-if="!loading" :description="t('history.noHistory')" />
    </el-card>
  </div>
</template>

<style scoped>
.conversation-history {
  max-width: 1200px;
  margin: 0 auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-title {
  font-size: 16px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.clickable-table :deep(.el-table__row) {
  cursor: pointer;
}

.conv-title-text {
  font-weight: 500;
}
</style>
