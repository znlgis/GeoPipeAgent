<script setup lang="ts">
import { computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'
import type { StepNodeData } from '@/types/pipeline'

const props = defineProps<{
  id: string
  data: StepNodeData
}>()

const categoryColors: Record<string, string> = {
  io: '#409eff',
  vector: '#67c23a',
  raster: '#e6a23c',
  analysis: '#9b59b6',
  network: '#00bcd4',
  qc: '#f56c6c',
}

const category = computed(() => {
  const use = props.data.use ?? ''
  return use.split('.')[0]?.split('/')[0]?.split('_')[0]?.toLowerCase() ?? ''
})

const headerColor = computed(() => categoryColors[category.value] ?? '#909399')

const statusColor = computed(() => {
  const statusMap: Record<string, string> = {
    idle: '#c0c4cc',
    running: '#409eff',
    success: '#67c23a',
    error: '#f56c6c',
  }
  return statusMap[props.data.status ?? 'idle'] ?? '#c0c4cc'
})

const isRunning = computed(() => props.data.status === 'running')
</script>

<template>
  <div class="step-node">
    <div class="step-node__header" :style="{ backgroundColor: headerColor }">
      <span class="step-node__label">{{ data.label }}</span>
      <span class="step-node__status" :class="{ spinning: isRunning }">
        <span class="status-dot" :style="{ backgroundColor: statusColor }" />
      </span>
    </div>

    <div class="step-node__body">
      <span class="step-node__use">{{ data.use }}</span>
      <div v-if="data.status === 'error' && data.errorMessage" class="step-node__error">
        {{ data.errorMessage }}
      </div>
    </div>

    <Handle
      id="input"
      type="target"
      :position="Position.Top"
      class="step-node__handle"
    />
    <Handle
      id="output"
      type="source"
      :position="Position.Bottom"
      class="step-node__handle"
    />
  </div>
</template>

<style scoped>
.step-node {
  width: 180px;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
  overflow: hidden;
  font-size: 12px;
}

.step-node__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  color: #fff;
}

.step-node__label {
  font-weight: 600;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.step-node__status {
  display: inline-flex;
  align-items: center;
  margin-left: 6px;
  flex-shrink: 0;
}

.status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.spinning .status-dot {
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(0.75); }
}

.step-node__body {
  padding: 8px 10px;
}

.step-node__use {
  color: #909399;
  font-size: 11px;
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.step-node__error {
  margin-top: 4px;
  padding: 4px 6px;
  background: #fef0f0;
  color: #f56c6c;
  border-radius: 4px;
  font-size: 10px;
  line-height: 1.3;
  word-break: break-word;
}

.step-node__handle {
  width: 10px;
  height: 10px;
  background: #409eff;
  border: 2px solid #fff;
}
</style>
