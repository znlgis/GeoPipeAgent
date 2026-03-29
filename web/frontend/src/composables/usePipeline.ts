import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePipelineStore } from '@/stores/pipelineStore'
import { ElMessageBox } from 'element-plus'
import axios from 'axios'
import type { PipelineInfo } from '@/types/pipeline'

export function usePipeline() {
  const store = usePipelineStore()
  const { t } = useI18n()
  const savedPipelines = ref<PipelineInfo[]>([])
  const loading = ref(false)

  async function loadSavedPipelines() {
    loading.value = true
    try {
      const res = await axios.get<PipelineInfo[]>('/api/pipeline/list')
      savedPipelines.value = res.data
    } catch (err) {
      console.error('Failed to load pipelines:', err)
    } finally {
      loading.value = false
    }
  }

  async function loadPipeline(id: string) {
    loading.value = true
    try {
      const res = await axios.get<{ yaml_content: string }>(
        `/api/pipeline/${id}`,
      )
      store.loadFromYaml(res.data.yaml_content)
    } catch (err) {
      console.error('Failed to load pipeline:', err)
    } finally {
      loading.value = false
    }
  }

  async function deletePipeline(id: string) {
    try {
      await ElMessageBox.confirm(t('pipeline.confirmDeletePipeline'), t('chat.confirmDeleteTitle'), {
        confirmButtonText: t('common.delete'),
        cancelButtonText: t('common.cancel'),
        type: 'warning',
      })
      await axios.delete(`/api/pipeline/${id}`)
      savedPipelines.value = savedPipelines.value.filter((p) => p.id !== id)
    } catch (err) {
      // User cancelled or request failed — nothing to do on cancel
      if (err !== 'cancel') {
        console.error('Failed to delete pipeline:', err)
      }
    }
  }

  return {
    savedPipelines,
    loading,
    loadSavedPipelines,
    loadPipeline,
    deletePipeline,
  }
}
