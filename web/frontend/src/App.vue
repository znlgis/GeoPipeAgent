<script setup lang="ts">
import { useRouter } from 'vue-router'
import { ref, onMounted, watch } from 'vue'
import { Sunny, Moon } from '@element-plus/icons-vue'

const router = useRouter()

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
  // Element Plus dark mode
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
</script>

<template>
  <el-container class="app-container">
    <el-header class="app-header">
      <div class="header-content">
        <h1 class="app-title">GeoPipeAgent</h1>
        <el-menu
          :default-active="$route.path"
          mode="horizontal"
          :router="true"
          class="nav-menu"
          @select="handleMenuSelect"
        >
          <el-menu-item index="/">流程编辑器</el-menu-item>
          <el-menu-item index="/chat">AI 对话</el-menu-item>
          <el-menu-item index="/history">历史记录</el-menu-item>
        </el-menu>
        <el-button
          :icon="isDark ? Sunny : Moon"
          circle
          size="small"
          class="theme-toggle"
          @click="toggleTheme"
        />
      </div>
    </el-header>
    <el-main class="app-main">
      <router-view />
    </el-main>
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
  height: 60px;
}

.header-content {
  display: flex;
  align-items: center;
  width: 100%;
}

.app-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--gp-text-primary);
  margin: 0;
  margin-right: 40px;
  white-space: nowrap;
}

.nav-menu {
  border-bottom: none;
  flex: 1;
  background: transparent;
}

.theme-toggle {
  margin-left: 12px;
  flex-shrink: 0;
}

.app-main {
  flex: 1;
  overflow: auto;
  padding: 20px;
  background: var(--gp-bg-secondary);
}
</style>
