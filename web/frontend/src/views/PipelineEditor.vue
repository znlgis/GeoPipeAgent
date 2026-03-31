<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import {
  VideoPlay,
  CircleCheck,
  FolderOpened,
  MagicStick,
  Upload,
  Download,
  DArrowLeft,
  DArrowRight,
  ArrowDown,
  ArrowUp,
  Timer,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { usePipelineStore } from '@/stores/pipelineStore'
import { useChatStore } from '@/stores/chatStore'
import { useTaskStore } from '@/stores/taskStore'
import { useFlowEditor } from '@/composables/useFlowEditor'
import FlowCanvas from '@/components/flow/FlowCanvas.vue'
import StepConfigPanel from '@/components/flow/StepConfigPanel.vue'
import NodePalette from '@/components/flow/NodePalette.vue'
import ExecutionLog from '@/components/common/ExecutionLog.vue'
import YamlPreview from '@/components/common/YamlPreview.vue'
import MapPreview from '@/components/common/MapPreview.vue'

const router = useRouter()
const pipelineStore = usePipelineStore()
const chatStore = useChatStore()
const taskStore = useTaskStore()
const { t } = useI18n()
const {
  isExecuting,
  showAiDialog,
  aiPrompt,
  executePipeline,
  validatePipeline,
  savePipeline,
  loadFromYaml,
  importYamlFile,
  exportYamlFile,
} = useFlowEditor()

const showSaveDialog = ref(false)
const saveName = ref('')
const activeBottomTab = ref('log')
const fileInputRef = ref<HTMLInputElement | null>(null)
const aiGenerating = ref(false)
const isSubmittingBackground = ref(false)

// Extract GeoJSON from execution result (if it contains spatial data)
const executionGeoJson = computed<Record<string, any> | null>(() => {
  const result = pipelineStore.executionResult
  if (!result) return null
  // Check if result itself is GeoJSON
  if (result.type === 'FeatureCollection' || result.type === 'Feature') return result
  // Check common nested locations
  if (result.geojson) return result.geojson
  if (result.geodata) return result.geodata
  if (result.output?.type === 'FeatureCollection') return result.output
  return null
})

// Auto-switch to map tab when GeoJSON becomes available
watch(executionGeoJson, (val) => {
  if (val) {
    showBottom.value = true
    activeBottomTab.value = 'map'
  }
})

// --- Panel collapse states ---
const showPalette = ref(true)
const showConfig = ref(true)
const showBottom = ref(true)

// --- Resizable bottom panel ---
const bottomPanelHeight = ref(200)
const isResizing = ref(false)
const resizeStartY = ref(0)
const resizeStartH = ref(0)
const MIN_BOTTOM_H = 100
const MAX_BOTTOM_H = 500

function startResize(event: MouseEvent) {
  isResizing.value = true
  resizeStartY.value = event.clientY
  resizeStartH.value = bottomPanelHeight.value
  document.addEventListener('mousemove', onResizeMove)
  document.addEventListener('mouseup', stopResize)
  document.body.style.cursor = 'row-resize'
  document.body.style.userSelect = 'none'
}

function onResizeMove(event: MouseEvent) {
  if (!isResizing.value) return
  const delta = resizeStartY.value - event.clientY
  const newHeight = Math.min(MAX_BOTTOM_H, Math.max(MIN_BOTTOM_H, resizeStartH.value + delta))
  bottomPanelHeight.value = newHeight
}

function stopResize() {
  isResizing.value = false
  document.removeEventListener('mousemove', onResizeMove)
  document.removeEventListener('mouseup', stopResize)
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
}

// --- Status bar info ---
const statusText = computed(() => {
  return t('pipeline.statusBar', {
    steps: pipelineStore.nodes.length,
    edges: pipelineStore.edges.length,
  })
})

const pipelineName = computed(() => {
  return pipelineStore.meta.name || t('pipeline.noPipeline')
})

onMounted(() => {
  pipelineStore.fetchSteps()
  document.addEventListener('keydown', handleGlobalKeydown)
})

onBeforeUnmount(() => {
  clearAiPoll()
  document.removeEventListener('keydown', handleGlobalKeydown)
})

// --- Keyboard shortcuts ---
function handleGlobalKeydown(event: KeyboardEvent) {
  const isCtrl = event.ctrlKey || event.metaKey
  if (isCtrl && event.key === 's') {
    event.preventDefault()
    handleOpenSave()
  } else if (isCtrl && event.key === 'Enter') {
    event.preventDefault()
    handleRun()
  } else if (isCtrl && event.key === 'b') {
    event.preventDefault()
    showPalette.value = !showPalette.value
  } else if (isCtrl && event.key === 'j') {
    event.preventDefault()
    showBottom.value = !showBottom.value
  }
}

async function handleRun() {
  await executePipeline()
  showBottom.value = true
  activeBottomTab.value = 'log'
}

async function handleSubmitBackground() {
  const yaml = pipelineStore.exportToYaml()
  if (!yaml) {
    ElMessage.warning(t('pipeline.empty'))
    return
  }
  isSubmittingBackground.value = true
  try {
    const result = await taskStore.submitTask(yaml)
    if (result) {
      ElMessage.success(t('task.submitted', { id: result.task_id }))
    }
  } finally {
    isSubmittingBackground.value = false
  }
}

function goToTemplates() {
  router.push('/templates')
}

async function handleValidate() {
  const result = await validatePipeline()
  if (result.valid) {
    ElMessage.success(t('pipeline.validationSuccess'))
  } else {
    ElMessage.error(result.errors.join('; '))
  }
}

function handleOpenSave() {
  saveName.value = pipelineStore.meta.name || ''
  showSaveDialog.value = true
}

async function handleSave() {
  if (!saveName.value.trim()) {
    ElMessage.warning(t('pipeline.enterName'))
    return
  }
  try {
    await savePipeline(saveName.value.trim())
    ElMessage.success(t('pipeline.savedSuccess'))
    showSaveDialog.value = false
  } catch {
    ElMessage.error(t('pipeline.saveFailed'))
  }
}

function handleImportClick() {
  fileInputRef.value?.click()
}

async function handleFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  try {
    await importYamlFile(file)
    ElMessage.success(t('pipeline.importSuccess'))
  } catch {
    ElMessage.error(t('pipeline.importFailed'))
  }
  input.value = ''
}

function handleExport() {
  exportYamlFile()
}

async function handleAiGenerate() {
  const prompt = aiPrompt.value.trim()
  if (!prompt) {
    ElMessage.warning(t('pipeline.enterPrompt'))
    return
  }
  aiGenerating.value = true
  chatStore.generatePipeline(prompt)

  aiPollTimer = setInterval(() => {
    if (!chatStore.isStreaming) {
      clearAiPoll()
      aiGenerating.value = false
      const yaml = chatStore.streamingContent || extractYamlFromContent()
      if (yaml) {
        loadFromYaml(yaml)
        ElMessage.success(t('pipeline.aiLoadedSuccess'))
        showAiDialog.value = false
        aiPrompt.value = ''
      } else {
        ElMessage.warning(t('pipeline.noValidYaml'))
      }
    }
  }, 300)
}

let aiPollTimer: ReturnType<typeof setInterval> | null = null
function clearAiPoll() {
  if (aiPollTimer) {
    clearInterval(aiPollTimer)
    aiPollTimer = null
  }
}

function extractYamlFromContent(): string {
  const conv = chatStore.currentConversation
  if (!conv?.messages.length) return ''
  const lastMsg = conv.messages[conv.messages.length - 1]
  if (lastMsg.role !== 'assistant') return ''
  const content = lastMsg.content
  const yamlMatch = content.match(/```ya?ml\n([\s\S]*?)```/)
  return yamlMatch ? yamlMatch[1].trim() : content
}

function handleLoadYaml(yaml: string) {
  loadFromYaml(yaml)
}
</script>

<template>
  <el-container direction="vertical" class="pipeline-editor">
    <!-- Toolbar -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-tooltip :content="t('pipeline.runTooltip')" placement="bottom" :show-after="500">
          <el-button
            type="primary"
            :icon="VideoPlay"
            :loading="isExecuting"
            @click="handleRun"
          >
            {{ t('pipeline.run') }}
          </el-button>
        </el-tooltip>
        <el-tooltip :content="t('pipeline.validateTooltip')" placement="bottom" :show-after="500">
          <el-button :icon="CircleCheck" @click="handleValidate">
            {{ t('pipeline.validate') }}
          </el-button>
        </el-tooltip>

        <el-divider direction="vertical" />

        <el-tooltip :content="t('pipeline.saveTooltip')" placement="bottom" :show-after="500">
          <el-button :icon="FolderOpened" @click="handleOpenSave">
            {{ t('common.save') }}
          </el-button>
        </el-tooltip>
        <el-tooltip :content="t('pipeline.aiGenerateTooltip')" placement="bottom" :show-after="500">
          <el-button :icon="MagicStick" @click="showAiDialog = true">
            {{ t('pipeline.aiGenerate') }}
          </el-button>
        </el-tooltip>

        <el-divider direction="vertical" />

        <el-tooltip :content="t('pipeline.importTooltip')" placement="bottom" :show-after="500">
          <el-button :icon="Upload" @click="handleImportClick">
            {{ t('common.import') }}
          </el-button>
        </el-tooltip>
        <el-tooltip :content="t('pipeline.exportTooltip')" placement="bottom" :show-after="500">
          <el-button :icon="Download" @click="handleExport">
            {{ t('common.export') }}
          </el-button>
        </el-tooltip>

        <el-divider direction="vertical" />

        <el-tooltip :content="t('task.submitTooltip')" placement="bottom" :show-after="500">
          <el-button :icon="Timer" :loading="isSubmittingBackground" @click="handleSubmitBackground">
            {{ t('task.submit') }}
          </el-button>
        </el-tooltip>
      </div>

      <div class="toolbar-right">
        <!-- Panel toggle buttons -->
        <el-tooltip
          :content="showPalette ? t('pipeline.collapsePalette') : t('pipeline.expandPalette')"
          placement="bottom"
          :show-after="500"
        >
          <el-button
            :icon="showPalette ? DArrowLeft : DArrowRight"
            size="small"
            text
            @click="showPalette = !showPalette"
          />
        </el-tooltip>
        <el-tooltip
          :content="showConfig ? t('pipeline.collapseConfig') : t('pipeline.expandConfig')"
          placement="bottom"
          :show-after="500"
        >
          <el-button
            :icon="showConfig ? DArrowRight : DArrowLeft"
            size="small"
            text
            @click="showConfig = !showConfig"
          />
        </el-tooltip>
        <el-tooltip
          :content="showBottom ? t('pipeline.collapseBottom') : t('pipeline.expandBottom')"
          placement="bottom"
          :show-after="500"
        >
          <el-button
            :icon="showBottom ? ArrowDown : ArrowUp"
            size="small"
            text
            @click="showBottom = !showBottom"
          />
        </el-tooltip>
      </div>
      <input
        ref="fileInputRef"
        type="file"
        accept=".yaml,.yml"
        class="hidden-file-input"
        @change="handleFileChange"
      />
    </div>

    <!-- Middle section: palette + canvas + config -->
    <el-container class="editor-middle">
      <transition name="slide-left">
        <el-aside v-show="showPalette" width="240px" class="palette-aside">
          <NodePalette />
        </el-aside>
      </transition>
      <el-main class="canvas-main">
        <FlowCanvas />
        <!-- Empty state guidance overlay -->
        <div v-if="pipelineStore.nodes.length === 0" class="canvas-empty-state">
          <div class="empty-state-card">
            <div class="empty-icon">🚀</div>
            <h3 class="empty-title">{{ t('emptyState.title') }}</h3>
            <div class="empty-hints">
              <p>📋 {{ t('emptyState.hint1') }}</p>
              <p>🤖 {{ t('emptyState.hint2') }}</p>
              <p>📦 {{ t('emptyState.hint3') }}</p>
            </div>
            <el-button type="primary" size="small" @click="goToTemplates">
              {{ t('emptyState.browseTemplates') }}
            </el-button>
          </div>
        </div>
      </el-main>
      <transition name="slide-right">
        <el-aside v-show="showConfig" width="300px" class="config-aside">
          <StepConfigPanel />
        </el-aside>
      </transition>
    </el-container>

    <!-- Bottom section: resizable tabs -->
    <template v-if="showBottom">
      <div class="resize-handle" @mousedown="startResize">
        <div class="resize-bar" />
      </div>
      <div class="bottom-panel" :style="{ height: bottomPanelHeight + 'px' }">
        <el-tabs v-model="activeBottomTab" class="bottom-tabs">
          <el-tab-pane :label="t('pipeline.executionLog')" name="log">
            <ExecutionLog />
          </el-tab-pane>
          <el-tab-pane :label="t('pipeline.yamlPreview')" name="yaml">
            <YamlPreview @load-yaml="handleLoadYaml" />
          </el-tab-pane>
          <el-tab-pane :label="t('pipeline.mapPreviewTab')" name="map">
            <div class="map-tab-container">
              <MapPreview :geojson="executionGeoJson" :height="bottomPanelHeight - 60" />
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </template>

    <!-- Status bar -->
    <div class="status-bar">
      <span class="status-name">{{ pipelineName }}</span>
      <span class="status-sep">|</span>
      <span class="status-info">{{ statusText }}</span>
      <span class="status-shortcuts">Ctrl+S {{ t('common.save') }} &middot; Ctrl+Enter {{ t('pipeline.run') }}</span>
    </div>

    <!-- AI Generate Dialog -->
    <el-dialog
      v-model="showAiDialog"
      :title="t('pipeline.aiGenerateTitle')"
      width="560px"
      :close-on-click-modal="false"
    >
      <el-input
        v-model="aiPrompt"
        type="textarea"
        :rows="6"
        :placeholder="t('pipeline.aiGenerateHint')"
      />
      <template #footer>
        <el-button @click="showAiDialog = false">{{ t('common.cancel') }}</el-button>
        <el-button
          type="primary"
          :loading="aiGenerating"
          @click="handleAiGenerate"
        >
          {{ t('common.generate') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- Save Dialog -->
    <el-dialog v-model="showSaveDialog" :title="t('pipeline.savePipeline')" width="420px">
      <el-input
        v-model="saveName"
        :placeholder="t('pipeline.enterName')"
        @keydown.enter="handleSave"
      />
      <template #footer>
        <el-button @click="showSaveDialog = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="handleSave">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>
  </el-container>
</template>

<style scoped>
.pipeline-editor {
  height: calc(100vh - 88px);
  display: flex;
  flex-direction: column;
}

/* ── Toolbar ── */
.toolbar {
  flex-shrink: 0;
  padding: 6px 12px;
  background: var(--gp-bg-primary);
  border-bottom: 1px solid var(--gp-border-color);
  border-radius: 4px 4px 0 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  transition: background var(--gp-transition), border-color var(--gp-transition);
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 2px;
  flex-shrink: 0;
}

.hidden-file-input {
  display: none;
}

/* ── Editor middle ── */
.editor-middle {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.palette-aside {
  border-right: 1px solid var(--gp-border-color);
  background: var(--gp-bg-primary);
  overflow-y: auto;
  padding: 12px;
  transition: background var(--gp-transition), border-color var(--gp-transition);
}

.canvas-main {
  padding: 0;
  overflow: hidden;
  position: relative;
}

.config-aside {
  border-left: 1px solid var(--gp-border-color);
  background: var(--gp-bg-primary);
  overflow-y: auto;
  padding: 12px;
  transition: background var(--gp-transition), border-color var(--gp-transition);
}

/* ── Panel transitions ── */
.slide-left-enter-active,
.slide-left-leave-active {
  transition: width 0.25s ease, opacity 0.2s ease, padding 0.25s ease;
  overflow: hidden;
}
.slide-left-enter-from,
.slide-left-leave-to {
  width: 0 !important;
  padding: 0 !important;
  opacity: 0;
}

.slide-right-enter-active,
.slide-right-leave-active {
  transition: width 0.25s ease, opacity 0.2s ease, padding 0.25s ease;
  overflow: hidden;
}
.slide-right-enter-from,
.slide-right-leave-to {
  width: 0 !important;
  padding: 0 !important;
  opacity: 0;
}

/* ── Resize handle ── */
.resize-handle {
  flex-shrink: 0;
  height: 6px;
  cursor: row-resize;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--gp-bg-primary);
  border-top: 1px solid var(--gp-border-color);
  transition: background 0.15s;
}

.resize-handle:hover {
  background: var(--gp-active-bg);
}

.resize-bar {
  width: 40px;
  height: 3px;
  background: var(--gp-border-color);
  border-radius: 2px;
  transition: background 0.15s;
}

.resize-handle:hover .resize-bar {
  background: #409eff;
}

/* ── Bottom panel ── */
.bottom-panel {
  flex-shrink: 0;
  background: var(--gp-bg-primary);
  display: flex;
  flex-direction: column;
  transition: background var(--gp-transition);
}

.bottom-tabs {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.bottom-tabs :deep(.el-tabs__header) {
  margin-bottom: 0;
  padding: 0 12px;
}

.bottom-tabs :deep(.el-tabs__content) {
  flex: 1;
  overflow: hidden;
}

.bottom-tabs :deep(.el-tab-pane) {
  height: 100%;
}

/* ── Status bar ── */
.status-bar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 3px 12px;
  font-size: 11px;
  color: var(--gp-text-muted);
  background: var(--gp-bg-primary);
  border-top: 1px solid var(--gp-border-color);
  transition: background var(--gp-transition), border-color var(--gp-transition);
}

.status-name {
  font-weight: 500;
  color: var(--gp-text-secondary);
}

.status-sep {
  opacity: 0.3;
}

.status-shortcuts {
  margin-left: auto;
  opacity: 0.5;
}

/* ── Map tab container ── */
.map-tab-container {
  height: 100%;
  overflow: auto;
}

/* ── Empty state overlay ── */
.canvas-empty-state {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  z-index: 5;
}

.empty-state-card {
  text-align: center;
  padding: 32px 40px;
  border-radius: 12px;
  background: var(--gp-bg-elevated);
  border: 1px dashed var(--gp-border-color);
  box-shadow: var(--gp-shadow-md);
  pointer-events: auto;
  max-width: 400px;
}

.empty-icon {
  font-size: 40px;
  margin-bottom: 12px;
}

.empty-title {
  margin: 0 0 16px;
  font-size: 16px;
  font-weight: 600;
  color: var(--gp-text-primary);
}

.empty-hints {
  text-align: left;
  margin-bottom: 20px;
}

.empty-hints p {
  margin: 8px 0;
  font-size: 13px;
  color: var(--gp-text-secondary);
  line-height: 1.6;
}
</style>
