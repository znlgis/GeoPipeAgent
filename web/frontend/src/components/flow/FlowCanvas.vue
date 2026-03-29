<script setup lang="ts">
import { watch } from 'vue'
import { VueFlow, useVueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import type { NodeChange, EdgeChange, Connection } from '@vue-flow/core'
import { usePipelineStore } from '@/stores/pipelineStore'
import type { StepSchema, StepNodeData } from '@/types/pipeline'
import StepNode from './StepNode.vue'

const store = usePipelineStore()
const { screenToFlowCoordinate } = useVueFlow()

/** Ensure every node uses the custom 'stepNode' type for proper slot rendering. */
function ensureNodeTypes() {
  for (const node of store.nodes) {
    if (node.type !== 'stepNode') {
      node.type = 'stepNode'
    }
  }
}

// Patch node types when the nodes array reference changes (e.g. YAML import).
watch(() => store.nodes, ensureNodeTypes, { immediate: true })

function onDragOver(event: DragEvent) {
  event.preventDefault()
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = 'move'
  }
}

function onDrop(event: DragEvent) {
  if (!event.dataTransfer) return
  const raw = event.dataTransfer.getData('application/geopipe-step')
  if (!raw) return

  let stepSchema: StepSchema
  try {
    stepSchema = JSON.parse(raw) as StepSchema
  } catch {
    return
  }

  const position = screenToFlowCoordinate({
    x: event.clientX,
    y: event.clientY,
  })

  const nodeId = store.addNode(stepSchema, position)
  const newNode = store.nodes.find((n) => n.id === nodeId)
  if (newNode) {
    newNode.type = 'stepNode'
  }
}

function onConnect(connection: Connection) {
  store.addEdge({
    id: `e-${connection.source}-${connection.target}`,
    source: connection.source,
    target: connection.target,
    sourceHandle: connection.sourceHandle ?? undefined,
    targetHandle: connection.targetHandle ?? undefined,
  })
}

function onNodeClick({ node }: { node: { id: string } }) {
  store.selectNode(node.id)
}

function onPaneClick() {
  store.selectNode(null)
}

function onNodesChange(changes: NodeChange[]) {
  for (const change of changes) {
    if (change.type === 'remove') {
      store.removeNode(change.id)
    }
  }
}

function onEdgesChange(changes: EdgeChange[]) {
  for (const change of changes) {
    if (change.type === 'remove') {
      store.removeEdge(change.id)
    }
  }
}
</script>

<template>
  <div
    class="flow-canvas-container"
    @dragover="onDragOver"
    @drop="onDrop"
  >
    <VueFlow
      v-model:nodes="store.nodes"
      v-model:edges="store.edges"
      :default-edge-options="{ type: 'smoothstep', animated: true }"
      :snap-to-grid="true"
      :snap-grid="[16, 16]"
      fit-view-on-init
      @connect="onConnect"
      @node-click="onNodeClick"
      @pane-click="onPaneClick"
      @nodes-change="onNodesChange"
      @edges-change="onEdgesChange"
    >
      <template #node-stepNode="props">
        <StepNode :id="props.id" :data="props.data as StepNodeData" />
      </template>

      <Background :gap="16" />
      <Controls />
      <MiniMap />
    </VueFlow>
  </div>
</template>

<style scoped>
.flow-canvas-container {
  width: 100%;
  min-height: 500px;
  height: 100%;
  border: 1px solid var(--gp-border-color, #dcdfe6);
  border-radius: 4px;
  overflow: hidden;
  background: var(--gp-bg-secondary, #f5f7fa);
  transition: background var(--gp-transition), border-color var(--gp-transition);
}

/* Vue Flow base styles */
.flow-canvas-container :deep(.vue-flow) {
  width: 100%;
  height: 100%;
}

/* Dark mode overrides for vue-flow internals */
.flow-canvas-container :deep(.vue-flow__background) {
  fill: var(--gp-bg-secondary, #f5f7fa);
}

.flow-canvas-container :deep(.vue-flow__minimap) {
  background: var(--gp-bg-elevated, #fff);
  border: 1px solid var(--gp-border-color, #dcdfe6);
  border-radius: 4px;
  box-shadow: var(--gp-shadow-sm);
}

.flow-canvas-container :deep(.vue-flow__controls) {
  box-shadow: var(--gp-shadow-sm);
  border-radius: 4px;
  overflow: hidden;
}

.flow-canvas-container :deep(.vue-flow__controls-button) {
  background: var(--gp-bg-primary, #fff);
  border-color: var(--gp-border-color, #dcdfe6);
  color: var(--gp-text-secondary, #606266);
}

.flow-canvas-container :deep(.vue-flow__controls-button:hover) {
  background: var(--gp-hover-bg, #f5f7fa);
}
</style>
