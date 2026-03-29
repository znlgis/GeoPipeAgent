<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Search } from '@element-plus/icons-vue'
import { usePipelineStore } from '@/stores/pipelineStore'
import type { StepSchema } from '@/types/pipeline'

const store = usePipelineStore()
const { t } = useI18n()

const searchQuery = ref('')

const categoryColors: Record<string, string> = {
  io: '#409eff',
  vector: '#67c23a',
  raster: '#e6a23c',
  analysis: '#9b59b6',
  network: '#00bcd4',
  qc: '#f56c6c',
}

const categoryLabels = computed<Record<string, string>>(() => ({
  io: t('nodePalette.categories.io'),
  vector: t('nodePalette.categories.vector'),
  raster: t('nodePalette.categories.raster'),
  analysis: t('nodePalette.categories.analysis'),
  network: t('nodePalette.categories.network'),
  qc: t('nodePalette.categories.qc'),
}))

const filteredCategories = computed(() => {
  const query = searchQuery.value.toLowerCase().trim()
  return store.stepCategories
    .map((cat) => ({
      ...cat,
      label: categoryLabels.value[cat.name] ?? cat.label,
      steps: query
        ? cat.steps.filter(
            (s) =>
              s.name.toLowerCase().includes(query) ||
              s.description.toLowerCase().includes(query),
          )
        : cat.steps,
    }))
    .filter((cat) => cat.steps.length > 0)
})

const defaultActive = computed(() =>
  filteredCategories.value.map((c) => c.name),
)

function onDragStart(event: DragEvent, step: StepSchema) {
  if (!event.dataTransfer) return
  event.dataTransfer.setData('application/geopipe-step', JSON.stringify(step))
  event.dataTransfer.effectAllowed = 'move'
}

function onDoubleClick(step: StepSchema) {
  // Add node at center of canvas
  const position = { x: 200 + Math.random() * 100, y: 100 + Math.random() * 100 }
  const nodeId = store.addNode(step, position)
  const newNode = store.nodes.find((n) => n.id === nodeId)
  if (newNode) {
    newNode.type = 'stepNode'
  }
}

onMounted(() => {
  if (store.steps.length === 0) {
    store.fetchSteps()
  }
})
</script>

<template>
  <div class="node-palette">
    <!-- Search -->
    <el-input
      v-model="searchQuery"
      size="small"
      :placeholder="t('nodePalette.searchSteps')"
      clearable
      class="palette-search"
    >
      <template #prefix>
        <el-icon><Search /></el-icon>
      </template>
    </el-input>

    <div class="palette-hint">{{ t('nodePalette.doubleClickHint') }}</div>

    <!-- Grouped steps -->
    <el-collapse
      v-if="filteredCategories.length > 0"
      :model-value="defaultActive"
      class="palette-collapse"
    >
      <el-collapse-item
        v-for="category in filteredCategories"
        :key="category.name"
        :name="category.name"
      >
        <template #title>
          <span class="category-title">
            <span
              class="category-dot"
              :style="{ backgroundColor: categoryColors[category.name] || '#909399' }"
            />
            {{ category.label }}
            <el-tag size="small" type="info" class="category-count">{{ category.steps.length }}</el-tag>
          </span>
        </template>
        <div
          v-for="step in category.steps"
          :key="step.name"
          class="palette-item"
          :style="{ '--cat-color': categoryColors[category.name] || '#909399' }"
          draggable="true"
          @dragstart="onDragStart($event, step)"
          @dblclick="onDoubleClick(step)"
        >
          <div class="palette-item__header">
            <span class="palette-item__name">{{ step.name }}</span>
          </div>
          <div class="palette-item__desc">{{ step.description }}</div>
        </div>
      </el-collapse-item>
    </el-collapse>

    <el-empty
      v-else-if="searchQuery"
      :description="t('nodePalette.noMatch')"
      :image-size="48"
    />
    <el-empty v-else :description="t('nodePalette.noSteps')" :image-size="48" />
  </div>
</template>

<style scoped>
.node-palette {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.palette-search {
  flex-shrink: 0;
}

.palette-hint {
  font-size: 11px;
  color: var(--gp-text-muted);
  text-align: center;
  padding: 0 4px;
}

.palette-collapse {
  border: none;
}

.palette-collapse :deep(.el-collapse-item__header) {
  font-size: 13px;
  font-weight: 600;
  height: 36px;
  line-height: 36px;
}

.category-title {
  display: flex;
  align-items: center;
  gap: 6px;
}

.category-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.category-count {
  font-size: 10px;
  margin-left: auto;
  margin-right: 8px;
}

.palette-item {
  padding: 8px 10px;
  margin-bottom: 4px;
  border: 1px solid var(--gp-border-color);
  border-left: 3px solid var(--cat-color, var(--gp-border-color));
  border-radius: 6px;
  cursor: grab;
  transition: background 0.15s, border-color 0.15s, box-shadow 0.15s;
  user-select: none;
  background: var(--gp-bg-primary);
}

.palette-item:hover {
  background: var(--gp-active-bg);
  border-color: var(--cat-color, #409eff);
  box-shadow: var(--gp-shadow-sm);
}

.palette-item:active {
  cursor: grabbing;
  transform: scale(0.98);
}

.palette-item__header {
  display: flex;
  align-items: center;
  gap: 6px;
}

.palette-item__name {
  font-size: 13px;
  font-weight: 500;
  color: var(--gp-text-primary);
}

.palette-item__desc {
  font-size: 11px;
  color: var(--gp-text-muted);
  line-height: 1.3;
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}
</style>
