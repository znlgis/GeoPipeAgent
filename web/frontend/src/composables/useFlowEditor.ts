import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePipelineStore } from '@/stores/pipelineStore'
import { createSSEConnection } from '@/utils/sseClient'
import axios from 'axios'

export function useFlowEditor() {
  const store = usePipelineStore()
  const { t } = useI18n()
  const isExecuting = ref(false)
  const showAiDialog = ref(false)
  const aiPrompt = ref('')

  async function executePipeline() {
    const yaml = store.exportToYaml()
    if (!yaml) return

    isExecuting.value = true
    store.executionStatus = 'running'
    store.executionLog = []

    store.nodes.forEach((n) => {
      if (n.data) n.data.status = 'idle'
    })

    createSSEConnection(
      '/api/pipeline/execute',
      { yaml_content: yaml },
      {
        onMessage(event, data) {
          if (event === 'progress') {
            store.executionLog.push(`[${data.step_id}] ${data.message}`)
            store.updateNodeData(data.step_id, { status: data.status })
          } else if (event === 'done') {
            store.executionStatus = 'done'
            store.executionLog.push(t('pipeline.executionDone'))
            isExecuting.value = false
          } else if (event === 'error') {
            store.executionStatus = 'error'
            store.executionLog.push(t('pipeline.executionError', { msg: data.message }))
            if (data.step_id) {
              store.updateNodeData(data.step_id, {
                status: 'error',
                errorMessage: data.message,
              })
            }
            isExecuting.value = false
          }
        },
        onError(err) {
          store.executionStatus = 'error'
          store.executionLog.push(
            t('pipeline.connectionError', { msg: err.message || t('pipeline.unknownError') }),
          )
          isExecuting.value = false
        },
      },
    )
  }

  async function validatePipeline(): Promise<{
    valid: boolean
    errors: string[]
  }> {
    const yaml = store.exportToYaml()
    if (!yaml) return { valid: false, errors: [t('pipeline.empty')] }
    try {
      const res = await axios.post('/api/pipeline/validate', {
        yaml_content: yaml,
      })
      return res.data
    } catch (err: any) {
      return {
        valid: false,
        errors: [err.response?.data?.detail || t('pipeline.validationFailed')],
      }
    }
  }

  async function savePipeline(name: string) {
    const yaml = store.exportToYaml()
    if (!yaml) return
    const res = await axios.post('/api/pipeline/save', {
      name,
      yaml_content: yaml,
    })
    return res.data
  }

  function loadFromYaml(yaml: string) {
    store.loadFromYaml(yaml)
  }

  function importYamlFile(file: File): Promise<void> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = (e) => {
        const content = e.target?.result as string
        store.loadFromYaml(content)
        resolve()
      }
      reader.onerror = reject
      reader.readAsText(file)
    })
  }

  function exportYamlFile() {
    const yaml = store.exportToYaml()
    if (!yaml) return
    const blob = new Blob([yaml], { type: 'text/yaml;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${store.meta.name || 'pipeline'}.yaml`
    a.click()
    URL.revokeObjectURL(url)
  }

  return {
    isExecuting,
    showAiDialog,
    aiPrompt,
    executePipeline,
    validatePipeline,
    savePipeline,
    loadFromYaml,
    importYamlFile,
    exportYamlFile,
  }
}
