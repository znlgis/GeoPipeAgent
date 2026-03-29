<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePipelineStore } from '@/stores/pipelineStore'
import type { StepNodeData, StepSchema, StepParamSchema } from '@/types/pipeline'

const store = usePipelineStore()
const { t } = useI18n()

const selectedNode = computed(() => {
  if (!store.selectedNodeId) return null
  return store.nodes.find((n) => n.id === store.selectedNodeId) ?? null
})

const nodeData = computed<StepNodeData | null>(() => {
  return (selectedNode.value?.data as StepNodeData) ?? null
})

const stepSchema = computed<StepSchema | null>(() => {
  if (!nodeData.value) return null
  return store.steps.find((s) => s.name === nodeData.value!.use) ?? null
})

const editableParams = computed<[string, StepParamSchema][]>(() => {
  if (!stepSchema.value) return []
  return Object.entries(stepSchema.value.params).filter(
    ([, schema]) => schema.type !== 'layer',
  )
})

const backendOptions = computed<string[]>(() => {
  const opts = ['auto']
  if (stepSchema.value?.backends) {
    opts.push(...stepSchema.value.backends)
  }
  return opts
})

function updateParam(key: string, value: any) {
  if (!store.selectedNodeId || !nodeData.value) return
  store.updateNodeData(store.selectedNodeId, {
    params: { ...nodeData.value.params, [key]: value },
  })
}

function updateField(field: keyof StepNodeData, value: any) {
  if (!store.selectedNodeId) return
  store.updateNodeData(store.selectedNodeId, { [field]: value })
}

function getParamValue(key: string): any {
  return nodeData.value?.params?.[key] ?? undefined
}

const statusText = computed<Record<string, string>>(() => ({
  idle: t('stepConfig.statusIdle'),
  running: t('stepConfig.statusRunning'),
  success: t('stepConfig.statusSuccess'),
  error: t('stepConfig.statusError'),
}))

const statusType: Record<string, string> = {
  idle: 'info',
  running: '',
  success: 'success',
  error: 'danger',
}
</script>

<template>
  <div class="step-config-panel">
    <!-- Placeholder when nothing selected -->
    <div v-if="!selectedNode || !nodeData" class="empty-state">
      <el-empty :description="t('stepConfig.selectNode')" :image-size="60" />
    </div>

    <!-- Config form -->
    <template v-else>
      <!-- Header -->
      <div class="panel-section">
        <div class="panel-label">{{ t('stepConfig.nodeId') }}</div>
        <el-input
          :model-value="selectedNode.id"
          size="small"
          disabled
        />
        <div class="panel-label" style="margin-top: 8px">{{ t('stepConfig.stepType') }}</div>
        <el-tag size="small" type="info">{{ nodeData.use }}</el-tag>
      </div>

      <el-divider />

      <!-- Dynamic params -->
      <div class="panel-section">
        <div class="section-title">{{ t('stepConfig.parameters') }}</div>

        <template v-if="editableParams.length > 0">
          <div
            v-for="[key, schema] in editableParams"
            :key="key"
            class="param-row"
          >
            <div class="param-label">
              <el-tooltip
                v-if="schema.description"
                :content="schema.description"
                placement="left"
              >
                <span>
                  {{ key }}
                  <span v-if="schema.required" class="required-mark">*</span>
                </span>
              </el-tooltip>
              <span v-else>
                {{ key }}
                <span v-if="schema.required" class="required-mark">*</span>
              </span>
            </div>

            <!-- Number -->
            <el-input-number
              v-if="schema.type === 'number'"
              :model-value="getParamValue(key)"
              size="small"
              controls-position="right"
              class="param-input"
              @update:model-value="(v: number | undefined) => updateParam(key, v)"
            />

            <!-- Enum / select -->
            <el-select
              v-else-if="schema.type === 'enum' || (schema.enum && schema.enum.length > 0)"
              :model-value="getParamValue(key)"
              size="small"
              class="param-input"
              @update:model-value="(v: string) => updateParam(key, v)"
            >
              <el-option
                v-for="opt in schema.enum"
                :key="opt"
                :label="opt"
                :value="opt"
              />
            </el-select>

            <!-- Boolean -->
            <el-switch
              v-else-if="schema.type === 'boolean'"
              :model-value="!!getParamValue(key)"
              size="small"
              @update:model-value="(v: boolean) => updateParam(key, v)"
            />

            <!-- String (default) -->
            <el-input
              v-else
              :model-value="getParamValue(key) ?? ''"
              size="small"
              class="param-input"
              :placeholder="schema.default != null ? String(schema.default) : ''"
              @update:model-value="(v: string) => updateParam(key, v)"
            />
          </div>
        </template>

        <el-text v-else type="info" size="small">{{ t('pipeline.noConfigurableParams') }}</el-text>
      </div>

      <el-divider />

      <!-- Advanced section -->
      <el-collapse class="advanced-collapse">
        <el-collapse-item :title="t('stepConfig.advanced')" name="advanced">
          <div class="param-row">
            <div class="param-label">{{ t('stepConfig.condition') }}</div>
            <el-input
              :model-value="nodeData.when ?? ''"
              size="small"
              placeholder="e.g. ${has_errors}"
              class="param-input"
              @update:model-value="(v: string) => updateField('when', v || undefined)"
            />
          </div>

          <div class="param-row">
            <div class="param-label">{{ t('stepConfig.errorStrategy') }}</div>
            <el-select
              :model-value="nodeData.onError ?? 'fail'"
              size="small"
              class="param-input"
              @update:model-value="(v: string) => updateField('onError', v)"
            >
              <el-option label="fail" value="fail" />
              <el-option label="skip" value="skip" />
              <el-option label="retry" value="retry" />
            </el-select>
          </div>

          <div v-if="stepSchema?.supports_backend" class="param-row">
            <div class="param-label">{{ t('stepConfig.backend') }}</div>
            <el-select
              :model-value="nodeData.backend ?? 'auto'"
              size="small"
              class="param-input"
              @update:model-value="(v: string) => updateField('backend', v)"
            >
              <el-option
                v-for="opt in backendOptions"
                :key="opt"
                :label="opt"
                :value="opt"
              />
            </el-select>
          </div>
        </el-collapse-item>
      </el-collapse>

      <el-divider />

      <!-- Execution status -->
      <div class="panel-section">
        <div class="section-title">{{ t('stepConfig.executionStatus') }}</div>
        <el-tag
          :type="(statusType[nodeData.status ?? 'idle'] as any) || 'info'"
          size="small"
        >
          {{ statusText[nodeData.status ?? 'idle'] }}
        </el-tag>
        <div v-if="nodeData.status === 'error' && nodeData.errorMessage" class="error-detail">
          <el-text type="danger" size="small">{{ nodeData.errorMessage }}</el-text>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.step-config-panel {
  padding: 4px;
  font-size: 13px;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
}

.panel-section {
  margin-bottom: 4px;
}

.panel-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}

.section-title {
  font-weight: 600;
  font-size: 13px;
  margin-bottom: 8px;
}

.param-row {
  margin-bottom: 12px;
}

.param-label {
  font-size: 12px;
  color: #606266;
  margin-bottom: 4px;
}

.required-mark {
  color: #f56c6c;
  margin-left: 2px;
}

.param-input {
  width: 100%;
}

.advanced-collapse {
  border: none;
}

.advanced-collapse :deep(.el-collapse-item__header) {
  font-size: 13px;
  height: 36px;
  line-height: 36px;
}

.error-detail {
  margin-top: 4px;
  padding: 6px 8px;
  background: #fef0f0;
  border-radius: 4px;
  word-break: break-word;
}
</style>
