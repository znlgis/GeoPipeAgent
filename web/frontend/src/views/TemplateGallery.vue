<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { useTemplateStore } from '@/stores/templateStore'
import { usePipelineStore } from '@/stores/pipelineStore'
import { getLocale } from '@/locales'
import type { TemplateInfo, TemplateDetail } from '@/types/template'

const { t } = useI18n()
const router = useRouter()
const templateStore = useTemplateStore()
const pipelineStore = usePipelineStore()
const searchQuery = ref('')
const selectedCategory = ref('')
const showDetailDialog = ref(false)
const detailTemplate = ref<TemplateDetail | null>(null)
const detailLoading = ref(false)

// --- Favorites ---
const favoriteIds = ref<string[]>([])

onMounted(() => {
  templateStore.fetchTemplates()
  // Load favorites from localStorage
  try {
    const saved = localStorage.getItem('geopipe-favorite-templates')
    if (saved) favoriteIds.value = JSON.parse(saved)
  } catch { /* ignore */ }
})

const currentLocale = computed(() => getLocale())

const categories = computed(() => {
  const cats = new Set(templateStore.templates.map((tpl) => tpl.category))
  return Array.from(cats).sort()
})

const filteredTemplates = computed(() => {
  let result = templateStore.templates
  if (selectedCategory.value) {
    result = result.filter((tpl) => tpl.category === selectedCategory.value)
  }
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    result = result.filter(
      (tpl) =>
        tpl.name.toLowerCase().includes(q) ||
        tpl.name_en.toLowerCase().includes(q) ||
        tpl.name_zh.includes(q) ||
        tpl.description_en.toLowerCase().includes(q) ||
        tpl.description_zh.includes(q) ||
        tpl.tags.some((tag) => tag.includes(q)),
    )
  }
  // Sort favorites first
  return [...result].sort((a, b) => {
    const aFav = favoriteIds.value.includes(a.id) ? 0 : 1
    const bFav = favoriteIds.value.includes(b.id) ? 0 : 1
    return aFav - bFav
  })
})

function isFavorite(tplId: string): boolean {
  return favoriteIds.value.includes(tplId)
}

function toggleFavorite(tplId: string) {
  const idx = favoriteIds.value.indexOf(tplId)
  if (idx >= 0) {
    favoriteIds.value.splice(idx, 1)
  } else {
    favoriteIds.value.push(tplId)
  }
  localStorage.setItem('geopipe-favorite-templates', JSON.stringify(favoriteIds.value))
}

function getDisplayName(tpl: TemplateInfo): string {
  return currentLocale.value === 'zh-CN' ? tpl.name_zh : tpl.name_en
}

function getDisplayDesc(tpl: TemplateInfo): string {
  return currentLocale.value === 'zh-CN' ? tpl.description_zh : tpl.description_en
}

function getDifficultyType(level: string): 'success' | 'warning' | 'danger' {
  if (level === 'beginner') return 'success'
  if (level === 'intermediate') return 'warning'
  return 'danger'
}

function getCategoryIcon(category: string): string {
  const icons: Record<string, string> = {
    io: '📂',
    vector: '🗺️',
    raster: '🌄',
    analysis: '📊',
    network: '🔗',
    qc: '✅',
  }
  return icons[category] || '📋'
}

async function loadToEditor(tpl: TemplateInfo) {
  const detail = await templateStore.loadTemplate(tpl.id)
  if (detail?.yaml_content) {
    pipelineStore.loadFromYaml(detail.yaml_content)
    ElMessage.success(t('template.loadedSuccess'))
    router.push('/')
  } else {
    ElMessage.error(t('template.loadFailed'))
  }
}

async function tryWithPrompt(tpl: TemplateInfo) {
  const detail = await templateStore.loadTemplate(tpl.id)
  if (!detail) {
    ElMessage.error(t('template.loadFailed'))
    return
  }
  const prompt = currentLocale.value === 'zh-CN' ? detail.prompt_zh : detail.prompt_en
  // Navigate to chat page with prompt pre-filled
  router.push({
    path: '/chat',
    query: { prompt: prompt, mode: 'generate' },
  })
}

async function viewDetail(tpl: TemplateInfo) {
  detailLoading.value = true
  showDetailDialog.value = true
  const detail = await templateStore.loadTemplate(tpl.id)
  if (detail) {
    detailTemplate.value = detail
  } else {
    ElMessage.error(t('template.loadFailed'))
    showDetailDialog.value = false
  }
  detailLoading.value = false
}
</script>

<template>
  <div class="template-gallery">
    <!-- Header -->
    <div class="gallery-header">
      <div class="header-text">
        <h2>{{ t('template.title') }}</h2>
        <p class="header-desc">{{ t('template.description') }}</p>
      </div>
      <div class="header-actions">
        <el-input
          v-model="searchQuery"
          :placeholder="t('common.search')"
          clearable
          size="default"
          class="search-input"
        >
          <template #prefix>
            <span>🔍</span>
          </template>
        </el-input>
      </div>
    </div>

    <!-- Category Filter -->
    <div class="category-filter">
      <el-radio-group v-model="selectedCategory" size="small">
        <el-radio-button :value="''">{{ t('template.allCategories') }}</el-radio-button>
        <el-radio-button
          v-for="cat in categories"
          :key="cat"
          :value="cat"
        >
          {{ getCategoryIcon(cat) }} {{ cat }}
        </el-radio-button>
      </el-radio-group>
    </div>

    <!-- Template Cards -->
    <div v-if="templateStore.loading" class="loading-state">
      <el-skeleton :rows="3" animated />
    </div>

    <div v-else-if="filteredTemplates.length === 0" class="empty-state">
      <p>{{ t('common.noData') }}</p>
    </div>

    <div v-else class="template-grid">
      <div
        v-for="tpl in filteredTemplates"
        :key="tpl.id"
        class="template-card"
        :class="{ unavailable: !tpl.available }"
      >
        <div class="card-header">
          <span class="category-icon">{{ getCategoryIcon(tpl.category) }}</span>
          <div class="card-title-area">
            <h3 class="card-title">{{ getDisplayName(tpl) }}</h3>
            <div class="card-badges">
              <el-tag size="small" :type="getDifficultyType(tpl.difficulty)">
                {{ t(`template.difficulty.${tpl.difficulty}`) }}
              </el-tag>
              <el-tag size="small" type="info">{{ tpl.category }}</el-tag>
            </div>
          </div>
          <el-button
            size="small"
            text
            class="fav-btn"
            :aria-label="isFavorite(tpl.id) ? t('template.unfavorite') : t('template.favorite')"
            @click.stop="toggleFavorite(tpl.id)"
          >
            {{ isFavorite(tpl.id) ? '⭐' : '☆' }}
          </el-button>
        </div>

        <p class="card-desc">{{ getDisplayDesc(tpl) }}</p>

        <div class="card-tags">
          <el-tag
            v-for="tag in tpl.tags"
            :key="tag"
            size="small"
            effect="plain"
            class="tag-item"
          >
            {{ tag }}
          </el-tag>
        </div>

        <div class="card-actions">
          <el-button
            type="primary"
            size="small"
            :disabled="!tpl.available"
            @click="loadToEditor(tpl)"
          >
            {{ t('template.loadToEditor') }}
          </el-button>
          <el-button
            size="small"
            :disabled="!tpl.available"
            @click="tryWithPrompt(tpl)"
          >
            {{ t('template.tryWithAI') }}
          </el-button>
          <el-button
            size="small"
            text
            :disabled="!tpl.available"
            @click="viewDetail(tpl)"
          >
            {{ t('template.viewDetail') }}
          </el-button>
        </div>
      </div>
    </div>

    <!-- Template Detail Dialog -->
    <el-dialog
      v-model="showDetailDialog"
      :title="t('template.detailTitle')"
      width="700px"
      :close-on-click-modal="true"
    >
      <div v-if="detailLoading" style="text-align: center; padding: 40px">
        <el-skeleton :rows="6" animated />
      </div>
      <div v-else-if="detailTemplate" class="detail-content">
        <div class="detail-meta">
          <h3 class="detail-name">
            {{ currentLocale === 'zh-CN' ? detailTemplate.name_zh : detailTemplate.name_en }}
          </h3>
          <div class="detail-badges">
            <el-tag size="small" :type="getDifficultyType(detailTemplate.difficulty)">
              {{ t(`template.difficulty.${detailTemplate.difficulty}`) }}
            </el-tag>
            <el-tag size="small" type="info">{{ detailTemplate.category }}</el-tag>
          </div>
          <p class="detail-desc">
            {{ currentLocale === 'zh-CN' ? detailTemplate.description_zh : detailTemplate.description_en }}
          </p>
        </div>

        <el-divider />

        <div class="detail-section">
          <h4>{{ t('template.prompt') }}</h4>
          <div class="detail-prompt">
            {{ currentLocale === 'zh-CN' ? detailTemplate.prompt_zh : detailTemplate.prompt_en }}
          </div>
        </div>

        <el-divider />

        <div class="detail-section">
          <h4>{{ t('template.yamlContent') }}</h4>
          <pre class="detail-yaml">{{ detailTemplate.yaml_content }}</pre>
        </div>
      </div>
      <template #footer>
        <el-button @click="showDetailDialog = false">{{ t('common.cancel') }}</el-button>
        <el-button
          v-if="detailTemplate"
          type="primary"
          @click="loadToEditor(detailTemplate); showDetailDialog = false"
        >
          {{ t('template.loadToEditor') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.template-gallery {
  max-width: 1200px;
  margin: 0 auto;
}

.gallery-header {
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

.search-input {
  width: 260px;
}

.category-filter {
  margin-bottom: 20px;
}

.template-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}

.template-card {
  background: var(--gp-bg-elevated);
  border: 1px solid var(--gp-border-color);
  border-radius: 8px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: box-shadow var(--gp-transition), border-color var(--gp-transition);
}

.template-card:hover {
  box-shadow: var(--gp-shadow-md);
  border-color: #409eff;
}

.template-card.unavailable {
  opacity: 0.6;
}

.card-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.category-icon {
  font-size: 28px;
  flex-shrink: 0;
  line-height: 1;
}

.card-title-area {
  flex: 1;
  min-width: 0;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  margin: 0 0 6px;
  color: var(--gp-text-primary);
}

.card-badges {
  display: flex;
  gap: 6px;
}

.card-desc {
  font-size: 13px;
  color: var(--gp-text-secondary);
  margin: 0;
  line-height: 1.5;
}

.card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.tag-item {
  font-size: 11px;
}

.card-actions {
  display: flex;
  gap: 8px;
  margin-top: auto;
  padding-top: 8px;
  border-top: 1px solid var(--gp-border-light);
}

.fav-btn {
  font-size: 18px;
  flex-shrink: 0;
  padding: 4px;
}

.loading-state,
.empty-state {
  padding: 60px 0;
  text-align: center;
  color: var(--gp-text-muted);
}

/* ── Template Detail Dialog ── */
.detail-content {
  max-height: 65vh;
  overflow-y: auto;
}

.detail-name {
  margin: 0 0 8px;
  font-size: 18px;
  color: var(--gp-text-primary);
}

.detail-badges {
  display: flex;
  gap: 6px;
  margin-bottom: 12px;
}

.detail-desc {
  margin: 0;
  font-size: 14px;
  color: var(--gp-text-secondary);
  line-height: 1.6;
}

.detail-section h4 {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--gp-text-primary);
}

.detail-prompt {
  background: var(--gp-bg-secondary);
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--gp-text-secondary);
}

.detail-yaml {
  background: var(--gp-code-bg, #1e1e1e);
  color: #d4d4d4;
  padding: 16px;
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.6;
  overflow-x: auto;
  max-height: 300px;
  margin: 0;
}
</style>
