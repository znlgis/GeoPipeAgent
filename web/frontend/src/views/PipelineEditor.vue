<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  VideoPlay,
  CircleCheck,
  FolderOpened,
  MagicStick,
  Upload,
  Download,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { usePipelineStore } from '@/stores/pipelineStore'
import { useChatStore } from '@/stores/chatStore'
import { useFlowEditor } from '@/composables/useFlowEditor'
import FlowCanvas from '@/components/flow/FlowCanvas.vue'
import StepConfigPanel from '@/components/flow/StepConfigPanel.vue'
import NodePalette from '@/components/flow/NodePalette.vue'
import ExecutionLog from '@/components/common/ExecutionLog.vue'
import YamlPreview from '@/components/common/YamlPreview.vue'

const pipelineStore = usePipelineStore()
const chatStore = useChatStore()
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

onMounted(() => {
  pipelineStore.fetchSteps()
})

async function handleRun() {
  await executePipeline()
  activeBottomTab.value = 'log'
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

  // Poll for generation completion
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

onBeforeUnmount(() => {
  clearAiPoll()
})

function extractYamlFromContent(): string {
  // Try to extract YAML from the last assistant message
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
      <el-space wrap>
        <el-button
          type="primary"
          :icon="VideoPlay"
          :loading="isExecuting"
          @click="handleRun"
        >
          {{ t('pipeline.run') }}
        </el-button>
        <el-button :icon="CircleCheck" @click="handleValidate">
          {{ t('pipeline.validate') }}
        </el-button>
        <el-button :icon="FolderOpened" @click="handleOpenSave">
          {{ t('common.save') }}
        </el-button>
        <el-button :icon="MagicStick" @click="showAiDialog = true">
          {{ t('pipeline.aiGenerate') }}
        </el-button>
        <el-button :icon="Upload" @click="handleImportClick">
          {{ t('common.import') }}
        </el-button>
        <el-button :icon="Download" @click="handleExport">
          {{ t('common.export') }}
        </el-button>
      </el-space>
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
      <el-aside width="240px" class="palette-aside">
        <NodePalette />
      </el-aside>
      <el-main class="canvas-main">
        <FlowCanvas />
      </el-main>
      <el-aside width="300px" class="config-aside">
        <StepConfigPanel />
      </el-aside>
    </el-container>

    <!-- Bottom section: tabs -->
    <div class="bottom-panel">
      <el-tabs v-model="activeBottomTab" class="bottom-tabs">
        <el-tab-pane :label="t('pipeline.executionLog')" name="log">
          <ExecutionLog />
        </el-tab-pane>
        <el-tab-pane :label="t('pipeline.yamlPreview')" name="yaml">
          <YamlPreview @load-yaml="handleLoadYaml" />
        </el-tab-pane>
      </el-tabs>
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
  height: calc(100vh - 100px);
  display: flex;
  flex-direction: column;
}

.toolbar {
  flex-shrink: 0;
  padding: 8px 12px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  border-radius: 4px 4px 0 0;
}

.hidden-file-input {
  display: none;
}

.editor-middle {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.palette-aside {
  border-right: 1px solid #e4e7ed;
  background: #fff;
  overflow-y: auto;
  padding: 12px;
}

.canvas-main {
  padding: 0;
  overflow: hidden;
}

.config-aside {
  border-left: 1px solid #e4e7ed;
  background: #fff;
  overflow-y: auto;
  padding: 12px;
}

.bottom-panel {
  flex-shrink: 0;
  height: 200px;
  border-top: 1px solid #e4e7ed;
  background: #fff;
  display: flex;
  flex-direction: column;
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
</style>
