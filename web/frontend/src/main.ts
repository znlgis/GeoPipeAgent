import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import App from './App.vue'

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
app.mount('#app')
