import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import ElementPlus from 'element-plus'
import { ElMessage } from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import enUs from 'element-plus/es/locale/lang/en'
import 'element-plus/dist/index.css'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import axios from 'axios'
import i18n, { getLocale } from './locales'
import App from './App.vue'

// ── Axios global error interceptor ──────────────────────────────────────────

axios.interceptors.response.use(
  (response) => response,
  (error) => {
    const t = i18n.global.t as (key: string) => string
    if (error.response) {
      const status = error.response.status
      const detail = error.response.data?.detail || error.response.statusText
      if (status === 401) {
        ElMessage.error(t('errors.authError'))
      } else if (status === 429) {
        ElMessage.warning(t('errors.rateLimitError'))
      } else if (status === 404) {
        ElMessage.warning(`${t('errors.notFoundError')}: ${detail}`)
      } else if (status >= 500) {
        ElMessage.error(`${t('errors.serverError')}: ${detail}`)
      }
    } else if (error.request) {
      ElMessage.error(t('errors.networkError'))
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
      path: '/templates',
      name: 'TemplateGallery',
      component: () => import('./views/TemplateGallery.vue'),
    },
    {
      path: '/skill',
      name: 'SkillManager',
      component: () => import('./views/SkillManager.vue'),
    },
    {
      path: '/history',
      name: 'ConversationHistory',
      component: () => import('./views/ConversationHistory.vue'),
    },
    {
      path: '/tasks',
      name: 'TaskManager',
      component: () => import('./views/TaskManager.vue'),
    },
  ],
})

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(i18n)
app.use(ElementPlus, { locale: getLocale() === 'en-US' ? enUs : zhCn })

// ── Vue global error handler ────────────────────────────────────────────────

app.config.errorHandler = (err, _instance, info) => {
  console.error(`[Vue Error] ${info}:`, err)
  const t = i18n.global.t as (key: string) => string
  ElMessage.error(t('errors.unexpectedError'))
}

app.mount('#app')
