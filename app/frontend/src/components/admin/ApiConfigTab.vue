<template>
  <div class="tab-content">
    <h2>API 配置列表</h2>
    <div class="toolbar">
      <button @click="showAddApi = true" class="btn-primary">添加 API 配置</button>
      <button @click="testAllConfigs" class="btn-test-all" :disabled="testingAll">
        {{ testingAll ? '测试中...' : '一键测试全部' }}
      </button>
    </div>
    <div v-if="testAllResult" :class="['test-all-banner', testAllResult.allSuccess ? 'success' : 'warning']">
      {{ testAllResult.message }}
      <button class="banner-close" @click="testAllResult = null">&times;</button>
    </div>
    <table class="data-table">
      <thead>
        <tr><th>名称</th><th>API类型</th><th>Base URL</th><th>模型</th><th>连接状态</th><th>操作</th></tr>
      </thead>
      <tbody>
        <tr v-for="config in apiConfigs" :key="config.id">
          <td>{{ config.name }}</td>
          <td>
            <span class="api-type-badge" :class="'type-' + config.api_type">
              {{ getApiTypeLabel(config.api_type) }}
            </span>
          </td>
          <td>{{ config.base_url }}</td>
          <td>{{ config.model_name }}</td>
          <td>
            <span v-if="testAllResults[config.id]" class="conn-status" :class="testAllResults[config.id].success ? 'conn-ok' : 'conn-fail'">
              {{ testAllResults[config.id].success ? '连接正常' : '连接失败' }}
              <span v-if="!testAllResults[config.id].success" class="conn-tip" :title="testAllResults[config.id].message">?</span>
            </span>
            <span v-else-if="testingAll" class="conn-status conn-pending">测试中...</span>
            <span v-else class="conn-status conn-none">未测试</span>
          </td>
          <td class="action-btns">
            <button @click="openEditApi(config)" class="btn-edit">编辑</button>
            <button @click="testExistingConfig(config)" class="btn-test-sm" :disabled="testingExistingId === config.id">
              {{ testingExistingId === config.id ? '测试中...' : '测试' }}
            </button>
            <button @click="deleteApiConfig(config.id)" class="btn-danger">删除</button>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-if="showAddApi" class="modal">
      <div class="modal-content">
        <h3>添加 API 配置</h3>
        <label class="form-label">配置名称 <span class="required">*</span></label>
        <input v-model="newApi.name" placeholder="例如：GPT-4o 官方、Claude Opus 代理" />
        <label class="form-label">API 类型 <span class="required">*</span></label>
        <select v-model="newApi.api_type" class="form-select">
          <option value="official">官方 API (OpenAI/Anthropic等)</option>
          <option value="proxy">三方代理商 API</option>
          <option value="ollama">Ollama 本地模型</option>
        </select>
        <label class="form-label">API Key <span v-if="newApi.api_type !== 'ollama'" class="required">*</span></label>
        <input v-model="newApi.api_key" placeholder="例如：sk-xxxxxxxxxxxxxxxx（Ollama可留空）" />
        <label class="form-label">Base URL <span class="required">*</span></label>
        <input v-model="newApi.base_url" placeholder="例如：https://api.openai.com/v1" />
        <div class="field-hint">完整的 API 地址，必须以 http:// 或 https:// 开头</div>
        <label class="form-label">模型名称 <span class="required">*</span></label>
        <input v-model="newApi.model_name" placeholder="例如：gpt-4o、claude-opus-4-20250514" />
        <button @click="testConnection" class="btn-test" :disabled="testingConnection">
          {{ testingConnection ? '测试中...' : '测试连接' }}
        </button>
        <div v-if="testResult" :class="['test-result', testResult.success ? 'success' : 'error']">
          {{ testResult.message }}
        </div>
        <div class="modal-actions">
          <button @click="addApiConfig" class="btn-primary">确认</button>
          <button @click="closeAddApiModal" class="btn-secondary">取消</button>
        </div>
      </div>
    </div>

    <div v-if="editingApi" class="modal">
      <div class="modal-content">
        <h3>编辑 API 配置</h3>
        <label class="form-label">配置名称</label>
        <input v-model="editingApi.name" />
        <label class="form-label">API 类型</label>
        <select v-model="editingApi.api_type" class="form-select">
          <option value="official">官方 API</option>
          <option value="proxy">三方代理商 API</option>
          <option value="ollama">Ollama 本地模型</option>
        </select>
        <label class="form-label">API Key</label>
        <input v-model="editingApi.api_key" />
        <label class="form-label">Base URL</label>
        <input v-model="editingApi.base_url" />
        <label class="form-label">模型名称</label>
        <input v-model="editingApi.model_name" />
        <div v-if="editTestResult" :class="['test-result', editTestResult.success ? 'success' : 'error']">
          {{ editTestResult.message }}
        </div>
        <div class="modal-actions">
          <button @click="saveEditApi" class="btn-primary">保存</button>
          <button @click="editingApi = null; editTestResult = null" class="btn-secondary">取消</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const props = defineProps({
  adminUsername: { type: String, required: true }
})

const emit = defineEmits(['configs-updated'])

const apiConfigs = ref([])
const showAddApi = ref(false)
const newApi = ref({ name: '', api_key: '', base_url: '', model_name: 'gpt-3.5-turbo', api_type: 'proxy' })
const testingConnection = ref(false)
const testResult = ref(null)
const editingApi = ref(null)
const editTestResult = ref(null)
const testingExistingId = ref(null)
const testingAll = ref(false)
const testAllResult = ref(null)
const testAllResults = ref({})
const getApiTypeLabel = (type) => {
  const labels = { 'official': '官方API', 'proxy': '代理商', 'ollama': 'Ollama' }
  return labels[type] || type
}

const loadApiConfigs = async () => {
  const res = await fetch(`/api/admin/api_configs?admin_username=${props.adminUsername}`)
  if (res.ok) {
    apiConfigs.value = await res.json()
    emit('configs-updated', apiConfigs.value)
  }
}

const testConnection = async () => {
  if (!newApi.value.base_url || !newApi.value.model_name) {
    alert('请填写 Base URL 和模型名称')
    return
  }
  testingConnection.value = true
  testResult.value = null
  try {
    const res = await fetch('/api/admin/api_configs/test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ admin_username: props.adminUsername, ...newApi.value })
    })
    testResult.value = await res.json()
  } catch (error) {
    testResult.value = { success: false, message: '测试请求失败: ' + error.message }
  } finally {
    testingConnection.value = false
  }
}

const closeAddApiModal = () => {
  showAddApi.value = false
  testResult.value = null
}

const addApiConfig = async () => {
  const res = await fetch('/api/admin/api_configs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ admin_username: props.adminUsername, ...newApi.value })
  })
  if (res.ok) {
    alert('添加成功')
    closeAddApiModal()
    newApi.value = { name: '', api_key: '', base_url: '', model_name: 'gpt-3.5-turbo', api_type: 'proxy' }
    loadApiConfigs()
  }
}

const openEditApi = (config) => {
  editingApi.value = { ...config }
  editTestResult.value = null
}
const saveEditApi = async () => {
  const res = await fetch(`/api/admin/api_configs/${editingApi.value.id}?admin_username=${props.adminUsername}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ admin_username: props.adminUsername, ...editingApi.value })
  })
  if (res.ok) {
    alert('更新成功')
    editingApi.value = null
    editTestResult.value = null
    loadApiConfigs()
  } else {
    const data = await res.json()
    alert(data.error || '更新失败')
  }
}

const testExistingConfig = async (config) => {
  testingExistingId.value = config.id
  try {
    const res = await fetch('/api/admin/api_configs/test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ admin_username: props.adminUsername, ...config })
    })
    const result = await res.json()
    alert(result.message)
  } catch (e) {
    alert('测试请求失败: ' + e.message)
  } finally {
    testingExistingId.value = null
  }
}

const testAllConfigs = async () => {
  testingAll.value = true
  testAllResult.value = null
  testAllResults.value = {}
  try {
    const res = await fetch('/api/admin/api_configs/test_all', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ admin_username: props.adminUsername })
    })
    const data = await res.json()
    if (data.results) {
      for (const r of data.results) {
        testAllResults.value[r.id] = { success: r.success, message: r.message }
      }
    }
    const allSuccess = data.results?.every(r => r.success) ?? false
    testAllResult.value = { message: data.message, allSuccess }
  } catch (e) {
    testAllResult.value = { message: '测试请求失败: ' + e.message, allSuccess: false }
  } finally {
    testingAll.value = false
  }
}

const deleteApiConfig = async (id) => {
  if (!confirm('确认删除?')) return
  const res = await fetch(`/api/admin/api_configs/${id}?admin_username=${props.adminUsername}`, { method: 'DELETE' })
  if (res.ok) { alert('删除成功'); loadApiConfigs() }
}

onMounted(() => { loadApiConfigs() })
</script>

<style scoped>
.toolbar { display: flex; gap: 10px; align-items: center; }
.api-type-badge { display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 500; }
.api-type-badge.type-official { background: #e3f2fd; color: #1976d2; }
.api-type-badge.type-proxy { background: #f3e5f5; color: #7b1fa2; }
.api-type-badge.type-ollama { background: #e8f5e9; color: #388e3c; }
.btn-test { width: 100%; background: linear-gradient(135deg, #ff9800, #f57c00); color: white; border: none; padding: 10px; border-radius: 6px; cursor: pointer; margin-bottom: 10px; transition: all 0.2s; }
.btn-test:hover { transform: translateY(-1px); }
.btn-test:disabled { background: #ccc; cursor: not-allowed; transform: none; }
.btn-edit { background: #3498db; color: white; border: none; padding: 6px 14px; border-radius: 6px; cursor: pointer; transition: all 0.2s; }
.btn-edit:hover { background: #2980b9; }
.btn-test-sm { background: #ff9800; color: white; border: none; padding: 6px 14px; border-radius: 6px; cursor: pointer; transition: all 0.2s; }
.btn-test-sm:disabled { background: #ccc; cursor: not-allowed; }
.btn-test-all { background: linear-gradient(135deg, #ff9800, #f57c00); color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; margin-bottom: 16px; transition: all 0.2s; font-weight: 500; }
.btn-test-all:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(255,152,0,0.3); }
.btn-test-all:disabled { background: #ccc; cursor: not-allowed; transform: none; box-shadow: none; }
.test-all-banner { padding: 12px 16px; border-radius: 8px; margin-bottom: 16px; font-size: 14px; display: flex; align-items: center; justify-content: space-between; }
.test-all-banner.success { background: #e8f5e9; color: #2e7d32; border: 1px solid #4caf50; }
.test-all-banner.warning { background: #fff3e0; color: #e65100; border: 1px solid #ff9800; }
.banner-close { background: none; border: none; font-size: 18px; cursor: pointer; color: inherit; padding: 0 4px; }
.conn-status { font-size: 12px; font-weight: 500; padding: 3px 10px; border-radius: 10px; white-space: nowrap; }
.conn-ok { background: #e8f5e9; color: #2e7d32; }
.conn-fail { background: #ffebee; color: #c62828; }
.conn-pending { background: #fff3e0; color: #e65100; }
.conn-none { background: #f1f5f9; color: #94a3b8; }
.conn-tip { display: inline-block; margin-left: 4px; width: 16px; height: 16px; line-height: 16px; text-align: center; border-radius: 50%; background: #c62828; color: white; font-size: 11px; cursor: help; }
.action-btns { display: flex; gap: 6px; }
</style>
