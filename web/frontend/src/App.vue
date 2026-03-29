<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

function handleMenuSelect(index: string) {
  router.push(index)
}
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
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
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
  color: #303133;
  margin: 0;
  margin-right: 40px;
  white-space: nowrap;
}

.nav-menu {
  border-bottom: none;
  flex: 1;
}

.app-main {
  flex: 1;
  overflow: auto;
  padding: 20px;
  background: #f5f7fa;
}
</style>
