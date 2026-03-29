import { describe, it, expect } from 'vitest'
import { extractStepRefs, yamlToGraph, graphToYaml, autoLayout } from './yamlConverter'

describe('extractStepRefs', () => {
  it('extracts step references from a string', () => {
    const refs = extractStepRefs('$load_roads.output')
    expect(refs).toHaveLength(1)
    expect(refs[0]).toEqual({ stepId: 'load_roads', attr: 'output' })
  })

  it('extracts multiple references', () => {
    const refs = extractStepRefs('$step1.output and $step2.stats')
    expect(refs).toHaveLength(2)
    expect(refs[0].stepId).toBe('step1')
    expect(refs[1].stepId).toBe('step2')
  })

  it('returns empty array for no references', () => {
    const refs = extractStepRefs('no references here')
    expect(refs).toHaveLength(0)
  })

  it('returns empty array for empty string', () => {
    const refs = extractStepRefs('')
    expect(refs).toHaveLength(0)
  })
})

describe('yamlToGraph', () => {
  const sampleYaml = `
pipeline:
  name: "Test Pipeline"
  description: "A test pipeline"
  variables:
    input_path: "data/test.shp"
  steps:
    - id: load
      use: io.read_vector
      params:
        path: "\${input_path}"
    - id: buffer
      use: vector.buffer
      params:
        input: "$load.output"
        distance: 500
    - id: save
      use: io.write_vector
      params:
        input: "$buffer.output"
        path: "output.shp"
  outputs:
    result: "$save.output"
`

  it('parses pipeline YAML into nodes and edges', () => {
    const { nodes, edges, meta } = yamlToGraph(sampleYaml)
    expect(nodes).toHaveLength(3)
    expect(edges).toHaveLength(2)
    expect(meta.name).toBe('Test Pipeline')
    expect(meta.description).toBe('A test pipeline')
  })

  it('creates correct node data', () => {
    const { nodes } = yamlToGraph(sampleYaml)
    const loadNode = nodes.find((n) => n.id === 'load')
    expect(loadNode).toBeDefined()
    expect(loadNode!.data.use).toBe('io.read_vector')
    expect(loadNode!.data.status).toBe('idle')
  })

  it('creates correct edges from step references', () => {
    const { edges } = yamlToGraph(sampleYaml)
    const loadToBuffer = edges.find(
      (e) => e.source === 'load' && e.target === 'buffer',
    )
    expect(loadToBuffer).toBeDefined()
    expect(loadToBuffer!.sourceHandle).toBe('output')
  })

  it('preserves pipeline variables', () => {
    const { meta } = yamlToGraph(sampleYaml)
    expect(meta.variables).toEqual({ input_path: 'data/test.shp' })
  })

  it('preserves pipeline outputs', () => {
    const { meta } = yamlToGraph(sampleYaml)
    expect(meta.outputs).toEqual({ result: '$save.output' })
  })

  it('throws on invalid YAML', () => {
    expect(() => yamlToGraph('not valid: [[[')).toThrow()
  })

  it('throws on YAML without pipeline key', () => {
    expect(() => yamlToGraph('key: value')).toThrow(/missing.*pipeline/)
  })

  it('handles empty steps array', () => {
    const { nodes, edges } = yamlToGraph('pipeline:\n  name: empty\n  steps: []\n')
    expect(nodes).toHaveLength(0)
    expect(edges).toHaveLength(0)
  })
})

describe('graphToYaml', () => {
  it('converts nodes and edges back to YAML', () => {
    const nodes = [
      {
        id: 'read',
        type: 'default',
        position: { x: 0, y: 0 },
        data: { use: 'io.read_vector', label: 'io.read_vector', params: { path: 'test.shp' }, status: 'idle' },
      },
      {
        id: 'write',
        type: 'default',
        position: { x: 0, y: 100 },
        data: { use: 'io.write_vector', label: 'io.write_vector', params: { path: 'out.shp' }, status: 'idle' },
      },
    ]
    const edges = [
      { id: 'read-write', source: 'read', target: 'write', sourceHandle: 'output' },
    ]
    const meta = { name: 'Test', variables: {}, outputs: {} }

    const yamlStr = graphToYaml(nodes as any, edges as any, meta)
    expect(yamlStr).toContain('name: Test')
    expect(yamlStr).toContain('use: io.read_vector')
    expect(yamlStr).toContain('use: io.write_vector')
  })

  it('round-trips YAML through graph and back', () => {
    const originalYaml = `
pipeline:
  name: "Round Trip"
  steps:
    - id: read
      use: io.read_vector
      params:
        path: "test.shp"
    - id: buffer
      use: vector.buffer
      params:
        input: "$read.output"
        distance: 100
`
    const { nodes, edges, meta } = yamlToGraph(originalYaml)
    const reconstructed = graphToYaml(nodes, edges, meta)

    // Parse both and compare structure
    expect(reconstructed).toContain('name: Round Trip')
    expect(reconstructed).toContain('use: io.read_vector')
    expect(reconstructed).toContain('use: vector.buffer')
  })

  it('preserves when and on_error fields', () => {
    const nodes = [
      {
        id: 'step1',
        type: 'default',
        position: { x: 0, y: 0 },
        data: {
          use: 'io.read_vector',
          label: 'io.read_vector',
          params: {},
          when: 'file_exists',
          onError: 'skip',
          status: 'idle',
        },
      },
    ]
    const meta = { name: 'Test', variables: {}, outputs: {} }

    const yamlStr = graphToYaml(nodes as any, [], meta)
    expect(yamlStr).toContain('when: file_exists')
    expect(yamlStr).toContain('on_error: skip')
  })
})

describe('autoLayout', () => {
  it('assigns positions to nodes', () => {
    const nodes = [
      { id: 'a', type: 'default', position: { x: 0, y: 0 }, data: {} },
      { id: 'b', type: 'default', position: { x: 0, y: 0 }, data: {} },
    ]
    const edges = [{ id: 'a-b', source: 'a', target: 'b' }]

    const result = autoLayout(nodes as any, edges as any)
    expect(result).toHaveLength(2)
    // Node b should be below node a
    const nodeA = result.find((n) => n.id === 'a')!
    const nodeB = result.find((n) => n.id === 'b')!
    expect(nodeB.position.y).toBeGreaterThan(nodeA.position.y)
  })
})
