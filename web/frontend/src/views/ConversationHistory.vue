<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search, View, Download, Delete } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'
import { useChatStore } from '@/stores/chatStore'
import type { ConversationSummary, Conversation } from '@/types/chat'

const chatStore = useChatStore()
const router = useRouter()

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

async function exportConversation(
  id: string,
  format: 'json' | 'markdown',
) {
  try {
    const res = await axios.get<Conversation>(`/api/v1/conversations/${id}`)
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
        `> 创建时间: ${formatDate(conv.created_at)}`,
        `> 更新时间: ${formatDate(conv.updated_at)}`,
        '',
        '---',
        '',
      ]
      for (const msg of conv.messages) {
        const roleLabel = msg.role === 'user' ? '**用户**' : '**助手**'
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
    ElMessage.success('导出成功')
  } catch {
    ElMessage.error('导出失败')
  }
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString('zh-CN')
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
          <span class="header-title">历史记录</span>
          <div class="header-actions">
            <el-input
              v-model="searchQuery"
              placeholder="搜索对话…"
              clearable
              size="small"
              style="width: 240px"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-button size="small" @click="handleRefresh">
              刷新
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
        <el-table-column prop="title" label="标题" min-width="200">
          <template #default="{ row }">
            <span class="conv-title-text">{{ row.title }}</span>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="更新时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.updated_at) }}
          </template>
        </el-table-column>
        <el-table-column
          prop="message_count"
          label="消息数"
          width="100"
          align="center"
        >
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.message_count }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" align="center">
          <template #default="{ row }">
            <el-space>
              <el-button
                size="small"
                type="primary"
                :icon="View"
                link
                @click.stop="openConversation(row)"
              >
                查看
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
                  导出
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
                删除
              </el-button>
            </el-space>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else-if="!loading" description="暂无历史记录" />
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
