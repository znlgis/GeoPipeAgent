<script setup lang="ts">
import { computed } from 'vue'
import { Upload } from '@element-plus/icons-vue'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import type { ChatMessage } from '@/types/chat'

const props = withDefaults(
  defineProps<{
    message: ChatMessage
    isStreaming?: boolean
  }>(),
  { isStreaming: false },
)

const emit = defineEmits<{
  (e: 'load-yaml', yaml: string): void
}>()

const md = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true,
  highlight(str: string, lang: string): string {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return `<pre class="hljs"><code>${hljs.highlight(str, { language: lang }).value}</code></pre>`
      } catch {
        /* fall through */
      }
    }
    return `<pre class="hljs"><code>${md.utils.escapeHtml(str)}</code></pre>`
  },
})

/** Rendered HTML from markdown content. */
const renderedContent = computed(() => md.render(props.message.content || ''))

/**
 * Extract all YAML code blocks from the message so we can attach
 * "load to editor" buttons below each one.
 */
const yamlBlocks = computed<string[]>(() => {
  const regex = /```yaml\s*\n([\s\S]*?)```/g
  const blocks: string[] = []
  let match: RegExpExecArray | null
  while ((match = regex.exec(props.message.content || '')) !== null) {
    blocks.push(match[1].trim())
  }
  return blocks
})

const formattedTime = computed(() => {
  try {
    const date = new Date(props.message.timestamp)
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
})

function handleLoadYaml(yaml: string) {
  emit('load-yaml', yaml)
}
</script>

<template>
  <div
    class="message-bubble"
    :class="{
      'message-user': message.role === 'user',
      'message-assistant': message.role === 'assistant',
      'message-system': message.role === 'system',
      'message-streaming': isStreaming,
    }"
  >
    <!-- System message -->
    <template v-if="message.role === 'system'">
      <div class="system-content">{{ message.content }}</div>
    </template>

    <!-- User / Assistant message -->
    <template v-else>
      <div class="bubble-wrapper">
        <div class="avatar">
          <el-avatar :size="32">
            {{ message.role === 'user' ? '我' : 'AI' }}
          </el-avatar>
        </div>

        <div class="bubble-body">
          <div class="bubble-content" v-html="renderedContent" />

          <!-- YAML load buttons -->
          <div v-for="(yaml, idx) in yamlBlocks" :key="idx" class="yaml-action">
            <el-button size="small" type="primary" plain :icon="Upload" @click="handleLoadYaml(yaml)">
              加载到编辑器
            </el-button>
          </div>

          <!-- Streaming indicator -->
          <span v-if="isStreaming" class="typing-indicator">
            <span /><span /><span />
          </span>

          <!-- Footer: time + token usage -->
          <div class="bubble-footer">
            <span class="timestamp">{{ formattedTime }}</span>
            <span v-if="message.token_usage" class="token-usage">
              tokens: {{ message.token_usage.prompt + message.token_usage.completion }}
            </span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.message-bubble {
  margin-bottom: 16px;
  display: flex;
}

/* --- Alignment --- */
.message-user {
  justify-content: flex-end;
}
.message-assistant {
  justify-content: flex-start;
}
.message-system {
  justify-content: center;
}

/* --- System --- */
.system-content {
  font-size: 12px;
  color: #909399;
  background: #f4f4f5;
  padding: 4px 12px;
  border-radius: 10px;
  max-width: 80%;
  text-align: center;
}

/* --- Bubble wrapper --- */
.bubble-wrapper {
  display: flex;
  gap: 8px;
  max-width: 80%;
}

.message-user .bubble-wrapper {
  flex-direction: row-reverse;
}

/* --- Avatar --- */
.message-user .avatar :deep(.el-avatar) {
  background-color: #409eff;
}
.message-assistant .avatar :deep(.el-avatar) {
  background-color: #67c23a;
}

/* --- Bubble body --- */
.bubble-body {
  padding: 10px 14px;
  border-radius: 10px;
  line-height: 1.6;
  word-break: break-word;
  min-width: 60px;
}

.message-user .bubble-body {
  background-color: #409eff;
  color: #fff;
  border-top-right-radius: 2px;
}

.message-assistant .bubble-body {
  background-color: #f5f7fa;
  color: #303133;
  border-top-left-radius: 2px;
}

/* --- Markdown content --- */
.bubble-content :deep(p) {
  margin: 0 0 8px;
}
.bubble-content :deep(p:last-child) {
  margin-bottom: 0;
}
.bubble-content :deep(pre.hljs) {
  border-radius: 6px;
  padding: 12px;
  overflow-x: auto;
  font-size: 13px;
  margin: 8px 0;
}
.message-user .bubble-content :deep(pre.hljs) {
  background: rgba(255, 255, 255, 0.15);
}
.message-assistant .bubble-content :deep(pre.hljs) {
  background: #1e1e1e;
  color: #d4d4d4;
}
.bubble-content :deep(code) {
  font-family: 'Fira Code', 'Consolas', monospace;
}
.bubble-content :deep(ul),
.bubble-content :deep(ol) {
  padding-left: 20px;
  margin: 4px 0;
}

/* --- YAML action --- */
.yaml-action {
  margin-top: 6px;
}

/* --- Typing indicator --- */
.typing-indicator {
  display: inline-flex;
  gap: 4px;
  padding-top: 4px;
}
.typing-indicator span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #909399;
  animation: blink 1.4s infinite both;
}
.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}
.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}
@keyframes blink {
  0%, 80%, 100% { opacity: 0.3; }
  40% { opacity: 1; }
}

/* --- Footer --- */
.bubble-footer {
  display: flex;
  gap: 8px;
  margin-top: 4px;
  font-size: 11px;
  opacity: 0.6;
}
.message-user .bubble-footer {
  justify-content: flex-end;
}
</style>
