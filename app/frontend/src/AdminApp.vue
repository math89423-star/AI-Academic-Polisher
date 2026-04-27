<template>
  <div id="admin-app">
    <!-- 登录界面 -->
    <div v-if="!isLoggedIn" class="login-container">
      <h2>管理后台登录</h2>
      <input v-model="loginUsername" placeholder="管理员用户名" @keyup.enter="handleLogin" />
      <input v-model="loginPassword" type="password" placeholder="密码" @keyup.enter="handleLogin" />
      <button @click="handleLogin" class="btn-primary">登录</button>
      <div v-if="loginError" class="error-msg">{{ loginError }}</div>
    </div>

    <!-- 管理后台主界面 -->
    <div v-else>
      <div class="admin-header">
        <h1>系统管理后台</h1>
        <div class="header-right">
          <span class="username">{{ currentUsername }}</span>
          <button @click="logout" class="logout-btn">退出登录</button>
        </div>
      </div>

      <div class="admin-container">
      <div class="tabs">
        <button :class="{ active: activeTab === 'users' }" @click="activeTab = 'users'">用户管理</button>
        <button :class="{ active: activeTab === 'api' }" @click="activeTab = 'api'">API 配置</button>
      </div>

      <div v-if="activeTab === 'users'" class="tab-content">
        <h2>用户列表</h2>
        <div class="toolbar">
          <button @click="showAddUser = true" class="btn-primary">添加用户</button>
          <button
            v-if="selectedUsers.length > 0"
            @click="showBatchAssign = true"
            class="btn-primary"
            style="background: #8e44ad;"
          >
            批量分配 LLM ({{ selectedUsers.length }}人)
          </button>
        </div>
        <table class="data-table">
          <thead>
            <tr>
              <th><input type="checkbox" @change="toggleSelectAll" :checked="isAllSelected" /></th>
              <th>用户名</th>
              <th>角色</th>
              <th>使用次数</th>
              <th>平衡模式 LLM</th>
              <th>极致模式 LLM</th>
              <th>极致模式权限</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in users" :key="user.id">
              <td><input type="checkbox" :value="user.username" v-model="selectedUsers" /></td>
              <td>{{ user.username }}</td>
              <td>{{ user.role }}</td>
              <td>{{ user.usage_count }}</td>
              <td>
                <select
                  class="inline-select"
                  :value="user.api_config_id_standard"
                  @change="updateUserConfig(user.username, 'standard', $event.target.value)"
                >
                  <option :value="null">系统默认</option>
                  <option v-for="c in apiConfigs" :key="c.id" :value="c.id">{{ c.name }}</option>
                </select>
              </td>
              <td>
                <select
                  class="inline-select"
                  :value="user.api_config_id_strict"
                  @change="updateUserConfig(user.username, 'strict', $event.target.value)"
                >
                  <option :value="null">系统默认</option>
                  <option v-for="c in apiConfigs" :key="c.id" :value="c.id">{{ c.name }}</option>
                </select>
              </td>
              <td>
                <label class="switch">
                  <input
                    type="checkbox"
                    :checked="user.can_use_strict"
                    @change="toggleStrictPermission(user.username, $event.target.checked)"
                  />
                  <span class="slider"></span>
                </label>
              </td>
              <td><button @click="deleteUser(user.username)" class="btn-danger">删除</button></td>
            </tr>
          </tbody>
        </table>

        <!-- 批量分配模态框 -->
        <div v-if="showBatchAssign" class="modal">
          <div class="modal-content">
            <h3>批量分配 LLM 配置</h3>
            <p style="color: #64748b; font-size: 13px;">将为 {{ selectedUsers.length }} 个用户统一设置</p>

            <label class="form-label">模式</label>
            <select v-model="batchMode" class="form-select">
              <option value="standard">平衡模式</option>
              <option value="strict">极致模式</option>
            </select>

            <label class="form-label">LLM 配置</label>
            <select v-model="batchConfigId" class="form-select">
              <option :value="null">系统默认</option>
              <option v-for="c in apiConfigs" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>

            <div class="modal-actions">
              <button @click="batchAssign" class="btn-primary">确认分配</button>
              <button @click="showBatchAssign = false" class="btn-secondary">取消</button>
            </div>
          </div>
        </div>

        <div v-if="showAddUser" class="modal">
          <div class="modal-content">
            <h3>添加新用户</h3>
            <input v-model="newUser.username" placeholder="用户名" />
            <input v-model="newUser.password" type="password" placeholder="密码" />
            <select v-model="newUser.role">
              <option value="user">普通用户</option>
              <option value="admin">管理员</option>
            </select>
            <div class="modal-actions">
              <button @click="addUser" class="btn-primary">确认</button>
              <button @click="showAddUser = false" class="btn-secondary">取消</button>
            </div>
          </div>
        </div>
      </div>

      <div v-if="activeTab === 'api'" class="tab-content">
        <h2>API 配置列表</h2>
        <button @click="showAddApi = true" class="btn-primary">添加 API 配置</button>
        <table class="data-table">
          <thead>
            <tr><th>名称</th><th>API类型</th><th>Base URL</th><th>模型</th><th>操作</th></tr>
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
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const activeTab = ref('users')
const users = ref([])
const apiConfigs = ref([])
const showAddUser = ref(false)
const showAddApi = ref(false)
const testingConnection = ref(false)
const testResult = ref(null)
const newUser = ref({ username: '', password: '', role: 'user' })
const newApi = ref({ name: '', api_key: '', base_url: '', model_name: 'gpt-3.5-turbo', api_type: 'proxy' })
const selectedUsers = ref([])
const showBatchAssign = ref(false)
const batchMode = ref('standard')
const batchConfigId = ref(null)
const editingApi = ref(null)
const editTestResult = ref(null)
const testingExistingId = ref(null)

const isAllSelected = computed(() => {
  return users.value.length > 0 && selectedUsers.value.length === users.value.length
})

const toggleSelectAll = (e) => {
  selectedUsers.value = e.target.checked ? users.value.map(u => u.username) : []
}

const getAdminUsername = () => sessionStorage.getItem('admin_username')

// 登录相关 - 管理后台使用独立的 session key
const isLoggedIn = ref(false)
const currentUsername = ref('')
const loginUsername = ref('')
const loginPassword = ref('')
const loginError = ref('')

const checkLoginStatus = () => {
  const savedUsername = getAdminUsername()
  if (savedUsername) {
    isLoggedIn.value = true
    currentUsername.value = savedUsername
    loadUsers()
    loadApiConfigs()
  }
}

const handleLogin = async () => {
  const username = loginUsername.value.trim()
  const password = loginPassword.value.trim()

  if (!username || !password) {
    loginError.value = '请输入用户名和密码'
    return
  }

  try {
    const res = await fetch('/api/auth/login/admin', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    })

    if (res.ok) {
      sessionStorage.setItem('admin_username', username)
      isLoggedIn.value = true
      currentUsername.value = username
      loginError.value = ''
      loadUsers()
      loadApiConfigs()
    } else {
      const data = await res.json()
      loginError.value = data.error || '用户名或密码错误'
    }
  } catch (error) {
    loginError.value = '服务尚未就绪或网络错误，请稍后重试'
  }
}

const loadUsers = async () => {
  const username = getAdminUsername()
  const res = await fetch(`/api/admin/users?admin_username=${username}`)
  if (res.ok) users.value = await res.json()
}

const loadApiConfigs = async () => {
  const username = getAdminUsername()
  const res = await fetch(`/api/admin/api_configs?admin_username=${username}`)
  if (res.ok) apiConfigs.value = await res.json()
}

const getApiTypeLabel = (type) => {
  const labels = {
    'official': '官方API',
    'proxy': '代理商',
    'ollama': 'Ollama'
  }
  return labels[type] || type
}

const testConnection = async () => {
  if (!newApi.value.base_url || !newApi.value.model_name) {
    alert('请填写 Base URL 和模型名称')
    return
  }

  testingConnection.value = true
  testResult.value = null

  try {
    const username = getAdminUsername()
    const res = await fetch('/api/admin/api_configs/test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        admin_username: username,
        ...newApi.value
      })
    })

    const result = await res.json()
    testResult.value = result
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

const addUser = async () => {
  const username = getAdminUsername()
  const res = await fetch('/api/admin/users', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      admin_username: username,
      new_username: newUser.value.username,
      ...newUser.value
    })
  })
  if (res.ok) {
    alert('添加成功')
    showAddUser.value = false
    newUser.value = { username: '', password: '', role: 'user' }
    loadUsers()
  }
}

const updateUserConfig = async (targetUsername, mode, configId) => {
  const adminUsername = getAdminUsername()
  const res = await fetch('/api/admin/users/update_config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      admin_username: adminUsername,
      target_username: targetUsername,
      mode,
      api_config_id: configId === 'null' ? null : Number(configId)
    })
  })
  if (res.ok) loadUsers()
}

const toggleStrictPermission = async (targetUsername, canUseStrict) => {
  const adminUsername = getAdminUsername()
  await fetch('/api/admin/users/update_strict_permission', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      admin_username: adminUsername,
      target_username: targetUsername,
      can_use_strict: canUseStrict
    })
  })
}

const batchAssign = async () => {
  const adminUsername = getAdminUsername()
  const res = await fetch('/api/admin/users/batch_update_config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      admin_username: adminUsername,
      usernames: selectedUsers.value,
      mode: batchMode.value,
      api_config_id: batchConfigId.value
    })
  })
  if (res.ok) {
    alert('批量分配成功')
    showBatchAssign.value = false
    selectedUsers.value = []
    loadUsers()
  }
}

const openEditApi = (config) => {
  editingApi.value = { ...config }
  editTestResult.value = null
}

const saveEditApi = async () => {
  const username = getAdminUsername()
  const res = await fetch(`/api/admin/api_configs/${editingApi.value.id}?admin_username=${username}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ admin_username: username, ...editingApi.value })
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
    const username = getAdminUsername()
    const res = await fetch('/api/admin/api_configs/test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ admin_username: username, ...config })
    })
    const result = await res.json()
    alert(result.message)
  } catch (e) {
    alert('测试请求失败: ' + e.message)
  } finally {
    testingExistingId.value = null
  }
}

const deleteUser = async (username) => {
  if (!confirm(`确认删除 ${username}?`)) return
  const adminUsername = getAdminUsername()
  const res = await fetch(`/api/admin/users/${username}?admin_username=${adminUsername}`, { method: 'DELETE' })
  if (res.ok) { alert('删除成功'); loadUsers() }
}

const addApiConfig = async () => {
  const username = getAdminUsername()
  const res = await fetch('/api/admin/api_configs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      admin_username: username,
      ...newApi.value
    })
  })
  if (res.ok) {
    alert('添加成功')
    closeAddApiModal()
    newApi.value = { name: '', api_key: '', base_url: '', model_name: 'gpt-3.5-turbo', api_type: 'proxy' }
    loadApiConfigs()
  }
}

const deleteApiConfig = async (id) => {
  if (!confirm('确认删除?')) return
  const username = getAdminUsername()
  const res = await fetch(`/api/admin/api_configs/${id}?admin_username=${username}`, { method: 'DELETE' })
  if (res.ok) { alert('删除成功'); loadApiConfigs() }
}

const logout = () => {
  sessionStorage.removeItem('admin_username')
  isLoggedIn.value = false
  currentUsername.value = ''
  window.location.href = '/admin'
}

onMounted(() => { checkLoginStatus() })
</script>

<style scoped>
#admin-app { min-height: 100vh; background: #f5f5f5; }
.admin-header { background: #2c3e50; color: white; padding: 20px; display: flex; justify-content: space-between; align-items: center; }
.logout-btn { background: #e74c3c; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; }
.admin-container { max-width: 1200px; margin: 20px auto; background: white; padding: 20px; border-radius: 8px; }
.tabs { display: flex; gap: 10px; margin-bottom: 20px; border-bottom: 2px solid #ddd; }
.tabs button { padding: 10px 20px; border: none; background: none; cursor: pointer; font-size: 16px; }
.tabs button.active { border-bottom: 3px solid #3498db; color: #3498db; }
.tab-content h2 { margin-bottom: 20px; }
.data-table { width: 100%; border-collapse: collapse; margin-top: 20px; }
.data-table th, .data-table td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
.data-table th { background: #f8f9fa; font-weight: bold; }
.btn-primary { background: #3498db; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; margin-bottom: 20px; }
.btn-danger { background: #e74c3c; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; }
.btn-secondary { background: #95a5a6; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; }
.modal { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.5); display: flex; justify-content: center; align-items: center; }
.modal-content { background: white; padding: 30px; border-radius: 8px; min-width: 400px; }
.modal-content h3 { margin-bottom: 20px; }
.modal-content input, .modal-content select { width: 100%; padding: 10px; margin-bottom: 15px; border: 1px solid #ddd; border-radius: 4px; }
.modal-actions { display: flex; gap: 10px; justify-content: flex-end; }
.form-label { display: block; margin-bottom: 5px; font-weight: 500; color: #333; }
.form-select { width: 100%; padding: 10px; margin-bottom: 15px; border: 1px solid #ddd; border-radius: 4px; background: white; }
.api-type-badge { display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 500; }
.api-type-badge.type-official { background: #e3f2fd; color: #1976d2; }
.api-type-badge.type-proxy { background: #f3e5f5; color: #7b1fa2; }
.api-type-badge.type-ollama { background: #e8f5e9; color: #388e3c; }
.btn-test { width: 100%; background: #ff9800; color: white; border: none; padding: 10px; border-radius: 4px; cursor: pointer; margin-bottom: 10px; }
.btn-test:disabled { background: #ccc; cursor: not-allowed; }
.btn-edit { background: #3498db; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; }
.btn-test-sm { background: #ff9800; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; }
.btn-test-sm:disabled { background: #ccc; cursor: not-allowed; }
.action-btns { display: flex; gap: 6px; }
.test-result { padding: 10px; border-radius: 4px; margin-bottom: 15px; font-size: 14px; }
.test-result.success { background: #e8f5e9; color: #2e7d32; border: 1px solid #4caf50; }
.test-result.error { background: #ffebee; color: #c62828; border: 1px solid #f44336; }
.login-container { max-width: 400px; margin: 100px auto; padding: 40px; background: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
.login-container h2 { margin-bottom: 30px; text-align: center; }
.login-container input { width: 100%; padding: 12px; margin-bottom: 20px; border: 1px solid #ddd; border-radius: 4px; }
.error-msg { color: #e74c3c; margin-top: 10px; font-size: 14px; }
.header-right { display: flex; align-items: center; gap: 15px; }
.username { color: #ecf0f1; font-size: 14px; }
.required { color: #e74c3c; margin-left: 2px; }
.field-hint { font-size: 12px; color: #94a3b8; margin: -10px 0 15px 0; }
.toolbar { display: flex; gap: 10px; align-items: center; }
.inline-select { padding: 4px 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 13px; background: white; min-width: 120px; }
.switch { position: relative; display: inline-block; width: 40px; height: 22px; }
.switch input { opacity: 0; width: 0; height: 0; }
.slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background: #ccc; border-radius: 22px; transition: 0.3s; }
.slider:before { content: ""; position: absolute; height: 16px; width: 16px; left: 3px; bottom: 3px; background: white; border-radius: 50%; transition: 0.3s; }
.switch input:checked + .slider { background: #2ecc71; }
.switch input:checked + .slider:before { transform: translateX(18px); }
</style>
