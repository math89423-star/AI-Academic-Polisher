<template>
  <div class="editor-container">
    <div class="box-header">
      <h3>润色结果</h3>
      <div style="display: flex; align-items: center;">
        <button
          v-if="showDiffButton"
          class="diff-toggle-btn"
          :class="{ active: isDiffMode }"
          @click="toggleDiffMode"
        >
          📊 对比模式
        </button>
        <button
          v-if="showCopyButton"
          class="diff-toggle-btn"
          style="margin-left: 5px;"
          @click="copyResult"
        >
          📋 复制
        </button>
        <span class="status-badge">{{ statusText }}</span>
        <span v-if="isWaiting" class="elapsed-timer">已等待 {{ elapsedText }}</span>
        <span class="server-msg">{{ currentTask?.serverInfo || '' }}</span>
        <a
          v-if="currentTask?.downloadUrl"
          :href="currentTask.downloadUrl"
          class="download-btn"
          target="_blank"
        >
          📥 下载 Word
        </a>
      </div>
    </div>
    <div class="content-area">
      <div
        ref="resultBox"
        class="result-box"
        :class="{ 'diff-mode': isDiffMode }"
        v-html="displayContent"
      ></div>
      <div v-if="resultCharCount > 0" class="char-count">字数: {{ resultCharCount }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onUnmounted } from 'vue'

const props = defineProps({
  currentTask: Object
})

const emit = defineEmits(['cancel', 'resume'])

const isDiffMode = ref(false)
const resultBox = ref(null)
const elapsedSeconds = ref(0)
let timerInterval = null

const isWaiting = computed(() => {
  if (!props.currentTask) return false
  return ['queued', 'processing'].includes(props.currentTask.status)
})

const elapsedText = computed(() => {
  const s = elapsedSeconds.value
  if (s < 60) return `${s}s`
  const m = Math.floor(s / 60)
  const rem = s % 60
  return `${m}m ${rem}s`
})

function calcElapsedFromServer() {
  if (!props.currentTask?.time) return 0
  const created = new Date(props.currentTask.time)
  if (isNaN(created.getTime())) return 0
  return Math.max(0, Math.floor((Date.now() - created.getTime()) / 1000))
}

function startTimer() {
  stopTimer()
  elapsedSeconds.value = calcElapsedFromServer()
  timerInterval = setInterval(() => { elapsedSeconds.value++ }, 1000)
}

function stopTimer() {
  if (timerInterval) {
    clearInterval(timerInterval)
    timerInterval = null
  }
}

watch(isWaiting, (waiting) => {
  if (waiting) startTimer()
  else stopTimer()
}, { immediate: true })

watch(() => props.currentTask?.status, (status) => {
  if (status && !['queued', 'processing'].includes(status)) {
    stopTimer()
  }
})

watch(() => props.currentTask?.id, () => {
  stopTimer()
  elapsedSeconds.value = calcElapsedFromServer()
  if (isWaiting.value) startTimer()
})

onUnmounted(() => stopTimer())

const statusText = computed(() => {
  if (!props.currentTask) return '待命'
  const status = props.currentTask.status
  if (['completed', 'done'].includes(status)) return '✅ 润色完成'
  if (['failed', 'cancelled'].includes(status)) return '❌ 失败/中止'
  return '⏳ 处理中'
})

const showDiffButton = computed(() => {
  return props.currentTask &&
    props.currentTask.task_type === 'text' &&
    props.currentTask.polished &&
    props.currentTask.polished.trim()
})

const showCopyButton = computed(() => {
  return props.currentTask &&
    props.currentTask.polished &&
    props.currentTask.polished.trim()
})

const resultCharCount = computed(() => {
  return props.currentTask?.polished?.length || 0
})

const displayContent = computed(() => {
  if (!props.currentTask) {
    return '润色结果将在这里流式输出...'
  }

  if (isDiffMode.value && props.currentTask.task_type === 'text') {
    return generateDiff(props.currentTask.original, props.currentTask.polished)
  }

  return props.currentTask.polished || '润色结果将在这里流式输出...'
})

watch(() => props.currentTask, () => {
  isDiffMode.value = false
})

const toggleDiffMode = () => {
  isDiffMode.value = !isDiffMode.value
}

const copyResult = async () => {
  if (!props.currentTask?.polished) return

  try {
    if (navigator.clipboard) {
      await navigator.clipboard.writeText(props.currentTask.polished)
    } else {
      const textarea = document.createElement('textarea')
      textarea.value = props.currentTask.polished
      textarea.style.position = 'fixed'
      textarea.style.opacity = '0'
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
    }
    alert('已复制到剪贴板')
  } catch (err) {
    console.error('复制失败:', err)
  }
}

// 简单的 diff 实现
const generateDiff = (original, polished) => {
  if (!original || !polished) return polished

  const origWords = original.split(/(\s+)/)
  const polishedWords = polished.split(/(\s+)/)

  let result = ''
  const maxLen = Math.max(origWords.length, polishedWords.length)

  for (let i = 0; i < maxLen; i++) {
    const origWord = origWords[i] || ''
    const polishedWord = polishedWords[i] || ''

    if (origWord !== polishedWord) {
      if (origWord) {
        result += `<span style="background-color: #fee; text-decoration: line-through;">${origWord}</span>`
      }
      if (polishedWord) {
        result += `<span style="background-color: #dfd;">${polishedWord}</span>`
      }
    } else {
      result += origWord
    }
  }

  return result
}
</script>

<style scoped>
.result-box {
  overflow-y: auto;
  padding: 20px;
  font-size: 14.5px;
  line-height: 1.6;
  color: var(--text-main);
  background-color: #fafafa;
  white-space: pre-wrap;
  word-wrap: break-word;
  height: 100%;
}

.download-btn {
  padding: 4px 10px;
  font-size: 13px;
  margin-left: 10px;
  background-color: #10b981;
  color: white;
  border-radius: 4px;
  text-decoration: none;
  font-weight: 500;
}

.diff-toggle-btn.active {
  background-color: var(--primary-color);
  color: white;
}

.elapsed-timer {
  margin-left: 8px;
  font-size: 12px;
  color: #f59e0b;
  font-weight: 500;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.content-area { position: relative; }
.char-count { position: absolute; bottom: 8px; right: 12px; font-size: 12px; color: #94a3b8; pointer-events: none; }
</style>
