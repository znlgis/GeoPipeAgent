import { ref, computed } from 'vue'
import { useChatStore } from '@/stores/chatStore'
import { createSSEConnection } from '@/utils/sseClient'
import axios from 'axios'

export interface LlmConfig {
  provider: string
  model: string
  api_key: string
  base_url?: string
  temperature?: number
  max_tokens?: number
}

export function useLlm() {
  const chatStore = useChatStore()
  const config = ref<LlmConfig>({
    provider: '',
    model: '',
    api_key: '',
    base_url: '',
    temperature: 0.7,
    max_tokens: 4096,
  })
  const configLoading = ref(false)

  const isConfigured = computed(() => !!config.value.api_key)

  async function loadConfig() {
    configLoading.value = true
    try {
      const res = await axios.get<LlmConfig>('/api/v1/llm/config')
      config.value = res.data
    } catch (err) {
      console.error('Failed to load LLM config:', err)
    } finally {
      configLoading.value = false
    }
  }

  async function saveConfig(newConfig: LlmConfig) {
    configLoading.value = true
    try {
      const res = await axios.put<LlmConfig>('/api/v1/llm/config', newConfig)
      config.value = res.data
      return true
    } catch (err) {
      console.error('Failed to save LLM config:', err)
      return false
    } finally {
      configLoading.value = false
    }
  }

  /**
   * Send a message with SSE streaming.
   * @param message - The user message text
   * @param mode - 'chat' for conversation, 'generate' for pipeline generation, 'analyze' for result analysis
   */
  function sendMessage(
    message: string,
    mode: 'chat' | 'generate' | 'analyze' = 'chat',
  ) {
    switch (mode) {
      case 'generate':
        chatStore.generatePipeline(message)
        break
      case 'analyze':
        chatStore.analyzeResult({ report: message })
        break
      default:
        chatStore.sendMessage(message, 'chat')
    }
  }

  function stopStreaming() {
    chatStore.stopStreaming()
  }

  return {
    config,
    configLoading,
    isConfigured,
    loadConfig,
    saveConfig,
    sendMessage,
    stopStreaming,
  }
}
