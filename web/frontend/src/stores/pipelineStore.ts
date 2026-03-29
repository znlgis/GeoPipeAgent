import { defineStore } from 'pinia'
import { computed, ref, type Ref } from 'vue'
import axios from 'axios'
import type { Node, Edge } from '@vue-flow/core'
import type {
  StepSchema,
  StepCategory,
  PipelineMeta,
  StepNodeData,
} from '@/types/pipeline'
import { yamlToGraph, graphToYaml, autoLayout } from '@/utils/yamlConverter'

/** Simplified node/edge shapes for Pinia ref to avoid deep type recursion */
type FlowNode = Node<StepNodeData, any, string>
type FlowEdge = Edge<any, any, string>

export const usePipelineStore = defineStore('pipeline', () => {
  // --- State ---
  const steps = ref<StepSchema[]>([])
  const nodes: Ref<FlowNode[]> = ref([])
  const edges: Ref<FlowEdge[]> = ref([])
  const meta = ref<PipelineMeta>({
    name: 'Untitled Pipeline',
    variables: {},
    outputs: {},
  })
  const selectedNodeId = ref<string | null>(null)
  const executionStatus = ref<'idle' | 'running' | 'done' | 'error'>('idle')
  const executionLog = ref<string[]>([])

  // --- Getters ---
  const stepCategories = computed<StepCategory[]>(() => {
    const categoryMap = new Map<string, StepSchema[]>()
    for (const step of steps.value) {
      const cat = step.category || 'uncategorized'
      if (!categoryMap.has(cat)) {
        categoryMap.set(cat, [])
      }
      categoryMap.get(cat)!.push(step)
    }
    return Array.from(categoryMap.entries()).map(([name, items]) => ({
      name,
      label: name.charAt(0).toUpperCase() + name.slice(1),
      steps: items,
    }))
  })

  const yamlPreview = computed<string>(() => {
    try {
      return graphToYaml(nodes.value, edges.value, meta.value)
    } catch {
      return '# Error generating YAML preview'
    }
  })

  // --- Actions ---
  async function fetchSteps() {
    try {
      const response = await axios.get<StepSchema[]>('/api/v1/steps')
      steps.value = response.data
    } catch (error) {
      console.error('Failed to fetch steps:', error)
    }
  }

  function loadFromYaml(yamlContent: string) {
    const result = yamlToGraph(yamlContent)
    nodes.value = result.nodes
    edges.value = result.edges
    meta.value = result.meta
    selectedNodeId.value = null
    executionStatus.value = 'idle'
    executionLog.value = []
  }

  function exportToYaml(): string {
    return graphToYaml(nodes.value, edges.value, meta.value)
  }

  function selectNode(id: string | null) {
    selectedNodeId.value = id
  }

  function updateNodeData(id: string, data: Partial<StepNodeData>) {
    const node = nodes.value.find((n) => n.id === id)
    if (node) {
      node.data = { ...(node.data as StepNodeData), ...data }
    }
  }

  function addNode(stepSchema: StepSchema, position: { x: number; y: number }) {
    const existingIds = nodes.value.map((n) => n.id)
    let baseName = stepSchema.name.replace(/[^a-zA-Z0-9_]/g, '_').toLowerCase()
    let counter = 1
    let nodeId = baseName
    while (existingIds.includes(nodeId)) {
      nodeId = `${baseName}_${counter++}`
    }

    const defaultParams: Record<string, any> = {}
    for (const [key, schema] of Object.entries(stepSchema.params)) {
      if (schema.default !== undefined) {
        defaultParams[key] = schema.default
      }
    }

    const newNode: FlowNode = {
      id: nodeId,
      type: 'default',
      position,
      data: {
        use: stepSchema.name,
        label: stepSchema.name,
        params: defaultParams,
        status: 'idle',
      } as StepNodeData,
    }

    nodes.value.push(newNode)
    return nodeId
  }

  function removeNode(id: string) {
    nodes.value = nodes.value.filter((n) => n.id !== id)
    edges.value = edges.value.filter((e) => e.source !== id && e.target !== id)
    if (selectedNodeId.value === id) {
      selectedNodeId.value = null
    }
  }

  function addEdge(edge: FlowEdge) {
    const exists = edges.value.some(
      (e) => e.source === edge.source && e.target === edge.target,
    )
    if (!exists) {
      edges.value.push(edge)
    }
  }

  function removeEdge(id: string) {
    edges.value = edges.value.filter((e) => e.id !== id)
  }

  function layoutNodes() {
    nodes.value = autoLayout(nodes.value, edges.value)
  }

  return {
    // State
    steps,
    nodes,
    edges,
    meta,
    selectedNodeId,
    executionStatus,
    executionLog,
    // Getters
    stepCategories,
    yamlPreview,
    // Actions
    fetchSteps,
    loadFromYaml,
    exportToYaml,
    selectNode,
    updateNodeData,
    addNode,
    removeNode,
    addEdge,
    removeEdge,
    layoutNodes,
  }
})
