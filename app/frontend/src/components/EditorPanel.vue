<template>
  <div class="editor-container">
    <div class="box-header">
      <h3>原始输入</h3>
      <div>
        <label style="margin-right: 10px; cursor: pointer; font-size: 13px;">
          <input type="radio" v-model="mode" value="zh"> 🇨🇳 中文润色
        </label>
        <label style="cursor: pointer; font-size: 13px;">
          <input type="radio" v-model="mode" value="en"> 🇬🇧 英文润色
        </label>
      </div>
    </div>

    <div class="content-area">
      <div v-if="isFileTask" id="docx-info-box">
        <div style="font-size: 56px; margin-bottom: 10px;">{{ currentTask?.task_type === 'pdf' ? '📕' : '📄' }}</div>
        <div>{{ currentTask?.title || '文档名称' }}</div>
        <div style="font-size: 13px; color: #10b981; background: #d1fae5; padding: 5px 15px; border-radius: 12px; font-weight: 500;">
          {{ currentTask?.task_type === 'pdf' ? 'PDF 智能解析引擎已激活' : 'Word 专用解析引擎已激活' }}
        </div>
      </div>

      <textarea
        v-else
        v-model="originalText"
        placeholder="请在此粘贴需要润色的长篇文本，或上传 Word/PDF 文档..."
      ></textarea>
      <div class="char-count">字数: {{ originalText.length }}</div>
    </div>

    <div class="bottom-control-bar">
      <div class="strategy-selector">
        <span>🤖 去AI化策略:</span>
        <span>
          <label
            v-for="(strategy, index) in strategies"
            :key="strategy.id"
            style="margin-right: 15px; cursor: pointer;"
            :style="{ color: strategy.color }"
          >
            <input
              type="radio"
              v-model="selectedStrategy"
              :value="strategy.id"
              :checked="index === 0"
            >
            {{ strategy.name }}
          </label>
          <span v-if="strategies.length === 0" style="color: #94a3b8; font-size: 12px;">
            正在加载策略库...
          </span>
        </span>
      </div>

      <div class="button-group">
        <button
          v-if="!currentTask"
          class="primary-btn"
          @click="handlePolish"
          :disabled="isProcessing"
        >
          开始极速润色
        </button>

        <input
          ref="fileInput"
          type="file"
          accept=".doc,.docx,.pdf"
          style="display: none;"
          @change="handleFileChange"
        >
        <button
          v-if="!currentTask"
          class="primary-btn"
          style="background-color: #f59e0b;"
          @click="$refs.fileInput.click()"
        >
          📄 上传文档
        </button>

        <button
          v-if="showCancel"
          class="danger-btn"
          @click="$emit('cancel')"
        >
          ⏹ 终止任务
        </button>

        <button
          v-if="showResume"
          class="primary-btn"
          style="background-color: #10b981;"
          @click="$emit('resume')"
        >
          ▶️ 继续执行
        </button>
      </div>
    </div>

    <ErrorToast v-if="errorToast" :error="errorToast" @close="errorToast = null" />
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useTaskStore } from '../stores/taskStore'
import { taskAPI } from '../api'
import ErrorToast from './ErrorToast.vue'

const props = defineProps({
  username: String,
  currentTask: Object,
  strategies: Array
})

const taskStore = useTaskStore()

const emit = defineEmits(['task-created', 'cancel', 'resume'])

const mode = ref('zh')
const originalText = ref('')
const selectedStrategy = ref('standard')
const isProcessing = ref(false)
const errorToast = ref(null)

const isFileTask = computed(() => {
  return props.currentTask && ['docx', 'pdf'].includes(props.currentTask.task_type)
})

const showCancel = computed(() => {
  return props.currentTask && ['processing', 'queued'].includes(props.currentTask.status)
})

const showResume = computed(() => {
  return props.currentTask && ['cancelled', 'failed'].includes(props.currentTask.status)
})

watch(() => props.currentTask, (task) => {
  if (task && task.task_type === 'text') {
    originalText.value = task.original || ''
  } else if (!task) {
    originalText.value = ''
  }
})

watch(() => props.strategies, (strategies) => {
  if (strategies.length > 0) {
    selectedStrategy.value = strategies[0].id
  }
})

const handlePolish = async () => {
  const text = originalText.value.trim()
  if (!text) return

  try {
    // 检查重复
    const dupData = await taskAPI.checkDuplicate(props.username, text)
    if (dupData?.is_duplicate) {
      const userConfirm = confirm(
        `检测到该文本在近期（24小时内）已优化过。\n` +
        `上次处理时间: ${new Date(dupData.last_processed).toLocaleString()}\n\n` +
        `是否仍要进行新一轮润色？`
      )
      if (!userConfirm) return
    }

    if (text.length > 1500) {
      const confirmLong = confirm(
        `当前文本共 ${text.length} 字符，属于长文本。\n` +
        `长文本将自动切片并发处理，耗时可能较长。\n\n` +
        `是否继续提交？`
      )
      if (!confirmLong) return
    }

    isProcessing.value = true
    const taskId = await taskStore.createTask(
      props.username,
      text,
      mode.value,
      selectedStrategy.value
    )
    emit('task-created', taskId)
  } catch (err) {
    errorToast.value = {
      type: '创建任务失败',
      message: err.message,
      suggestion: '请检查网络连接或稍后重试'
    }
  } finally {
    isProcessing.value = false
  }
}

const handleFileChange = async (event) => {
  const file = event.target.files[0]
  if (!file) return

  try {
    isProcessing.value = true
    const taskId = await taskStore.uploadDocument(
      props.username,
      file,
      mode.value,
      selectedStrategy.value
    )
    emit('task-created', taskId)
  } catch (err) {
    errorToast.value = {
      type: '文档上传失败',
      message: err.message,
      suggestion: '请确保文件格式正确（支持 doc/docx/pdf）且大小不超过限制'
    }
  } finally {
    isProcessing.value = false
    event.target.value = ''
  }
}
</script>

<style scoped>
.char-count { position: absolute; bottom: 8px; right: 12px; font-size: 12px; color: #94a3b8; pointer-events: none; }
.content-area { position: relative; }
</style>
