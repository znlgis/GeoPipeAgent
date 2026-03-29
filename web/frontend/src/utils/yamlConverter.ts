import yaml from 'js-yaml'
import dagre from 'dagre'
import type { Node, Edge } from '@vue-flow/core'
import type { PipelineMeta, StepNodeData } from '@/types/pipeline'

const NODE_WIDTH = 200
const NODE_HEIGHT = 60

/** Extract all $step_id.attr references from a string value */
export function extractStepRefs(value: string): Array<{ stepId: string; attr: string }> {
  const refs: Array<{ stepId: string; attr: string }> = []
  const regex = /\$(\w+)\.(\w+)/g
  let match: RegExpExecArray | null
  while ((match = regex.exec(value)) !== null) {
    refs.push({ stepId: match[1], attr: match[2] })
  }
  return refs
}

/** Recursively scan an object for step references */
function scanForRefs(obj: any): Array<{ stepId: string; attr: string }> {
  const refs: Array<{ stepId: string; attr: string }> = []
  if (typeof obj === 'string') {
    refs.push(...extractStepRefs(obj))
  } else if (Array.isArray(obj)) {
    for (const item of obj) {
      refs.push(...scanForRefs(item))
    }
  } else if (obj && typeof obj === 'object') {
    for (const val of Object.values(obj)) {
      refs.push(...scanForRefs(val))
    }
  }
  return refs
}

/** Auto-layout nodes using dagre */
export function autoLayout(nodes: Node[], edges: Edge[]): Node[] {
  const g = new dagre.graphlib.Graph()
  g.setDefaultEdgeLabel(() => ({}))
  g.setGraph({ rankdir: 'TB', nodesep: 80, ranksep: 100 })

  for (const node of nodes) {
    g.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT })
  }
  for (const edge of edges) {
    g.setEdge(edge.source, edge.target)
  }

  dagre.layout(g)

  return nodes.map((node) => {
    const pos = g.node(node.id)
    return {
      ...node,
      position: {
        x: pos.x - NODE_WIDTH / 2,
        y: pos.y - NODE_HEIGHT / 2,
      },
    }
  })
}

/** Parse YAML pipeline definition into Vue Flow nodes and edges */
export function yamlToGraph(yamlContent: string): {
  nodes: Node[]
  edges: Edge[]
  meta: PipelineMeta
} {
  const doc = yaml.load(yamlContent) as any
  if (!doc || !doc.pipeline) {
    throw new Error('Invalid pipeline YAML: missing "pipeline" root key')
  }

  const pipeline = doc.pipeline
  const steps: any[] = pipeline.steps || []

  const meta: PipelineMeta = {
    name: pipeline.name || 'Untitled Pipeline',
    description: pipeline.description,
    crs: pipeline.crs,
    variables: pipeline.variables || {},
    outputs: pipeline.outputs || {},
  }

  const nodes: Node[] = []
  const edges: Edge[] = []
  const edgeSet = new Set<string>()

  for (let i = 0; i < steps.length; i++) {
    const step = steps[i]
    const stepId = step.id || `step_${i}`

    const nodeData: StepNodeData = {
      use: step.use || '',
      label: step.label || step.use || stepId,
      params: step.params || {},
      when: step.when,
      onError: step.on_error,
      backend: step.backend,
      status: 'idle',
    }

    nodes.push({
      id: stepId,
      type: 'default',
      position: { x: 0, y: 0 },
      data: nodeData,
    })

    // Scan params for step references to create edges
    const refs = scanForRefs(step.params || {})
    for (const ref of refs) {
      const edgeId = `${ref.stepId}-${stepId}`
      if (!edgeSet.has(edgeId)) {
        edgeSet.add(edgeId)
        edges.push({
          id: edgeId,
          source: ref.stepId,
          target: stepId,
          sourceHandle: ref.attr,
          animated: true,
        })
      }
    }
  }

  const layoutedNodes = autoLayout(nodes, edges)

  return { nodes: layoutedNodes, edges, meta }
}

/** Topological sort of node IDs based on edges */
function topologicalSort(nodeIds: string[], edges: Edge[]): string[] {
  const inDegree = new Map<string, number>()
  const adj = new Map<string, string[]>()

  for (const id of nodeIds) {
    inDegree.set(id, 0)
    adj.set(id, [])
  }

  for (const edge of edges) {
    adj.get(edge.source)?.push(edge.target)
    inDegree.set(edge.target, (inDegree.get(edge.target) || 0) + 1)
  }

  const queue: string[] = []
  for (const [id, deg] of inDegree) {
    if (deg === 0) queue.push(id)
  }

  const sorted: string[] = []
  while (queue.length > 0) {
    const node = queue.shift()!
    sorted.push(node)
    for (const neighbor of adj.get(node) || []) {
      const newDeg = (inDegree.get(neighbor) || 1) - 1
      inDegree.set(neighbor, newDeg)
      if (newDeg === 0) queue.push(neighbor)
    }
  }

  // Append any remaining nodes not reached (cycles or disconnected)
  for (const id of nodeIds) {
    if (!sorted.includes(id)) sorted.push(id)
  }

  return sorted
}

/** Convert Vue Flow DAG back to YAML string */
export function graphToYaml(
  nodes: Node[],
  edges: Edge[],
  meta: PipelineMeta,
): string {
  const nodeIds = nodes.map((n) => n.id)
  const sortedIds = topologicalSort(nodeIds, edges)

  const nodeMap = new Map<string, Node>()
  for (const node of nodes) {
    nodeMap.set(node.id, node)
  }

  const steps: any[] = []

  for (const id of sortedIds) {
    const node = nodeMap.get(id)
    if (!node) continue

    const data = node.data as StepNodeData
    const step: any = {
      id,
      use: data.use,
    }

    if (data.label && data.label !== data.use && data.label !== id) {
      step.label = data.label
    }

    if (data.params && Object.keys(data.params).length > 0) {
      step.params = { ...data.params }
    }

    if (data.when) step.when = data.when
    if (data.onError) step.on_error = data.onError
    if (data.backend) step.backend = data.backend

    steps.push(step)
  }

  const pipeline: any = {
    name: meta.name,
  }

  if (meta.description) pipeline.description = meta.description
  if (meta.crs) pipeline.crs = meta.crs
  if (meta.variables && Object.keys(meta.variables).length > 0) {
    pipeline.variables = meta.variables
  }

  pipeline.steps = steps

  if (meta.outputs && Object.keys(meta.outputs).length > 0) {
    pipeline.outputs = meta.outputs
  }

  return yaml.dump({ pipeline }, { lineWidth: 120, noRefs: true })
}
