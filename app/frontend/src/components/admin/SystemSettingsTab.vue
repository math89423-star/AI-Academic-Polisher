<template>
  <div class="tab-content">
    <h2>系统设置</h2>
    <p style="color: #64748b; margin-bottom: 20px;">调整系统运行参数，修改后对新提交的任务生效</p>

    <div class="setting-card">
      <div class="setting-header">
        <label class="form-label" style="margin-bottom: 0; font-size: 15px;">文本分块大小（字符数）</label>
      </div>
      <p class="setting-desc">
        润色时会将长文本按此大小切分为多个片段，逐片段发送给 AI 处理。
        值越大，单次处理的上下文越完整，但可能增加单次请求耗时或触发模型 token 限制；
        值越小，并发效率更高，但上下文连贯性可能下降。建议范围 800~3000，默认 1500。
      </p>
      <div style="display: flex; align-items: center; gap: 12px; margin-top: 12px;">
        <input
          type="number"
          v-model.number="chunkSize"
          min="500"
          max="5000"
          step="100"
          class="chunk-input"
        />
        <span style="color: #94a3b8; font-size: 13px;">范围 500 ~ 5000</span>
      </div>
      <div style="margin-top: 16px;">
        <button @click="saveChunkSize" class="btn-primary" :disabled="savingChunkSize">
          {{ savingChunkSize ? '保存中...' : '保存' }}
        </button>
        <button @click="chunkSize = 1500" class="btn-secondary" style="margin-left: 10px;">恢复默认</button>
      </div>
      <div v-if="chunkSizeMsg" :class="['test-result', chunkSizeMsgOk ? 'success' : 'error']" style="margin-top: 10px;">
        {{ chunkSizeMsg }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const props = defineProps({
  adminUsername: { type: String, required: true }
})

const chunkSize = ref(1500)
const savingChunkSize = ref(false)
const chunkSizeMsg = ref('')
const chunkSizeMsgOk = ref(false)

const loadChunkSize = async () => {
  try {
    const res = await fetch(`/api/admin/chunk_size?admin_username=${props.adminUsername}`)
    if (res.ok) {
      const data = await res.json()
      chunkSize.value = data.chunk_size
    }
  } catch (e) { /* ignore */ }
}

const saveChunkSize = async () => {
  if (chunkSize.value < 500 || chunkSize.value > 5000) {
    chunkSizeMsg.value = '分块大小需在 500~5000 之间'
    chunkSizeMsgOk.value = false
    return
  }
  savingChunkSize.value = true
  chunkSizeMsg.value = ''
  try {
    const res = await fetch('/api/admin/chunk_size', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ admin_username: props.adminUsername, chunk_size: chunkSize.value })
    })
    const data = await res.json()
    if (res.ok) {
      chunkSizeMsg.value = data.message
      chunkSizeMsgOk.value = true
    } else {
      chunkSizeMsg.value = data.error || '保存失败'
      chunkSizeMsgOk.value = false
    }
  } catch (e) {
    chunkSizeMsg.value = '请求失败: ' + e.message
    chunkSizeMsgOk.value = false
  } finally {
    savingChunkSize.value = false
  }
}

onMounted(() => { loadChunkSize() })
</script>

<style scoped>
.setting-card { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 20px 24px; max-width: 600px; }
.setting-header { margin-bottom: 4px; }
.setting-desc { color: #64748b; font-size: 13px; line-height: 1.7; margin: 0; }
.chunk-input { width: 140px; padding: 10px 14px; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 15px; font-weight: 500; text-align: center; }
.chunk-input:focus { outline: none; border-color: #3498db; box-shadow: 0 0 0 3px rgba(52,152,219,0.12); }
</style>
