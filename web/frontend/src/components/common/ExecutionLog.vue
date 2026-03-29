<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { Delete } from '@element-plus/icons-vue'
import { usePipelineStore } from '@/stores/pipelineStore'

const pipelineStore = usePipelineStore()
const logContainerRef = ref<HTMLElement | null>(null)

const statusConfig = computed(() => {
  const map: Record<string, { label: string; type: 'info' | 'success' | 'warning' | 'danger'; icon: string }> = {
    idle: { label: '空闲', type: 'info', icon: '⏸' },
    running: { label: '运行中', type: 'warning', icon: '⏳' },
    done: { label: '完成', type: 'success', icon: '✅' },
    error: { label: '错误', type: 'danger', icon: '❌' },
  }
  return map[pipelineStore.executionStatus] ?? map.idle
})

function getLineClass(line: string): string {
  const lower = line.toLowerCase()
  if (lower.includes('成功') || lower.includes('success')) return 'log-success'
  if (lower.includes('错误') || lower.includes('error')) return 'log-error'
  if (lower.includes('运行') || lower.includes('running')) return 'log-running'
  return 'log-default'
}

function clearLog() {
  pipelineStore.executionLog = []
}

function scrollToBottom() {
  nextTick(() => {
    if (logContainerRef.value) {
      logContainerRef.value.scrollTop = logContainerRef.value.scrollHeight
    }
  })
}

watch(
  () => pipelineStore.executionLog.length,
  () => scrollToBottom(),
)
</script>

<template>
  <div class="execution-log">
    <!-- Header -->
    <div class="log-header">
      <div class="status-indicator">
        <el-tag :type="statusConfig.type" size="small" effect="dark">
          {{ statusConfig.icon }} {{ statusConfig.label }}
        </el-tag>
        <span class="title">执行日志</span>
      </div>
      <el-button
        size="small"
        :icon="Delete"
        :disabled="pipelineStore.executionLog.length === 0"
        @click="clearLog"
      >
        清除
      </el-button>
    </div>

    <!-- Log entries -->
    <div ref="logContainerRef" class="log-container">
      <div
        v-if="pipelineStore.executionLog.length === 0"
        class="log-empty"
      >
        暂无日志
      </div>
      <div
        v-for="(line, index) in pipelineStore.executionLog"
        :key="index"
        class="log-line"
        :class="getLineClass(line)"
      >
        <span class="line-number">{{ index + 1 }}</span>
        <span class="line-content">{{ line }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.execution-log {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border-bottom: 1px solid #e4e7ed;
  background: #fafafa;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
}

.title {
  font-size: 13px;
  font-weight: 600;
  color: #606266;
}

.log-container {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
  background: #1e1e1e;
  font-family: 'Fira Code', 'Consolas', monospace;
  font-size: 12px;
  line-height: 1.6;
}

.log-empty {
  padding: 24px;
  text-align: center;
  color: #909399;
}

.log-line {
  display: flex;
  padding: 1px 12px;
}
.log-line:hover {
  background: rgba(255, 255, 255, 0.05);
}

.line-number {
  display: inline-block;
  min-width: 32px;
  text-align: right;
  margin-right: 12px;
  color: #606266;
  user-select: none;
}

.line-content {
  white-space: pre-wrap;
  word-break: break-all;
}

/* Log level colours */
.log-success .line-content {
  color: #67c23a;
}
.log-error .line-content {
  color: #f56c6c;
}
.log-running .line-content {
  color: #409eff;
}
.log-default .line-content {
  color: #d4d4d4;
}
</style>
