<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useI18n } from 'vue-i18n'
import { Refresh, Delete, View } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'
import { useTaskStore } from '@/stores/taskStore'
import { formatDate } from '@/utils/format'
import MapPreview from '@/components/common/MapPreview.vue'
import type { TaskStatus } from '@/types/task'

const { t } = useI18n()
const taskStore = useTaskStore()

// Auto-refresh interval
let refreshTimer: ReturnType<typeof setInterval> | null = null

// Result dialog state
const showResultDialog = ref(false)
const resultTask = ref<TaskStatus | null>(null)
const resultGeoLayers = ref<any[]>([])
const resultLoading = ref(false)

onMounted(() => {
  taskStore.fetchTasks()
  // Auto-refresh every 5 seconds
  refreshTimer = setInterval(() => {
    taskStore.fetchTasks()
  }, 5000)
})

onBeforeUnmount(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
})

function getStatusType(status: string): 'info' | 'warning' | 'success' | 'danger' {
  switch (status) {
    case 'pending': return 'info'
    case 'running': return 'warning'
    case 'completed': return 'success'
    case 'failed': return 'danger'
    default: return 'info'
  }
}

function getStatusIcon(status: string): string {
  switch (status) {
    case 'pending': return '⏳'
    case 'running': return '⚙️'
    case 'completed': return '✅'
    case 'failed': return '❌'
    default: return '❓'
  }
}

function getStatusLabel(status: string): string {
  const key = `task.${status}` as const
  return t(key)
}

async function handleDelete(task: TaskStatus) {
  try {
    await ElMessageBox.confirm(t('task.confirmDelete'), t('task.deleteTask'), {
      confirmButtonText: t('common.confirm'),
      cancelButtonText: t('common.cancel'),
      type: 'warning',
    })
    const ok = await taskStore.deleteTask(task.id)
    if (ok) {
      ElMessage.success(t('task.deleted'))
    }
  } catch {
    // User cancelled
  }
}

async function handleViewResult(task: TaskStatus) {
  resultTask.value = task
  resultGeoLayers.value = []
  resultLoading.value = true
  showResultDialog.value = true

  try {
    const response = await axios.get(`/api/task/${task.id}/geodata`)
    if (response.data?.layers) {
      resultGeoLayers.value = response.data.layers
    }
  } catch {
    // No geodata available — will show raw JSON fallback
  } finally {
    resultLoading.value = false
  }
}

function handleRefresh() {
  taskStore.fetchTasks()
}
</script>

<template>
  <div class="task-manager">
    <!-- Header -->
    <div class="manager-header">
      <div class="header-text">
        <h2>{{ t('task.title') }}</h2>
        <p class="header-desc">{{ t('task.managerDesc') }}</p>
      </div>
      <div class="header-actions">
        <el-button :icon="Refresh" @click="handleRefresh">
          {{ t('task.refreshList') }}
        </el-button>
      </div>
    </div>

    <!-- Task Table -->
    <div v-if="taskStore.loading && taskStore.tasks.length === 0" class="loading-state">
      <el-skeleton :rows="5" animated />
    </div>

    <div v-else-if="taskStore.tasks.length === 0" class="empty-state">
      <p>{{ t('task.noTasks') }}</p>
    </div>

    <el-table
      v-else
      :data="taskStore.tasks"
      stripe
      class="task-table"
    >
      <el-table-column :label="t('task.taskId')" prop="id" width="160">
        <template #default="{ row }">
          <code class="task-id">{{ row.id }}</code>
        </template>
      </el-table-column>

      <el-table-column :label="t('task.type')" prop="type" width="160" />

      <el-table-column :label="t('task.status')" width="130">
        <template #default="{ row }">
          <el-tag :type="getStatusType(row.status)" size="small" effect="dark">
            {{ getStatusIcon(row.status) }} {{ getStatusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column :label="t('task.progress')" width="200">
        <template #default="{ row }">
          <el-progress
            :percentage="row.progress || 0"
            :status="row.status === 'completed' ? 'success' : row.status === 'failed' ? 'exception' : undefined"
            :stroke-width="14"
            :text-inside="true"
          />
        </template>
      </el-table-column>

      <el-table-column label="" min-width="200">
        <template #default="{ row }">
          <span v-if="row.message" class="task-message">{{ row.message }}</span>
          <span v-if="row.error" class="task-error">{{ row.error }}</span>
        </template>
      </el-table-column>

      <el-table-column :label="t('task.createdAt')" width="170">
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>

      <el-table-column :label="t('task.actions')" width="140" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="row.status === 'completed'"
            type="primary"
            size="small"
            :icon="View"
            text
            @click="handleViewResult(row)"
          />
          <el-button
            type="danger"
            size="small"
            :icon="Delete"
            text
            @click="handleDelete(row)"
          />
        </template>
      </el-table-column>
    </el-table>

    <!-- Result Viewer Dialog -->
    <el-dialog
      v-model="showResultDialog"
      :title="t('task.resultTitle')"
      width="800px"
      :close-on-click-modal="true"
    >
      <div v-if="resultLoading" class="result-loading">
        <el-skeleton :rows="4" animated />
      </div>
      <div v-else-if="resultTask" class="result-content">
        <!-- Spatial data visualization -->
        <div v-if="resultGeoLayers.length > 0" class="result-map">
          <MapPreview :layers="resultGeoLayers" :height="400" />
        </div>

        <!-- Raw result data -->
        <div class="result-raw">
          <h4>{{ t('task.rawResult') }}</h4>
          <pre class="result-json">{{ JSON.stringify(resultTask.result, null, 2) }}</pre>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.task-manager {
  max-width: 1200px;
  margin: 0 auto;
}

.manager-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
  gap: 16px;
}

.header-text h2 {
  margin: 0 0 4px;
  font-size: 20px;
  color: var(--gp-text-primary);
}

.header-desc {
  margin: 0;
  font-size: 13px;
  color: var(--gp-text-secondary);
}

.task-table {
  width: 100%;
}

.task-id {
  font-size: 12px;
  background: var(--gp-bg-secondary);
  padding: 2px 6px;
  border-radius: 3px;
  color: var(--gp-text-secondary);
}

.task-message {
  font-size: 13px;
  color: var(--gp-text-secondary);
}

.task-error {
  font-size: 13px;
  color: #f56c6c;
}

.loading-state,
.empty-state {
  padding: 60px 0;
  text-align: center;
  color: var(--gp-text-muted);
}

/* ── Result Dialog ── */
.result-loading {
  padding: 20px;
}

.result-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.result-map {
  border-radius: 8px;
  overflow: hidden;
}

.result-raw h4 {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--gp-text-primary);
}

.result-json {
  background: var(--gp-code-bg, #1e1e1e);
  color: #d4d4d4;
  padding: 16px;
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.5;
  overflow: auto;
  max-height: 300px;
  margin: 0;
}
</style>
