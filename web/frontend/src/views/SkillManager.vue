<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { Download, Refresh, Document, CopyDocument } from '@element-plus/icons-vue'
import { useSkillStore } from '@/stores/skillStore'

const { t } = useI18n()
const skillStore = useSkillStore()

const activeTab = ref('skill')
const expandedModules = ref<Set<string>>(new Set())

onMounted(async () => {
  await skillStore.fetchModules()
  await skillStore.fetchAllContent()
})

const currentContent = computed(() => {
  return skillStore.contents.get(activeTab.value)
})

async function handleGenerate() {
  const result = await skillStore.generateSkillFiles()
  if (result) {
    ElMessage.success(t('skill.generateSuccess', { count: result.files.length }))
  } else {
    ElMessage.error(t('skill.generateFailed'))
  }
}

async function handleCopyContent(moduleId: string) {
  const content = skillStore.contents.get(moduleId)
  if (content) {
    try {
      await navigator.clipboard.writeText(content.content)
      ElMessage.success(t('common.copiedToClipboard'))
    } catch {
      ElMessage.error(t('common.copyFailed'))
    }
  }
}

function handleDownload(moduleId: string) {
  const content = skillStore.contents.get(moduleId)
  if (!content) return

  const filenames: Record<string, string> = {
    'skill': 'SKILL.md',
    'steps-reference': 'steps-reference.md',
    'pipeline-schema': 'pipeline-schema.md',
  }

  const blob = new Blob([content.content], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filenames[moduleId] || `${moduleId}.md`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

function handleDownloadAll() {
  for (const mod of skillStore.modules) {
    handleDownload(mod.id)
  }
}

function toggleExpand(moduleId: string) {
  if (expandedModules.value.has(moduleId)) {
    expandedModules.value.delete(moduleId)
  } else {
    expandedModules.value.add(moduleId)
  }
}
</script>

<template>
  <div class="skill-manager">
    <!-- Header -->
    <div class="skill-header">
      <div class="header-info">
        <h2 class="page-title">{{ t('skill.managerTitle') }}</h2>
        <p class="page-desc">{{ t('skill.managerDesc') }}</p>
      </div>
      <div class="header-actions">
        <el-button :icon="Refresh" @click="handleGenerate" :loading="skillStore.isGenerating">
          {{ t('skill.regenerate') }}
        </el-button>
        <el-button :icon="Download" type="primary" @click="handleDownloadAll">
          {{ t('skill.downloadAll') }}
        </el-button>
      </div>
    </div>

    <!-- Module cards overview -->
    <div class="module-cards">
      <div
        v-for="mod in skillStore.modules"
        :key="mod.id"
        class="module-card"
        :class="{ active: activeTab === mod.id }"
        @click="activeTab = mod.id"
      >
        <div class="card-icon">
          <el-icon :size="24"><Document /></el-icon>
        </div>
        <div class="card-info">
          <div class="card-name">{{ mod.name }}</div>
          <div class="card-desc">{{ mod.description }}</div>
        </div>
        <div class="card-meta">
          <el-tag size="small" effect="plain">~{{ mod.token_estimate }} tokens</el-tag>
        </div>
      </div>
    </div>

    <!-- Content viewer -->
    <div class="content-viewer" v-if="currentContent">
      <div class="viewer-header">
        <div class="viewer-title">
          <h3>{{ skillStore.modules.find(m => m.id === activeTab)?.name }}</h3>
          <el-tag size="small" type="info">
            {{ currentContent.char_count.toLocaleString() }} {{ t('skill.chars') }}
          </el-tag>
        </div>
        <div class="viewer-actions">
          <el-button
            size="small"
            :icon="CopyDocument"
            @click="handleCopyContent(activeTab)"
          >
            {{ t('common.copy') }}
          </el-button>
          <el-button
            size="small"
            :icon="Download"
            @click="handleDownload(activeTab)"
          >
            {{ t('common.export') }}
          </el-button>
        </div>
      </div>
      <div class="viewer-content">
        <pre class="markdown-source"><code>{{ currentContent.content }}</code></pre>
      </div>
    </div>

    <div v-else class="content-loading">
      <el-skeleton :rows="10" animated />
    </div>

    <!-- Skill integration guide -->
    <div class="integration-guide">
      <h3>{{ t('skill.guideTitle') }}</h3>
      <div class="guide-steps">
        <div class="guide-step">
          <div class="step-number">1</div>
          <div class="step-content">
            <div class="step-title">{{ t('skill.guideStep1Title') }}</div>
            <div class="step-desc">{{ t('skill.guideStep1Desc') }}</div>
          </div>
        </div>
        <div class="guide-step">
          <div class="step-number">2</div>
          <div class="step-content">
            <div class="step-title">{{ t('skill.guideStep2Title') }}</div>
            <div class="step-desc">{{ t('skill.guideStep2Desc') }}</div>
          </div>
        </div>
        <div class="guide-step">
          <div class="step-number">3</div>
          <div class="step-content">
            <div class="step-title">{{ t('skill.guideStep3Title') }}</div>
            <div class="step-desc">{{ t('skill.guideStep3Desc') }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.skill-manager {
  max-width: 1100px;
  margin: 0 auto;
  padding: 0 8px;
}

/* -- Header -- */
.skill-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--gp-text-primary);
  margin: 0 0 4px;
}

.page-desc {
  font-size: 14px;
  color: var(--gp-text-muted);
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

/* -- Module cards -- */
.module-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 12px;
  margin-bottom: 24px;
}

.module-card {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  border-radius: 10px;
  background: var(--gp-bg-primary);
  border: 2px solid var(--gp-border-light);
  cursor: pointer;
  transition: all 0.2s;
}

.module-card:hover {
  border-color: var(--el-color-primary-light-5);
  box-shadow: var(--gp-shadow-sm);
}

.module-card.active {
  border-color: var(--el-color-primary);
  background: var(--gp-active-bg);
}

.card-icon {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: var(--gp-bg-secondary);
  color: var(--el-color-primary);
}

.card-info {
  flex: 1;
  min-width: 0;
}

.card-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--gp-text-primary);
  margin-bottom: 4px;
}

.card-desc {
  font-size: 12px;
  color: var(--gp-text-muted);
  line-height: 1.4;
}

.card-meta {
  flex-shrink: 0;
}

/* -- Content viewer -- */
.content-viewer {
  background: var(--gp-bg-primary);
  border: 1px solid var(--gp-border-light);
  border-radius: 10px;
  overflow: hidden;
  margin-bottom: 24px;
}

.viewer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--gp-border-light);
}

.viewer-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.viewer-title h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--gp-text-primary);
}

.viewer-actions {
  display: flex;
  gap: 6px;
}

.viewer-content {
  max-height: 500px;
  overflow-y: auto;
  padding: 0;
}

.markdown-source {
  margin: 0;
  padding: 16px;
  font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--gp-text-secondary);
  white-space: pre-wrap;
  word-break: break-word;
  background: var(--gp-code-bg);
}

.markdown-source code {
  font-family: inherit;
  color: #d4d4d4;
}

.content-loading {
  padding: 24px;
  background: var(--gp-bg-primary);
  border-radius: 10px;
  margin-bottom: 24px;
}

/* -- Integration guide -- */
.integration-guide {
  background: var(--gp-bg-primary);
  border: 1px solid var(--gp-border-light);
  border-radius: 10px;
  padding: 20px;
  margin-bottom: 24px;
}

.integration-guide h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--gp-text-primary);
  margin: 0 0 16px;
}

.guide-steps {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.guide-step {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.step-number {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--el-color-primary);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
}

.step-content {
  flex: 1;
}

.step-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--gp-text-primary);
  margin-bottom: 2px;
}

.step-desc {
  font-size: 13px;
  color: var(--gp-text-muted);
  line-height: 1.5;
}
</style>
