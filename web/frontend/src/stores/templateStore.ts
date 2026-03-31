import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'
import type { TemplateInfo, TemplateDetail } from '@/types/template'

export const useTemplateStore = defineStore('template', () => {
  const templates = ref<TemplateInfo[]>([])
  const currentTemplate = ref<TemplateDetail | null>(null)
  const loading = ref(false)

  async function fetchTemplates() {
    loading.value = true
    try {
      const response = await axios.get<TemplateInfo[]>('/api/template/list')
      templates.value = response.data
    } catch (error) {
      console.error('Failed to fetch templates:', error)
    } finally {
      loading.value = false
    }
  }

  async function loadTemplate(templateId: string): Promise<TemplateDetail | null> {
    loading.value = true
    try {
      const response = await axios.get<TemplateDetail>(`/api/template/${templateId}`)
      currentTemplate.value = response.data
      return response.data
    } catch (error) {
      console.error('Failed to load template:', error)
      return null
    } finally {
      loading.value = false
    }
  }

  return {
    templates,
    currentTemplate,
    loading,
    fetchTemplates,
    loadTemplate,
  }
})
