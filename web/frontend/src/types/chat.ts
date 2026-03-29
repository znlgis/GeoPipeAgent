export interface TokenUsage {
  prompt: number
  completion: number
}

export interface ChatMessage {
  role: 'system' | 'user' | 'assistant'
  content: string
  timestamp: string
  token_usage?: TokenUsage
  metadata?: Record<string, any>
}

export interface Conversation {
  id: string
  title: string
  created_at: string
  updated_at: string
  config: Record<string, any>
  messages: ChatMessage[]
}

export interface ConversationSummary {
  id: string
  title: string
  created_at: string
  updated_at: string
  message_count: number
}

export type LlmEventType = 'chunk' | 'done' | 'error'

export interface LlmChunkEvent {
  content: string
  token: number
}

export interface LlmDoneEvent {
  result: Record<string, any>
  total_tokens: number
}

export interface LlmErrorEvent {
  code: string
  message: string
}
