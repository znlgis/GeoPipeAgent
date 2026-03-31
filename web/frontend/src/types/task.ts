/** Task-related type definitions. */

export interface TaskStatus {
  id: string
  type: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  message: string
  created_at: string
  updated_at: string
  result: Record<string, any> | null
  error: string | null
}

export interface TaskSubmitResponse {
  task_id: string
  status: string
  message: string
}
