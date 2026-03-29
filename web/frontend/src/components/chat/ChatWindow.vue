<script setup lang="ts">
import { ref, computed, nextTick, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { VideoPause, MagicStick } from '@element-plus/icons-vue'
import { useChatStore } from '@/stores/chatStore'
import { useSkillStore } from '@/stores/skillStore'
import type { ChatMessage } from '@/types/chat'
import MessageBubble from './MessageBubble.vue'

const emit = defineEmits<{
  (e: 'load-pipeline', yaml: string): void
}>()

const chatStore = useChatStore()
const skillStore = useSkillStore()
const { t } = useI18n()

const inputText = ref('')
const activeMode = ref<'chat' | 'pipeline' | 'analyze'>('chat')
const messageListRef = ref<HTMLElement | null>(null)
const showSkillPopover = ref(false)

const messages = computed<ChatMessage[]>(
  () => chatStore.currentConversation?.messages ?? [],
)

const canSend = computed(
  () => inputText.value.trim().length > 0 && !chatStore.isStreaming,
)

onMounted(() => {
  skillStore.fetchModules()
})

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
    ElMessage.warning(t('chat.selectConversation'))
    return
  }

  const skill = skillStore.skillSettings

  switch (activeMode.value) {
    case 'pipeline':
      chatStore.generatePipeline(text, skill)
      break
    case 'analyze':
      chatStore.analyzeResult({ report: text })
      break
    default:
      chatStore.sendMessage(text, 'chat', skill)
  }

  inputText.value = ''
}

function handleStop() {
  chatStore.stopStreaming()
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

function handleToggleSkill() {
  skillStore.setSkillEnabled(!skillStore.skillEnabled)
}

function handleToggleModule(moduleId: string) {
  skillStore.toggleModule(moduleId)
}
</script>

<template>
  <div class="chat-window">
    <!-- Empty state - enhanced welcome -->
    <div v-if="!chatStore.currentConversation" class="empty-state">
      <div class="welcome-card">
        <div class="welcome-icon">
          <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
          </svg>
        </div>
        <h3 class="welcome-title">{{ t('chat.welcomeTitle') }}</h3>
        <p class="welcome-desc">{{ t('chat.welcomeDesc') }}</p>
        <div class="welcome-hints">
          <div class="hint-item">
            <el-tag size="small" type="primary" effect="plain">{{ t('chat.modeChat') }}</el-tag>
            <span>{{ t('chat.welcomeHint1') }}</span>
          </div>
          <div class="hint-item">
            <el-tag size="small" type="success" effect="plain">{{ t('chat.modePipeline') }}</el-tag>
            <span>{{ t('chat.welcomeHint2') }}</span>
          </div>
          <div class="hint-item">
            <el-tag size="small" type="warning" effect="plain">{{ t('chat.modeAnalyze') }}</el-tag>
            <span>{{ t('chat.welcomeHint3') }}</span>
          </div>
          <div class="hint-item">
            <el-tag size="small" type="info" effect="plain">Skill</el-tag>
            <span>{{ t('chat.welcomeHint4') }}</span>
          </div>
        </div>
      </div>
    </div>

    <template v-else>
      <!-- Message list -->
      <div ref="messageListRef" class="message-list">
        <TransitionGroup name="msg-appear">
          <MessageBubble
            v-for="(msg, index) in messages"
            :key="`msg-${index}`"
            :message="msg"
            @load-yaml="handleLoadYaml"
          />
        </TransitionGroup>

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
        <!-- Mode selector & Skill toggle -->
        <div class="input-controls">
          <div class="controls-left">
            <el-button-group size="small">
              <el-button
                :type="activeMode === 'chat' ? 'primary' : 'default'"
                @click="activeMode = 'chat'"
              >
                {{ t('chat.modeChat') }}
              </el-button>
              <el-button
                :type="activeMode === 'pipeline' ? 'primary' : 'default'"
                @click="activeMode = 'pipeline'"
              >
                {{ t('chat.modePipeline') }}
              </el-button>
              <el-button
                :type="activeMode === 'analyze' ? 'primary' : 'default'"
                @click="activeMode = 'analyze'"
              >
                {{ t('chat.modeAnalyze') }}
              </el-button>
            </el-button-group>

            <!-- Skill toggle with popover -->
            <el-popover
              v-model:visible="showSkillPopover"
              placement="top-start"
              :width="320"
              trigger="click"
            >
              <template #reference>
                <el-button
                  size="small"
                  :type="skillStore.skillEnabled ? 'success' : 'default'"
                  :icon="MagicStick"
                  class="skill-toggle-btn"
                >
                  Skill
                  <el-badge
                    v-if="skillStore.skillEnabled"
                    :value="skillStore.selectedModules.length || skillStore.modules.length"
                    type="success"
                    class="skill-badge"
                  />
                </el-button>
              </template>

              <div class="skill-popover">
                <div class="skill-popover-header">
                  <span class="skill-popover-title">{{ t('skill.enhanceTitle') }}</span>
                  <el-switch
                    :model-value="skillStore.skillEnabled"
                    :active-text="t('skill.enabled')"
                    :inactive-text="t('skill.disabled')"
                    size="small"
                    @change="handleToggleSkill"
                  />
                </div>
                <p class="skill-popover-desc">{{ t('skill.enhanceDesc') }}</p>

                <div v-if="skillStore.skillEnabled" class="skill-module-list">
                  <div
                    v-for="mod in skillStore.modules"
                    :key="mod.id"
                    class="skill-module-item"
                    @click="handleToggleModule(mod.id)"
                  >
                    <el-checkbox
                      :model-value="skillStore.selectedModules.includes(mod.id)"
                      size="small"
                      @click.stop
                      @change="handleToggleModule(mod.id)"
                    >
                      <span class="module-name">{{ mod.name }}</span>
                    </el-checkbox>
                    <span class="module-tokens">~{{ mod.token_estimate }} tokens</span>
                  </div>
                </div>

                <div v-if="skillStore.skillEnabled" class="skill-popover-footer">
                  <span class="token-estimate">
                    {{ t('skill.estimatedTokens') }}: ~{{ skillStore.totalTokenEstimate }}
                  </span>
                </div>
              </div>
            </el-popover>
          </div>

          <!-- Stop button -->
          <transition name="fade">
            <el-button
              v-if="chatStore.isStreaming"
              type="danger"
              size="small"
              :icon="VideoPause"
              @click="handleStop"
            >
              {{ t('chat.stopGenerating') }}
            </el-button>
          </transition>
        </div>

        <div class="input-row">
          <el-input
            v-model="inputText"
            type="textarea"
            :autosize="{ minRows: 1, maxRows: 4 }"
            :placeholder="
              activeMode === 'chat'
                ? t('chat.chatPlaceholder')
                : activeMode === 'pipeline'
                  ? t('chat.pipelinePlaceholder')
                  : t('chat.analyzePlaceholder')
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
            {{ t('chat.send') }}
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
  background: var(--gp-bg-secondary);
  transition: background var(--gp-transition);
}

/* -- Welcome state -- */
.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.welcome-card {
  text-align: center;
  max-width: 420px;
}

.welcome-icon {
  color: var(--gp-text-muted);
  margin-bottom: 16px;
  opacity: 0.6;
}

.welcome-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--gp-text-primary);
  margin: 0 0 8px;
}

.welcome-desc {
  font-size: 14px;
  color: var(--gp-text-muted);
  margin: 0 0 24px;
}

.welcome-hints {
  display: flex;
  flex-direction: column;
  gap: 12px;
  text-align: left;
}

.hint-item {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: var(--gp-text-secondary);
  padding: 10px 14px;
  border-radius: 8px;
  background: var(--gp-bg-primary);
  border: 1px solid var(--gp-border-light);
  transition: background var(--gp-transition), border-color var(--gp-transition);
}

.hint-item .el-tag {
  flex-shrink: 0;
}

/* -- Message list -- */
.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

/* Message appear animation */
.msg-appear-enter-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}
.msg-appear-enter-from {
  opacity: 0;
  transform: translateY(12px);
}

/* -- Input area -- */
.input-area {
  border-top: 1px solid var(--gp-border-color);
  padding: 10px 16px;
  background: var(--gp-bg-primary);
  transition: background var(--gp-transition), border-color var(--gp-transition);
}

.input-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.controls-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.skill-toggle-btn {
  position: relative;
}

.skill-toggle-btn .skill-badge {
  margin-left: 4px;
}

.skill-toggle-btn .skill-badge :deep(.el-badge__content) {
  font-size: 10px;
  height: 14px;
  line-height: 14px;
  padding: 0 4px;
}

.input-row {
  display: flex;
  gap: 8px;
  align-items: flex-end;
}

.input-row :deep(.el-textarea) {
  flex: 1;
}

/* -- Skill popover -- */
.skill-popover {
  padding: 4px 0;
}

.skill-popover-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.skill-popover-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--gp-text-primary);
}

.skill-popover-desc {
  font-size: 12px;
  color: var(--gp-text-muted);
  margin: 0 0 12px;
  line-height: 1.5;
}

.skill-module-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 12px;
}

.skill-module-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s;
}

.skill-module-item:hover {
  background: var(--gp-hover-bg);
}

.module-name {
  font-size: 13px;
  color: var(--gp-text-primary);
}

.module-tokens {
  font-size: 11px;
  color: var(--gp-text-muted);
  flex-shrink: 0;
}

.skill-popover-footer {
  padding-top: 8px;
  border-top: 1px solid var(--gp-border-light);
}

.token-estimate {
  font-size: 12px;
  color: var(--gp-text-secondary);
}

/* Fade transition for stop button */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
