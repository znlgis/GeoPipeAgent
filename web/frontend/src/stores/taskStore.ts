import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'
import type { TaskStatus, TaskSubmitResponse } from '@/types/task'
import { createSSEConnection } from '@/utils/sseClient'

export const useTaskStore = defineStore('task', () => {
  const tasks = ref<TaskStatus[]>([])
  const loading = ref(false)

  async function fetchTasks() {
    loading.value = true
    try {
      const response = await axios.get<TaskStatus[]>('/api/task/list')
      tasks.value = response.data
    } catch (error) {
      console.error('Failed to fetch tasks:', error)
    } finally {
      loading.value = false
    }
  }

  async function submitTask(yamlContent: string): Promise<TaskSubmitResponse | null> {
    try {
      const response = await axios.post<TaskSubmitResponse>('/api/task/submit', {
        yaml_content: yamlContent,
      })
      // Refresh list after submit
      await fetchTasks()
      return response.data
    } catch (error) {
      console.error('Failed to submit task:', error)
      return null
    }
  }

  async function deleteTask(taskId: string): Promise<boolean> {
    try {
      await axios.delete(`/api/task/${taskId}`)
      tasks.value = tasks.value.filter((t) => t.id !== taskId)
      return true
    } catch (error) {
      console.error('Failed to delete task:', error)
      return false
    }
  }

  async function getTask(taskId: string): Promise<TaskStatus | null> {
    try {
      const response = await axios.get<TaskStatus>(`/api/task/${taskId}`)
      return response.data
    } catch (error) {
      console.error('Failed to get task:', error)
      return null
    }
  }

  function streamTask(
    taskId: string,
    onProgress: (data: { status: string; progress: number; message: string }) => void,
    onDone: (data: { result?: any }) => void,
    onError: (data: { error: string }) => void,
  ) {
    return createSSEConnection(
      `/api/task/${taskId}/stream`,
      null,
      {
        onMessage(event, data) {
          if (event === 'progress') {
            onProgress(data)
          } else if (event === 'done') {
            onDone(data)
            fetchTasks()
          } else if (event === 'error') {
            onError(data)
            fetchTasks()
          }
        },
        onError(err) {
          onError({ error: err.message || 'Connection error' })
        },
      },
      'GET',
    )
  }

  return {
    tasks,
    loading,
    fetchTasks,
    submitTask,
    deleteTask,
    getTask,
    streamTask,
  }
})
