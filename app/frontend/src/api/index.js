// API 服务层
const API_BASE = '/api'

export const authAPI = {
  async login(username) {
    const res = await fetch(`${API_BASE}/auth/login/user`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username })
    })
    if (!res.ok) {
      const data = await res.json()
      throw new Error(data.error || '验证失败')
    }
    return res.json()
  }
}

export const taskAPI = {
  async getHistory(username) {
    const res = await fetch(`${API_BASE}/tasks/history?username=${username}`)
    if (!res.ok) throw new Error('获取历史失败')
    return res.json()
  },

  async getStrategies(username) {
    const params = username ? `?username=${username}` : ''
    const res = await fetch(`${API_BASE}/tasks/strategies${params}`)
    if (!res.ok) throw new Error('获取策略失败')
    return res.json()
  },

  async checkDuplicate(username, text) {
    const res = await fetch(`${API_BASE}/tasks/check_duplicate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, text })
    })
    if (!res.ok) return null
    return res.json()
  },

  async createTask(username, text, mode, strategy) {
    const res = await fetch(`${API_BASE}/tasks/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, text, mode, strategy })
    })
    if (!res.ok) {
      const data = await res.json()
      throw new Error(data.error || '创建任务失败')
    }
    return res.json()
  },

  async uploadDocument(username, file, mode, strategy) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('username', username)
    formData.append('mode', mode)
    formData.append('strategy', strategy)

    const res = await fetch(`${API_BASE}/tasks/upload_document`, {
      method: 'POST',
      body: formData
    })
    if (!res.ok) {
      const data = await res.json()
      throw new Error(data.error || '上传失败')
    }
    return res.json()
  },

  async cancelTask(taskId) {
    const res = await fetch(`${API_BASE}/tasks/${taskId}/cancel`, {
      method: 'POST'
    })
    if (!res.ok) throw new Error('取消任务失败')
    return res.json()
  },

  async resumeTask(taskId, username) {
    const res = await fetch(`${API_BASE}/tasks/${taskId}/resume`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username })
    })
    if (!res.ok) throw new Error('恢复任务失败')
    return res.json()
  },

  async deleteTask(taskId, username) {
    const res = await fetch(`${API_BASE}/tasks/${taskId}/delete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username })
    })
    if (!res.ok) {
      const data = await res.json()
      throw new Error(data.error || '删除任务失败')
    }
    return res.json()
  },

  async getQueueStatus() {
    const res = await fetch(`${API_BASE}/tasks/queue_status`)
    if (!res.ok) return { pending_count: 0 }
    return res.json()
  },

  async getTaskDetail(taskId) {
    const res = await fetch(`${API_BASE}/tasks/${taskId}/detail`)
    if (!res.ok) throw new Error('获取任务详情失败')
    return res.json()
  },

  // SSE 流式连接
  connectSSE(taskId, onMessage, onError) {
    let retryCount = 0
    const maxRetries = 5
    let eventSource = null
    let closed = false

    function connect() {
      eventSource = new EventSource(`${API_BASE}/tasks/${taskId}/stream`)

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          retryCount = 0
          onMessage(data)
        } catch (err) {
          console.error('SSE parse error:', err)
        }
      }

      eventSource.onerror = async () => {
        eventSource.close()
        if (closed) return

        // 重连前检查任务状态，避免对已完成任务无限重连
        try {
          const res = await fetch(`${API_BASE}/tasks/${taskId}/detail`)
          if (res.ok) {
            const detail = await res.json()
            if (detail.status === 'completed' || detail.status === 'failed' || detail.status === 'cancelled') {
              onMessage({
                type: detail.status === 'completed' ? 'done' : 'fatal',
                content: detail.status === 'completed'
                  ? { download_url: detail.download_url || '' }
                  : '任务已结束'
              })
              return
            }
          }
        } catch (e) { /* 状态检查失败则继续重连逻辑 */ }

        if (retryCount < maxRetries) {
          retryCount++
          const delay = Math.min(1000 * retryCount, 5000)
          setTimeout(connect, delay)
        } else {
          onError(new Error('SSE 重连失败'))
        }
      }
    }

    connect()

    const proxy = {
      close() {
        closed = true
        if (eventSource) eventSource.close()
      }
    }
    return proxy
  }
}
