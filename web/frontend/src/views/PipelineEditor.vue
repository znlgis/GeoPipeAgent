<script setup lang="ts">
import { onMounted } from 'vue'
import { usePipelineStore } from '@/stores/pipelineStore'

const pipelineStore = usePipelineStore()

onMounted(() => {
  pipelineStore.fetchSteps()
})
</script>

<template>
  <div class="pipeline-editor">
    <el-row :gutter="16" class="editor-layout">
      <el-col :span="4">
        <el-card shadow="never" class="panel">
          <template #header>
            <span>步骤库</span>
          </template>
          <el-collapse v-if="pipelineStore.stepCategories.length > 0">
            <el-collapse-item
              v-for="category in pipelineStore.stepCategories"
              :key="category.name"
              :title="category.label"
              :name="category.name"
            >
              <div
                v-for="step in category.steps"
                :key="step.name"
                class="step-item"
                draggable="true"
              >
                <el-text size="small">{{ step.name }}</el-text>
                <el-text type="info" size="small" class="step-desc">
                  {{ step.description }}
                </el-text>
              </div>
            </el-collapse-item>
          </el-collapse>
          <el-empty v-else description="暂无可用步骤" :image-size="60" />
        </el-card>
      </el-col>
      <el-col :span="14">
        <el-card shadow="never" class="panel canvas-panel">
          <template #header>
            <div class="canvas-header">
              <span>流程画布</span>
              <el-button-group>
                <el-button size="small" @click="pipelineStore.layoutNodes()">
                  自动布局
                </el-button>
                <el-button size="small" type="primary">
                  运行
                </el-button>
              </el-button-group>
            </div>
          </template>
          <div class="canvas-placeholder">
            <el-empty description="拖拽步骤到画布开始编辑" />
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="panel">
          <template #header>
            <span>属性面板</span>
          </template>
          <div v-if="pipelineStore.selectedNodeId">
            <el-text>节点: {{ pipelineStore.selectedNodeId }}</el-text>
          </div>
          <el-empty v-else description="选择节点查看属性" :image-size="60" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.pipeline-editor {
  height: calc(100vh - 120px);
}

.editor-layout {
  height: 100%;
}

.panel {
  height: 100%;
}

.canvas-panel :deep(.el-card__body) {
  height: calc(100% - 56px);
  padding: 0;
}

.canvas-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.canvas-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.step-item {
  padding: 8px;
  margin-bottom: 4px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  cursor: grab;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.step-item:hover {
  background: #ecf5ff;
  border-color: #409eff;
}

.step-desc {
  line-height: 1.3;
}
</style>
