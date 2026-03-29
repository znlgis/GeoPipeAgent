import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'
import type {
  Conversation,
  ConversationSummary,
  ChatMessage,
} from '@/types/chat'
import { createSSEConnection } from '@/utils/sseClient'

export const useChatStore = defineStore('chat', () => {
  // --- State ---
  const conversations = ref<ConversationSummary[]>([])
  const currentConversation = ref<Conversation | null>(null)
  const isStreaming = ref(false)
  const streamingContent = ref('')

  let activeController: AbortController | null = null

  // --- Actions ---
  async function fetchConversations() {
    try {
      const response = await axios.get<ConversationSummary[]>(
        '/api/llm/conversations',
      )
      conversations.value = response.data
    } catch (error) {
      console.error('Failed to fetch conversations:', error)
    }
  }

  async function loadConversation(id: string) {
    try {
      const response = await axios.get<Conversation>(
        `/api/llm/conversations/${id}`,
      )
      currentConversation.value = response.data
    } catch (error) {
      console.error('Failed to load conversation:', error)
    }
  }

  function sendMessage(message: string, mode: 'chat' | 'pipeline' = 'chat') {
    if (!currentConversation.value) return

    // Add user message locally
    const userMessage: ChatMessage = {
      role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    }
    currentConversation.value.messages.push(userMessage)

    isStreaming.value = true
    streamingContent.value = ''

    // Cancel any existing stream
    if (activeController) {
      activeController.abort()
    }

    const url =
      mode === 'pipeline'
        ? '/api/llm/chat'
        : '/api/llm/chat'

    activeController = createSSEConnection(
      url,
      { message, conversation_id: currentConversation.value.id },
      {
        onMessage: (event, data) => {
          if (event === 'chunk' && data.content) {
            streamingContent.value += data.content
          } else if (event === 'done') {
            // Finalize the assistant message
            const assistantMessage: ChatMessage = {
              role: 'assistant',
              content: streamingContent.value,
              timestamp: new Date().toISOString(),
              token_usage: data.total_tokens
                ? { prompt: 0, completion: data.total_tokens }
                : undefined,
              metadata: data.result,
            }
            currentConversation.value?.messages.push(assistantMessage)
            streamingContent.value = ''
            isStreaming.value = false
          }
        },
        onError: (error) => {
          console.error('SSE error:', error)
          isStreaming.value = false
          streamingContent.value = ''
        },
        onDone: () => {
          isStreaming.value = false
          activeController = null
        },
      },
    )
  }

  async function deleteConversation(id: string) {
    try {
      await axios.delete(`/api/llm/conversations/${id}`)
      conversations.value = conversations.value.filter((c) => c.id !== id)
      if (currentConversation.value?.id === id) {
        currentConversation.value = null
      }
    } catch (error) {
      console.error('Failed to delete conversation:', error)
    }
  }

  function generatePipeline(description: string) {
    isStreaming.value = true
    streamingContent.value = ''

    if (activeController) {
      activeController.abort()
    }

    activeController = createSSEConnection(
      '/api/llm/generate-pipeline',
      { description },
      {
        onMessage: (event, data) => {
          if (event === 'chunk' && data.content) {
            streamingContent.value += data.content
          } else if (event === 'done') {
            isStreaming.value = false
          }
        },
        onError: (error) => {
          console.error('Pipeline generation error:', error)
          isStreaming.value = false
          streamingContent.value = ''
        },
        onDone: () => {
          isStreaming.value = false
          activeController = null
        },
      },
    )
  }

  function analyzeResult(report: Record<string, any>) {
    isStreaming.value = true
    streamingContent.value = ''

    if (activeController) {
      activeController.abort()
    }

    activeController = createSSEConnection(
      '/api/llm/analyze-result',
      { report },
      {
        onMessage: (event, data) => {
          if (event === 'chunk' && data.content) {
            streamingContent.value += data.content
          } else if (event === 'done') {
            isStreaming.value = false
          }
        },
        onError: (error) => {
          console.error('Result analysis error:', error)
          isStreaming.value = false
          streamingContent.value = ''
        },
        onDone: () => {
          isStreaming.value = false
          activeController = null
        },
      },
    )
  }

  function stopStreaming() {
    if (activeController) {
      activeController.abort()
      activeController = null
    }
    isStreaming.value = false
    streamingContent.value = ''
  }

  return {
    // State
    conversations,
    currentConversation,
    isStreaming,
    streamingContent,
    // Actions
    fetchConversations,
    loadConversation,
    sendMessage,
    deleteConversation,
    generatePipeline,
    analyzeResult,
    stopStreaming,
  }
})
