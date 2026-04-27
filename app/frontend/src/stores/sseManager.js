import { taskAPI } from '../api'

/**
 * SSE 连接管理器
 * 从 taskStore 中抽离，独立管理 SSE 生命周期
 */
export function createSSEManager() {
  let eventSource = null

  function start(taskId, onEvent, onError) {
    stop()

    eventSource = taskAPI.connectSSE(
      taskId,
      (data) => onEvent(data),
      (err) => {
        console.error('SSE error:', err)
        if (onError) onError(err)
      }
    )
  }

  function stop() {
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
  }

  function isActive() {
    return eventSource !== null
  }

  return { start, stop, isActive }
}
