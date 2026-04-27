import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { taskAPI } from '../api'
import { createSSEManager } from './sseManager'

export const useTaskStore = defineStore('task', () => {
  const tasks = ref({})
  const currentTaskId = ref(null)
  const strategies = ref([])
  const pendingCount = ref(0)
  let queuePollTimer = null

  const sse = createSSEManager()

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

  async function loadStrategies(username) {
    try {
      const data = await taskAPI.getStrategies(username)
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
      time: new Date().toISOString(),
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
      time: new Date().toISOString(),
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

  function _handleSSEEvent(taskId, data) {
    const task = tasks.value[taskId]
    if (!task) return

    if (data.type === 'status') {
      const c = data.content || {}
      task.status = c.status || data.status
      task.serverInfo = c.message || data.message || ''
    } else if (data.type === 'chunk' || data.type === 'stream') {
      task.polished += (typeof data.content === 'string' ? data.content : '')
    } else if (data.type === 'block') {
      task.serverInfo = typeof data.content === 'string' ? data.content : ''
    } else if (data.type === 'progress') {
      task.serverInfo = `处理中 ${data.content}%`
    } else if (data.type === 'done') {
      task.status = 'completed'
      const c = data.content || {}
      task.downloadUrl = (typeof c === 'object' ? c.download_url : '') || ''
      task.serverInfo = ''
      sse.stop()
    } else if (data.type === 'error' || data.type === 'fatal') {
      task.status = 'failed'
      task.serverInfo = (typeof data.content === 'string' ? data.content : data.message) || '处理失败'
      sse.stop()
    }
  }

  function startSSE(taskId) {
    sse.start(
      taskId,
      (data) => _handleSSEEvent(taskId, data),
      (err) => {
        const task = tasks.value[taskId]
        if (task && task.status === 'processing') {
          task.serverInfo = '连接中断'
        }
      }
    )
  }

  function stopSSE() {
    sse.stop()
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

  async function deleteTask(taskId, username) {
    await taskAPI.deleteTask(taskId, username)
    delete tasks.value[taskId]
    if (currentTaskId.value === taskId) {
      const remaining = sortedTasks.value
      currentTaskId.value = remaining.length > 0 ? remaining[0].id : null
    }
  }

  async function fetchQueueStatus() {
    try {
      const data = await taskAPI.getQueueStatus()
      pendingCount.value = data.pending_count
    } catch (e) { /* ignore */ }
  }

  function startQueuePolling() {
    fetchQueueStatus()
    queuePollTimer = setInterval(fetchQueueStatus, 10000)
  }

  function stopQueuePolling() {
    if (queuePollTimer) {
      clearInterval(queuePollTimer)
      queuePollTimer = null
    }
  }

  return {
    tasks,
    currentTaskId,
    currentTask,
    sortedTasks,
    strategies,
    pendingCount,
    loadHistory,
    loadStrategies,
    switchTask,
    createNewTask,
    createTask,
    uploadDocx,
    startSSE,
    stopSSE,
    cancelTask,
    resumeTask,
    deleteTask,
    startQueuePolling,
    stopQueuePolling
  }
})
