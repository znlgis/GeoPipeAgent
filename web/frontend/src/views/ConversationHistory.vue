<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useChatStore } from '@/stores/chatStore'

const chatStore = useChatStore()
const router = useRouter()

onMounted(() => {
  chatStore.fetchConversations()
})

function openConversation(id: string) {
  chatStore.loadConversation(id)
  router.push('/chat')
}

function handleDelete(id: string) {
  chatStore.deleteConversation(id)
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString('zh-CN')
}
</script>

<template>
  <div class="conversation-history">
    <el-card shadow="never">
      <template #header>
        <div class="header">
          <span>历史记录</span>
          <el-button size="small" @click="chatStore.fetchConversations()">
            刷新
          </el-button>
        </div>
      </template>
      <el-table
        v-if="chatStore.conversations.length > 0"
        :data="chatStore.conversations"
        stripe
        style="width: 100%"
      >
        <el-table-column prop="title" label="标题" min-width="200" />
        <el-table-column prop="message_count" label="消息数" width="100" align="center" />
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
        <el-table-column label="操作" width="160" align="center">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="openConversation(row.id)">
              打开
            </el-button>
            <el-popconfirm title="确定要删除吗？" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button size="small" type="danger" link>删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else description="暂无历史记录" />
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
</style>
