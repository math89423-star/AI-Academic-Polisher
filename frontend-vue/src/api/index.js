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

  async getStrategies() {
    const res = await fetch(`${API_BASE}/tasks/strategies`)
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

  async uploadDocx(username, file, mode, strategy) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('username', username)
    formData.append('mode', mode)
    formData.append('strategy', strategy)

    const res = await fetch(`${API_BASE}/tasks/upload_docx`, {
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

  async resumeTask(taskId) {
    const res = await fetch(`${API_BASE}/tasks/${taskId}/resume`, {
      method: 'POST'
    })
    if (!res.ok) throw new Error('恢复任务失败')
    return res.json()
  },

  // SSE 流式连接
  connectSSE(taskId, onMessage, onError) {
    const eventSource = new EventSource(`${API_BASE}/tasks/${taskId}/stream`)

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        onMessage(data)
      } catch (err) {
        console.error('SSE parse error:', err)
      }
    }

    eventSource.onerror = (err) => {
      eventSource.close()
      onError(err)
    }

    return eventSource
  }
}
