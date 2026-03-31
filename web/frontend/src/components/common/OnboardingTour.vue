<script setup lang="ts">
/**
 * OnboardingTour — First-visit guided tour introducing key features.
 *
 * Shows a step-by-step overlay tour on first visit. The tour completion
 * state is persisted in localStorage to avoid showing it again.
 */
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const STORAGE_KEY = 'geopipe-tour-completed'
const isVisible = ref(false)
const currentStep = ref(0)

interface TourStep {
  titleKey: string
  descKey: string
  icon: string
}

const steps: TourStep[] = [
  {
    titleKey: 'tour.welcomeTitle',
    descKey: 'tour.welcomeDesc',
    icon: '🚀',
  },
  {
    titleKey: 'tour.editorTitle',
    descKey: 'tour.editorDesc',
    icon: '🔧',
  },
  {
    titleKey: 'tour.chatTitle',
    descKey: 'tour.chatDesc',
    icon: '🤖',
  },
  {
    titleKey: 'tour.templatesTitle',
    descKey: 'tour.templatesDesc',
    icon: '📦',
  },
  {
    titleKey: 'tour.skillTitle',
    descKey: 'tour.skillDesc',
    icon: '🧠',
  },
  {
    titleKey: 'tour.readyTitle',
    descKey: 'tour.readyDesc',
    icon: '✨',
  },
]

onMounted(() => {
  const completed = localStorage.getItem(STORAGE_KEY)
  if (!completed) {
    isVisible.value = true
  }
})

function nextStep() {
  if (currentStep.value < steps.length - 1) {
    currentStep.value++
  } else {
    completeTour()
  }
}

function prevStep() {
  if (currentStep.value > 0) {
    currentStep.value--
  }
}

function completeTour() {
  isVisible.value = false
  localStorage.setItem(STORAGE_KEY, 'true')
}

function skipTour() {
  completeTour()
}
</script>

<template>
  <transition name="tour-fade">
    <div v-if="isVisible" class="tour-overlay" @click.self="skipTour">
      <div class="tour-card">
        <!-- Progress indicator -->
        <div class="tour-progress">
          <span
            v-for="(_, idx) in steps"
            :key="idx"
            class="progress-dot"
            :class="{ active: idx === currentStep, done: idx < currentStep }"
          />
        </div>

        <!-- Step content -->
        <div class="tour-content">
          <div class="tour-icon">{{ steps[currentStep].icon }}</div>
          <h3 class="tour-title">{{ t(steps[currentStep].titleKey) }}</h3>
          <p class="tour-desc">{{ t(steps[currentStep].descKey) }}</p>
        </div>

        <!-- Actions -->
        <div class="tour-actions">
          <el-button v-if="currentStep > 0" size="small" text @click="prevStep">
            {{ t('tour.prev') }}
          </el-button>
          <el-button size="small" text @click="skipTour">
            {{ t('tour.skip') }}
          </el-button>
          <el-button type="primary" size="small" @click="nextStep">
            {{ currentStep < steps.length - 1 ? t('tour.next') : t('tour.start') }}
          </el-button>
        </div>

        <!-- Step counter -->
        <div class="tour-counter">
          {{ currentStep + 1 }} / {{ steps.length }}
        </div>
      </div>
    </div>
  </transition>
</template>

<style scoped>
.tour-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  backdrop-filter: blur(2px);
}

.tour-card {
  background: var(--gp-bg-elevated, #fff);
  border-radius: 16px;
  padding: 32px 36px;
  max-width: 440px;
  width: 90%;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.2);
  text-align: center;
  position: relative;
}

.tour-progress {
  display: flex;
  justify-content: center;
  gap: 6px;
  margin-bottom: 24px;
}

.progress-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--gp-border-color, #e4e7ed);
  transition: all 0.3s ease;
}

.progress-dot.active {
  background: #409eff;
  transform: scale(1.3);
}

.progress-dot.done {
  background: #67c23a;
}

.tour-content {
  margin-bottom: 28px;
}

.tour-icon {
  font-size: 48px;
  margin-bottom: 16px;
  line-height: 1;
}

.tour-title {
  margin: 0 0 12px;
  font-size: 20px;
  font-weight: 700;
  color: var(--gp-text-primary, #303133);
}

.tour-desc {
  margin: 0;
  font-size: 14px;
  line-height: 1.7;
  color: var(--gp-text-secondary, #606266);
}

.tour-actions {
  display: flex;
  justify-content: center;
  gap: 8px;
}

.tour-counter {
  margin-top: 16px;
  font-size: 12px;
  color: var(--gp-text-muted, #909399);
}

.tour-fade-enter-active,
.tour-fade-leave-active {
  transition: opacity 0.3s ease;
}
.tour-fade-enter-from,
.tour-fade-leave-to {
  opacity: 0;
}
</style>
