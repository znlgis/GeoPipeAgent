/** Pipeline-level metadata */
export interface PipelineMeta {
  name: string
  description?: string
  crs?: string
  variables: Record<string, any>
  outputs: Record<string, string>
}

/** Step node data for Vue Flow */
export interface StepNodeData {
  use: string
  label: string
  params: Record<string, any>
  when?: string
  onError?: string
  backend?: string
  status?: 'idle' | 'running' | 'success' | 'error'
  errorMessage?: string
}

/** Step parameter schema from backend */
export interface StepParamSchema {
  type: string
  required: boolean
  description: string
  default?: any
  enum?: string[]
}

/** Step schema from backend */
export interface StepSchema {
  name: string
  category: string
  description: string
  params: Record<string, StepParamSchema>
  outputs: Record<string, { type: string; description?: string }>
  supports_backend: boolean
  backends?: string[]
  examples?: Array<{ description: string; params: Record<string, any> }>
}

/** Category group */
export interface StepCategory {
  name: string
  label: string
  steps: StepSchema[]
}

/** Pipeline info (saved pipeline) */
export interface PipelineInfo {
  id: string
  name: string
  version: number
  created_at: string
  updated_at: string
}

/** SSE event types */
export type PipelineEventType = 'progress' | 'done' | 'error'

export interface PipelineProgressEvent {
  step_id: string
  status: 'running' | 'success' | 'error'
  message: string
}

export interface PipelineDoneEvent {
  result: Record<string, any>
  total_time: number
}

export interface PipelineErrorEvent {
  code: string
  message: string
  step_id?: string
}
