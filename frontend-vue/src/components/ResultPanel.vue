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
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  currentTask: Object
})

const emit = defineEmits(['cancel', 'resume'])

const isDiffMode = ref(false)
const resultBox = ref(null)

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
    await navigator.clipboard.writeText(props.currentTask.polished)
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
</style>
