<script setup lang="ts">
import { ref, computed, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useChatStore } from '@/stores/chatStore'
import type { ChatMessage } from '@/types/chat'
import MessageBubble from './MessageBubble.vue'

const emit = defineEmits<{
  (e: 'load-pipeline', yaml: string): void
}>()

const chatStore = useChatStore()

const inputText = ref('')
const activeMode = ref<'chat' | 'pipeline' | 'analyze'>('chat')
const messageListRef = ref<HTMLElement | null>(null)

const messages = computed<ChatMessage[]>(
  () => chatStore.currentConversation?.messages ?? [],
)

const canSend = computed(
  () => inputText.value.trim().length > 0 && !chatStore.isStreaming,
)

function scrollToBottom() {
  nextTick(() => {
    if (messageListRef.value) {
      messageListRef.value.scrollTop = messageListRef.value.scrollHeight
    }
  })
}

// Auto-scroll when messages change or streaming content updates
watch(
  () => [messages.value.length, chatStore.streamingContent],
  () => scrollToBottom(),
)

function send() {
  const text = inputText.value.trim()
  if (!text) return

  if (!chatStore.currentConversation) {
    ElMessage.warning('请先选择或创建一个对话')
    return
  }

  switch (activeMode.value) {
    case 'pipeline':
      chatStore.generatePipeline(text)
      break
    case 'analyze':
      chatStore.analyzeResult({ report: text })
      break
    default:
      chatStore.sendMessage(text, 'chat')
  }

  inputText.value = ''
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    send()
  }
}

function handleLoadYaml(yaml: string) {
  emit('load-pipeline', yaml)
}
</script>

<template>
  <div class="chat-window">
    <!-- Empty state -->
    <div v-if="!chatStore.currentConversation" class="empty-state">
      <el-empty description="暂无对话">
        <template #image>
          <span class="empty-icon">💬</span>
        </template>
      </el-empty>
    </div>

    <template v-else>
      <!-- Message list -->
      <div ref="messageListRef" class="message-list">
        <MessageBubble
          v-for="(msg, index) in messages"
          :key="index"
          :message="msg"
          @load-yaml="handleLoadYaml"
        />

        <!-- Streaming partial message -->
        <MessageBubble
          v-if="chatStore.isStreaming && chatStore.streamingContent"
          :message="{
            role: 'assistant',
            content: chatStore.streamingContent,
            timestamp: new Date().toISOString(),
          }"
          :is-streaming="true"
          @load-yaml="handleLoadYaml"
        />
      </div>

      <!-- Input area -->
      <div class="input-area">
        <!-- Mode selector -->
        <div class="mode-selector">
          <el-button-group size="small">
            <el-button
              :type="activeMode === 'chat' ? 'primary' : 'default'"
              @click="activeMode = 'chat'"
            >
              对话
            </el-button>
            <el-button
              :type="activeMode === 'pipeline' ? 'primary' : 'default'"
              @click="activeMode = 'pipeline'"
            >
              生成流水线
            </el-button>
            <el-button
              :type="activeMode === 'analyze' ? 'primary' : 'default'"
              @click="activeMode = 'analyze'"
            >
              分析结果
            </el-button>
          </el-button-group>
        </div>

        <div class="input-row">
          <el-input
            v-model="inputText"
            type="textarea"
            :autosize="{ minRows: 1, maxRows: 4 }"
            :placeholder="
              activeMode === 'chat'
                ? '输入消息...'
                : activeMode === 'pipeline'
                  ? '描述你想要的流水线...'
                  : '粘贴执行结果进行分析...'
            "
            :disabled="chatStore.isStreaming"
            @keydown="handleKeydown"
          />
          <el-button
            type="primary"
            :disabled="!canSend"
            :loading="chatStore.isStreaming"
            @click="send"
          >
            发送
          </el-button>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.chat-window {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}
.empty-icon {
  font-size: 48px;
}

/* --- Message list --- */
.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

/* --- Input area --- */
.input-area {
  border-top: 1px solid #e4e7ed;
  padding: 12px 16px;
  background: #fff;
}

.mode-selector {
  margin-bottom: 8px;
}

.input-row {
  display: flex;
  gap: 8px;
  align-items: flex-end;
}

.input-row :deep(.el-textarea) {
  flex: 1;
}
</style>
