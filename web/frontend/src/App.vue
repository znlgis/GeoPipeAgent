<script setup lang="ts">
import { useRouter } from 'vue-router'
import { ref, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Sunny, Moon } from '@element-plus/icons-vue'
import { setLocale, getLocale } from './locales'
import OnboardingTour from './components/common/OnboardingTour.vue'

const router = useRouter()
const { t } = useI18n()

function handleMenuSelect(index: string) {
  router.push(index)
}

// --- Dark Theme ---
const isDark = ref(false)

function toggleTheme() {
  isDark.value = !isDark.value
}

watch(isDark, (dark) => {
  document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light')
  if (dark) {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }
  localStorage.setItem('geopipe-theme', dark ? 'dark' : 'light')
})

onMounted(() => {
  const saved = localStorage.getItem('geopipe-theme')
  if (saved === 'dark') {
    isDark.value = true
  }
})

// --- i18n ---
const currentLocale = ref(getLocale())

function toggleLocale() {
  const newLocale = currentLocale.value === 'zh-CN' ? 'en-US' : 'zh-CN'
  setLocale(newLocale as 'zh-CN' | 'en-US')
  currentLocale.value = newLocale
}
</script>

<template>
  <el-container class="app-container">
    <el-header class="app-header">
      <div class="header-content">
        <h1 class="app-title">
          <span class="title-icon">&#9670;</span>
          GeoPipeAgent
        </h1>
        <el-menu
          :default-active="$route.path"
          mode="horizontal"
          :router="true"
          class="nav-menu"
          @select="handleMenuSelect"
        >
          <el-menu-item index="/">{{ t('nav.pipelineEditor') }}</el-menu-item>
          <el-menu-item index="/chat">{{ t('nav.aiChat') }}</el-menu-item>
          <el-menu-item index="/templates">{{ t('nav.templates') }}</el-menu-item>
          <el-menu-item index="/skill">{{ t('nav.skillManager') }}</el-menu-item>
          <el-menu-item index="/history">{{ t('nav.history') }}</el-menu-item>
          <el-menu-item index="/tasks">{{ t('nav.tasks') }}</el-menu-item>
        </el-menu>
        <div class="header-actions">
          <el-tooltip :content="isDark ? 'Light Mode' : 'Dark Mode'" placement="bottom">
            <el-button
              :icon="isDark ? Sunny : Moon"
              circle
              size="small"
              class="theme-toggle"
              @click="toggleTheme"
            />
          </el-tooltip>
          <el-tooltip :content="currentLocale === 'zh-CN' ? 'English' : '中文'" placement="bottom">
            <el-button
              size="small"
              class="locale-toggle"
              @click="toggleLocale"
            >
              {{ currentLocale === 'zh-CN' ? 'EN' : '中' }}
            </el-button>
          </el-tooltip>
        </div>
      </div>
    </el-header>
    <el-main class="app-main">
      <router-view v-slot="{ Component }">
        <transition name="page-fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </el-main>
    <OnboardingTour />
  </el-container>
</template>

<style>
html,
body,
#app {
  margin: 0;
  padding: 0;
  height: 100%;
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB',
    'Microsoft YaHei', Arial, sans-serif;
}

/* ── CSS Custom Properties for theming ── */
:root {
  --gp-bg-primary: #ffffff;
  --gp-bg-secondary: #f5f7fa;
  --gp-bg-elevated: #ffffff;
  --gp-text-primary: #303133;
  --gp-text-secondary: #606266;
  --gp-text-muted: #909399;
  --gp-border-color: #e4e7ed;
  --gp-border-light: #ebeef5;
  --gp-shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.08);
  --gp-shadow-md: 0 2px 8px rgba(0, 0, 0, 0.12);
  --gp-hover-bg: #f5f7fa;
  --gp-active-bg: #ecf5ff;
  --gp-code-bg: #1e1e1e;
  --gp-transition: 0.2s ease;
}

html.dark {
  --gp-bg-primary: #1d1e1f;
  --gp-bg-secondary: #141414;
  --gp-bg-elevated: #262727;
  --gp-text-primary: #e5eaf3;
  --gp-text-secondary: #cfd3dc;
  --gp-text-muted: #a3a6ad;
  --gp-border-color: #414243;
  --gp-border-light: #363637;
  --gp-shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.2);
  --gp-shadow-md: 0 2px 8px rgba(0, 0, 0, 0.3);
  --gp-hover-bg: #2a2b2c;
  --gp-active-bg: #1a3a5c;
  --gp-code-bg: #0d1117;

  /* Element Plus dark mode overrides */
  --el-bg-color: #1d1e1f;
  --el-bg-color-overlay: #262727;
  --el-bg-color-page: #141414;
  --el-text-color-primary: #e5eaf3;
  --el-text-color-regular: #cfd3dc;
  --el-text-color-secondary: #a3a6ad;
  --el-text-color-placeholder: #8d9095;
  --el-border-color: #414243;
  --el-border-color-light: #363637;
  --el-border-color-lighter: #2e2e2f;
  --el-fill-color: #262727;
  --el-fill-color-light: #1d1e1f;
  --el-fill-color-lighter: #262727;
  --el-fill-color-blank: #1d1e1f;
  --el-mask-color: rgba(0, 0, 0, 0.8);
  color-scheme: dark;
}

/* ── Page transition ── */
.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.page-fade-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.page-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

/* ── Smooth scrollbar ── */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: var(--gp-text-muted);
  border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
  background: var(--gp-text-secondary);
}
</style>

<style scoped>
.app-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  display: flex;
  align-items: center;
  background: var(--gp-bg-primary);
  border-bottom: 1px solid var(--gp-border-color);
  padding: 0 20px;
  height: 56px;
  box-shadow: var(--gp-shadow-sm);
  z-index: 100;
  transition: background var(--gp-transition), border-color var(--gp-transition);
}

.header-content {
  display: flex;
  align-items: center;
  width: 100%;
}

.app-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--gp-text-primary);
  margin: 0;
  margin-right: 32px;
  white-space: nowrap;
  display: flex;
  align-items: center;
  gap: 6px;
  letter-spacing: -0.3px;
  transition: color var(--gp-transition);
}

.title-icon {
  color: #409eff;
  font-size: 14px;
}

.nav-menu {
  border-bottom: none;
  flex: 1;
  background: transparent;
}

.nav-menu :deep(.el-menu-item) {
  transition: color 0.15s, border-color 0.15s;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.theme-toggle,
.locale-toggle {
  flex-shrink: 0;
}

.app-main {
  flex: 1;
  overflow: auto;
  padding: 16px;
  background: var(--gp-bg-secondary);
  transition: background var(--gp-transition);
}
</style>
