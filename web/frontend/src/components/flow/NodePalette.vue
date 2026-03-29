<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Search } from '@element-plus/icons-vue'
import { usePipelineStore } from '@/stores/pipelineStore'
import type { StepSchema } from '@/types/pipeline'

const store = usePipelineStore()
const { t } = useI18n()

const searchQuery = ref('')

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
      label: categoryLabels[cat.name] ?? cat.label,
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

    <!-- Grouped steps -->
    <el-collapse
      v-if="filteredCategories.length > 0"
      :model-value="defaultActive"
      class="palette-collapse"
    >
      <el-collapse-item
        v-for="category in filteredCategories"
        :key="category.name"
        :title="category.label"
        :name="category.name"
      >
        <div
          v-for="step in category.steps"
          :key="step.name"
          class="palette-item"
          draggable="true"
          @dragstart="onDragStart($event, step)"
        >
          <div class="palette-item__name">{{ step.name }}</div>
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

.palette-collapse {
  border: none;
}

.palette-collapse :deep(.el-collapse-item__header) {
  font-size: 13px;
  font-weight: 600;
  height: 36px;
  line-height: 36px;
}

.palette-item {
  padding: 8px 10px;
  margin-bottom: 4px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  cursor: grab;
  transition: background 0.15s, border-color 0.15s;
  user-select: none;
}

.palette-item:hover {
  background: #ecf5ff;
  border-color: #409eff;
}

.palette-item:active {
  cursor: grabbing;
}

.palette-item__name {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
}

.palette-item__desc {
  font-size: 11px;
  color: #909399;
  line-height: 1.3;
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}
</style>
