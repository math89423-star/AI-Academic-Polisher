import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { taskAPI } from '../api'

export const useTaskStore = defineStore('task', () => {
  const tasks = ref({})
  const currentTaskId = ref(null)
  const strategies = ref([])
  const eventSource = ref(null)

  const currentTask = computed(() => {
    return currentTaskId.value ? tasks.value[currentTaskId.value] : null
  })

  const sortedTasks = computed(() => {
    return Object.values(tasks.value).sort((a, b) => b.id - a.id)
  })

  async function loadHistory(username) {
    try {
      const data = await taskAPI.getHistory(username)
      tasks.value = {}
      data.forEach(t => {
        tasks.value[t.id] = {
          id: t.id,
          time: t.created_at,
          original: t.original_text,
          polished: t.polished_text,
          status: t.status,
          serverInfo: '',
          task_type: t.task_type || 'text',
          downloadUrl: t.download_url || '',
          title: t.title
        }
      })
      if (data.length > 0 && !currentTaskId.value) {
        currentTaskId.value = data[0].id
      }
    } catch (err) {
      console.error('加载历史失败:', err)
    }
  }

  async function loadStrategies() {
    try {
      const data = await taskAPI.getStrategies()
      strategies.value = data
    } catch (err) {
      console.error('加载策略失败:', err)
      strategies.value = []
    }
  }

  function switchTask(taskId) {
    currentTaskId.value = taskId
  }

  function createNewTask() {
    currentTaskId.value = null
  }

  async function createTask(username, text, mode, strategy) {
    const data = await taskAPI.createTask(username, text, mode, strategy)
    const newTask = {
      id: data.task_id,
      time: new Date().toLocaleString('zh-CN'),
      original: text,
      polished: '',
      status: 'queued',
      serverInfo: '',
      task_type: 'text',
      downloadUrl: '',
      title: ''
    }
    tasks.value[data.task_id] = newTask
    currentTaskId.value = data.task_id
    return data.task_id
  }

  async function uploadDocx(username, file, mode, strategy) {
    const data = await taskAPI.uploadDocx(username, file, mode, strategy)
    const newTask = {
      id: data.task_id,
      time: new Date().toLocaleString('zh-CN'),
      original: '',
      polished: '',
      status: 'queued',
      serverInfo: '',
      task_type: 'docx',
      downloadUrl: '',
      title: file.name
    }
    tasks.value[data.task_id] = newTask
    currentTaskId.value = data.task_id
    return data.task_id
  }

  function startSSE(taskId) {
    if (eventSource.value) {
      eventSource.value.close()
    }

    eventSource.value = taskAPI.connectSSE(
      taskId,
      (data) => {
        const task = tasks.value[taskId]
        if (!task) return

        if (data.type === 'status') {
          task.status = data.status
          task.serverInfo = data.message || ''
        } else if (data.type === 'chunk') {
          task.polished += data.content
        } else if (data.type === 'done') {
          task.status = 'completed'
          task.downloadUrl = data.download_url || ''
          if (eventSource.value) {
            eventSource.value.close()
            eventSource.value = null
          }
        } else if (data.type === 'error') {
          task.status = 'failed'
          task.serverInfo = data.message || '处理失败'
          if (eventSource.value) {
            eventSource.value.close()
            eventSource.value = null
          }
        }
      },
      (err) => {
        console.error('SSE error:', err)
        const task = tasks.value[taskId]
        if (task && task.status === 'processing') {
          task.serverInfo = '连接中断'
        }
      }
    )
  }

  function stopSSE() {
    if (eventSource.value) {
      eventSource.value.close()
      eventSource.value = null
    }
  }

  async function cancelTask(taskId) {
    await taskAPI.cancelTask(taskId)
    const task = tasks.value[taskId]
    if (task) {
      task.status = 'cancelled'
    }
    stopSSE()
  }

  async function resumeTask(taskId) {
    await taskAPI.resumeTask(taskId)
    const task = tasks.value[taskId]
    if (task) {
      task.status = 'queued'
      task.polished = ''
    }
    startSSE(taskId)
  }

  return {
    tasks,
    currentTaskId,
    currentTask,
    sortedTasks,
    strategies,
    loadHistory,
    loadStrategies,
    switchTask,
    createNewTask,
    createTask,
    uploadDocx,
    startSSE,
    stopSSE,
    cancelTask,
    resumeTask
  }
})
