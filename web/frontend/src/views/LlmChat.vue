<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { useChatStore } from '@/stores/chatStore'

const chatStore = useChatStore()
const inputMessage = ref('')
const chatContainerRef = ref<HTMLElement>()

async function handleSend() {
  const msg = inputMessage.value.trim()
  if (!msg || chatStore.isStreaming) return
  inputMessage.value = ''
  chatStore.sendMessage(msg)
  await nextTick()
  scrollToBottom()
}

function scrollToBottom() {
  if (chatContainerRef.value) {
    chatContainerRef.value.scrollTop = chatContainerRef.value.scrollHeight
  }
}
</script>

<template>
  <div class="llm-chat">
    <el-row :gutter="16" class="chat-layout">
      <el-col :span="6">
        <el-card shadow="never" class="panel">
          <template #header>
            <div class="panel-header">
              <span>对话列表</span>
              <el-button size="small" type="primary">新建对话</el-button>
            </div>
          </template>
          <div v-if="chatStore.conversations.length > 0" class="conversation-list">
            <div
              v-for="conv in chatStore.conversations"
              :key="conv.id"
              class="conversation-item"
              :class="{ active: chatStore.currentConversation?.id === conv.id }"
              @click="chatStore.loadConversation(conv.id)"
            >
              <el-text truncated>{{ conv.title }}</el-text>
              <el-text type="info" size="small">
                {{ conv.message_count }} 条消息
              </el-text>
            </div>
          </div>
          <el-empty v-else description="暂无对话" :image-size="60" />
        </el-card>
      </el-col>
      <el-col :span="18">
        <el-card shadow="never" class="panel chat-panel">
          <template #header>
            <span>{{ chatStore.currentConversation?.title || 'AI 对话' }}</span>
          </template>
          <div class="chat-content">
            <div ref="chatContainerRef" class="messages-container">
              <template v-if="chatStore.currentConversation">
                <div
                  v-for="(msg, idx) in chatStore.currentConversation.messages"
                  :key="idx"
                  class="message"
                  :class="msg.role"
                >
                  <div class="message-bubble">
                    <el-text v-if="msg.role === 'user'" class="message-text">
                      {{ msg.content }}
                    </el-text>
                    <div v-else class="message-text" v-html="msg.content" />
                  </div>
                </div>
                <div v-if="chatStore.isStreaming" class="message assistant">
                  <div class="message-bubble">
                    <div class="message-text">
                      {{ chatStore.streamingContent }}
                      <span class="typing-cursor">|</span>
                    </div>
                  </div>
                </div>
              </template>
              <el-empty v-else description="选择或创建对话开始" />
            </div>
            <div class="input-area">
              <el-input
                v-model="inputMessage"
                type="textarea"
                :rows="2"
                placeholder="输入消息..."
                :disabled="chatStore.isStreaming"
                @keydown.enter.ctrl="handleSend"
              />
              <el-button
                type="primary"
                :loading="chatStore.isStreaming"
                :disabled="!inputMessage.trim()"
                @click="handleSend"
              >
                发送
              </el-button>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.llm-chat {
  height: calc(100vh - 120px);
}

.chat-layout {
  height: 100%;
}

.panel {
  height: 100%;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chat-panel :deep(.el-card__body) {
  height: calc(100% - 56px);
  padding: 0;
  display: flex;
  flex-direction: column;
}

.chat-content {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.conversation-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.conversation-item {
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.conversation-item:hover {
  background: #f5f7fa;
}

.conversation-item.active {
  background: #ecf5ff;
}

.message {
  margin-bottom: 16px;
  display: flex;
}

.message.user {
  justify-content: flex-end;
}

.message.assistant {
  justify-content: flex-start;
}

.message-bubble {
  max-width: 70%;
  padding: 10px 14px;
  border-radius: 8px;
}

.message.user .message-bubble {
  background: #409eff;
  color: #fff;
}

.message.assistant .message-bubble {
  background: #f4f4f5;
  color: #303133;
}

.message-text {
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.6;
}

.typing-cursor {
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  50% {
    opacity: 0;
  }
}

.input-area {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid #e4e7ed;
  align-items: flex-end;
}

.input-area .el-input {
  flex: 1;
}
</style>
