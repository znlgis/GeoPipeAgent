<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { CopyDocument, Upload } from '@element-plus/icons-vue'
import hljs from 'highlight.js'
import { usePipelineStore } from '@/stores/pipelineStore'

const props = withDefaults(
  defineProps<{
    yaml?: string
  }>(),
  { yaml: '' },
)

const emit = defineEmits<{
  (e: 'load-yaml', yaml: string): void
}>()

const pipelineStore = usePipelineStore()
const codeRef = ref<HTMLElement | null>(null)

/** Use the external prop if provided, otherwise fall back to store. */
const yamlContent = computed(() => props.yaml || pipelineStore.yamlPreview)

const highlightedYaml = computed(() => {
  if (!yamlContent.value) return ''
  try {
    return hljs.highlight(yamlContent.value, { language: 'yaml' }).value
  } catch {
    return yamlContent.value
  }
})

async function copyToClipboard() {
  try {
    await navigator.clipboard.writeText(yamlContent.value)
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.error('复制失败')
  }
}

function loadToEditor() {
  emit('load-yaml', yamlContent.value)
}
</script>

<template>
  <div class="yaml-preview">
    <div class="toolbar">
      <span class="title">YAML 预览</span>
      <div class="actions">
        <el-button size="small" :icon="CopyDocument" @click="copyToClipboard">
          复制
        </el-button>
        <el-button
          v-if="props.yaml"
          size="small"
          type="primary"
          :icon="Upload"
          @click="loadToEditor"
        >
          加载到编辑器
        </el-button>
      </div>
    </div>

    <div class="code-container">
      <pre v-if="yamlContent"><code ref="codeRef" class="hljs language-yaml" v-html="highlightedYaml" /></pre>
      <el-empty v-else description="暂无 YAML 内容" :image-size="64" />
    </div>
  </div>
</template>

<style scoped>
.yaml-preview {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border-bottom: 1px solid #e4e7ed;
  background: #fafafa;
}

.title {
  font-size: 13px;
  font-weight: 600;
  color: #606266;
}

.actions {
  display: flex;
  gap: 6px;
}

.code-container {
  flex: 1;
  overflow: auto;
  background: #1e1e1e;
}

.code-container pre {
  margin: 0;
  padding: 12px;
  font-size: 13px;
  line-height: 1.5;
}

.code-container code {
  font-family: 'Fira Code', 'Consolas', monospace;
}
</style>
