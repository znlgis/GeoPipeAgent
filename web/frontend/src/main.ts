import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import ElementPlus from 'element-plus'
import { ElMessage } from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import axios from 'axios'
import App from './App.vue'

// ── Axios global error interceptor ──────────────────────────────────────────

axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      const status = error.response.status
      const detail = error.response.data?.detail || error.response.statusText
      if (status === 401) {
        ElMessage.error('认证失败，请检查 API Key 配置')
      } else if (status === 429) {
        ElMessage.warning('请求过于频繁，请稍后重试')
      } else if (status === 404) {
        ElMessage.warning(`资源未找到: ${detail}`)
      } else if (status >= 500) {
        ElMessage.error(`服务器错误: ${detail}`)
      }
    } else if (error.request) {
      ElMessage.error('网络连接失败，请检查后端服务是否启动')
    }
    return Promise.reject(error)
  },
)

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'PipelineEditor',
      component: () => import('./views/PipelineEditor.vue'),
    },
    {
      path: '/chat',
      name: 'LlmChat',
      component: () => import('./views/LlmChat.vue'),
    },
    {
      path: '/history',
      name: 'ConversationHistory',
      component: () => import('./views/ConversationHistory.vue'),
    },
  ],
})

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: zhCn })

// ── Vue global error handler ────────────────────────────────────────────────

app.config.errorHandler = (err, _instance, info) => {
  console.error(`[Vue Error] ${info}:`, err)
  ElMessage.error('发生了一个意外错误，请刷新页面重试')
}

app.mount('#app')
