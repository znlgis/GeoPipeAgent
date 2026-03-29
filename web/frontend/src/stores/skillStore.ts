import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'
import type {
  SkillModule,
  SkillContentResponse,
  SkillSettings,
  SkillGenerateResponse,
  SkillImportRequest,
  SkillImportUrlRequest,
  SkillImportResponse,
} from '@/types/skill'

export const useSkillStore = defineStore('skill', () => {
  // --- State ---
  const modules = ref<SkillModule[]>([])
  const contents = ref<Map<string, SkillContentResponse>>(new Map())
  const isLoading = ref(false)
  const isGenerating = ref(false)
  const isImporting = ref(false)

  // Skill settings for chat (persisted in localStorage)
  const skillEnabled = ref<boolean>(loadSetting('geopipe-skill-enabled', false))
  const selectedModules = ref<string[]>(loadSetting('geopipe-skill-modules', []))

  // --- Computed ---
  const totalTokenEstimate = computed(() => {
    if (!skillEnabled.value) return 0
    const activeModules = selectedModules.value.length > 0
      ? selectedModules.value
      : modules.value.map((m) => m.id)
    return modules.value
      .filter((m) => activeModules.includes(m.id))
      .reduce((sum, m) => sum + m.token_estimate, 0)
  })

  const skillSettings = computed<SkillSettings>(() => ({
    enabled: skillEnabled.value,
    modules: selectedModules.value.length > 0 ? selectedModules.value : [],
  }))

  // --- Actions ---

  async function fetchModules() {
    try {
      isLoading.value = true
      const response = await axios.get<{ modules: SkillModule[] }>('/api/skill/modules')
      modules.value = response.data.modules

      // If no modules selected yet, default to all
      if (selectedModules.value.length === 0) {
        selectedModules.value = modules.value.map((m) => m.id)
        saveSetting('geopipe-skill-modules', selectedModules.value)
      }
    } catch (error) {
      console.error('Failed to fetch skill modules:', error)
    } finally {
      isLoading.value = false
    }
  }

  async function fetchContent(moduleId: string) {
    try {
      isLoading.value = true
      const response = await axios.get<SkillContentResponse>(`/api/skill/content/${moduleId}`)
      contents.value.set(moduleId, response.data)
    } catch (error) {
      console.error(`Failed to fetch skill content for ${moduleId}:`, error)
    } finally {
      isLoading.value = false
    }
  }

  async function fetchAllContent() {
    try {
      isLoading.value = true
      const response = await axios.get<SkillContentResponse[]>('/api/skill/content')
      for (const item of response.data) {
        contents.value.set(item.module, item)
      }
    } catch (error) {
      console.error('Failed to fetch all skill content:', error)
    } finally {
      isLoading.value = false
    }
  }

  async function generateSkillFiles(): Promise<SkillGenerateResponse | null> {
    try {
      isGenerating.value = true
      const response = await axios.post<SkillGenerateResponse>('/api/skill/generate')
      // Clear cache after generation
      await axios.post('/api/skill/clear-cache')
      // Refresh content
      await fetchAllContent()
      return response.data
    } catch (error) {
      console.error('Failed to generate skill files:', error)
      return null
    } finally {
      isGenerating.value = false
    }
  }

  function setSkillEnabled(enabled: boolean) {
    skillEnabled.value = enabled
    saveSetting('geopipe-skill-enabled', enabled)
  }

  function setSelectedModules(moduleIds: string[]) {
    selectedModules.value = moduleIds
    saveSetting('geopipe-skill-modules', moduleIds)
  }

  function toggleModule(moduleId: string) {
    const idx = selectedModules.value.indexOf(moduleId)
    if (idx >= 0) {
      selectedModules.value.splice(idx, 1)
    } else {
      selectedModules.value.push(moduleId)
    }
    saveSetting('geopipe-skill-modules', selectedModules.value)
  }

  async function importSkill(req: SkillImportRequest): Promise<SkillImportResponse | null> {
    try {
      isImporting.value = true
      const response = await axios.post<SkillImportResponse>('/api/skill/import', req)
      // Refresh modules list and content
      await fetchModules()
      return response.data
    } catch (error) {
      console.error('Failed to import skill:', error)
      return null
    } finally {
      isImporting.value = false
    }
  }

  async function importSkillFromUrl(req: SkillImportUrlRequest): Promise<SkillImportResponse | null> {
    try {
      isImporting.value = true
      const response = await axios.post<SkillImportResponse>('/api/skill/import-url', req)
      await fetchModules()
      return response.data
    } catch (error) {
      console.error('Failed to import skill from URL:', error)
      return null
    } finally {
      isImporting.value = false
    }
  }

  async function deleteExternalSkill(moduleId: string): Promise<boolean> {
    try {
      await axios.delete(`/api/skill/external/${moduleId}`)
      // Remove from local state
      contents.value.delete(moduleId)
      const idx = selectedModules.value.indexOf(moduleId)
      if (idx >= 0) {
        selectedModules.value.splice(idx, 1)
        saveSetting('geopipe-skill-modules', selectedModules.value)
      }
      await fetchModules()
      return true
    } catch (error) {
      console.error(`Failed to delete external skill ${moduleId}:`, error)
      return false
    }
  }

  return {
    // State
    modules,
    contents,
    isLoading,
    isGenerating,
    isImporting,
    skillEnabled,
    selectedModules,
    // Computed
    totalTokenEstimate,
    skillSettings,
    // Actions
    fetchModules,
    fetchContent,
    fetchAllContent,
    generateSkillFiles,
    setSkillEnabled,
    setSelectedModules,
    toggleModule,
    importSkill,
    importSkillFromUrl,
    deleteExternalSkill,
  }
})

// --- Helpers ---

function loadSetting<T>(key: string, defaultValue: T): T {
  try {
    const raw = localStorage.getItem(key)
    if (raw !== null) {
      return JSON.parse(raw) as T
    }
  } catch {
    // ignore
  }
  return defaultValue
}

function saveSetting<T>(key: string, value: T) {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch {
    // ignore
  }
}
