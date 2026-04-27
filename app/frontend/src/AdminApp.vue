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
        <button :class="{ active: activeTab === 'theme' }" @click="activeTab = 'theme'">主题设置</button>
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

      <div v-if="activeTab === 'theme'" class="tab-content">
        <h2>主题设置</h2>
        <p style="color: #64748b; margin-bottom: 20px;">自定义系统主题色和页面背景，保存后对所有用户生效</p>

        <div class="theme-form">
          <div class="theme-row">
            <label class="form-label">主题主色调</label>
            <div style="display: flex; align-items: center; gap: 12px;">
              <input type="color" v-model="themeConfig.primary_color" class="color-picker" />
              <input type="text" v-model="themeConfig.primary_color" class="color-input" placeholder="#3b82f6" />
              <button class="btn-sm" @click="themeConfig.primary_color = '#3b82f6'">重置</button>
            </div>
          </div>

          <div class="theme-row">
            <label class="form-label">背景类型</label>
            <div class="bg-type-group">
              <button :class="{ active: themeConfig.bg_type === 'color' }" @click="themeConfig.bg_type = 'color'">纯色</button>
              <button :class="{ active: themeConfig.bg_type === 'gradient' }" @click="themeConfig.bg_type = 'gradient'">渐变</button>
              <button :class="{ active: themeConfig.bg_type === 'image' }" @click="themeConfig.bg_type = 'image'">背景图</button>
            </div>
          </div>

          <div v-if="themeConfig.bg_type === 'color'" class="theme-row">
            <label class="form-label">背景颜色</label>
            <div style="display: flex; align-items: center; gap: 12px;">
              <input type="color" v-model="themeConfig.bg_value" class="color-picker" />
              <input type="text" v-model="themeConfig.bg_value" class="color-input" />
            </div>
          </div>

          <div v-if="themeConfig.bg_type === 'gradient'" class="theme-row">
            <label class="form-label">渐变 CSS</label>
            <input type="text" v-model="themeConfig.bg_value" placeholder="linear-gradient(135deg, #667eea, #764ba2)" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px;" />
            <div class="field-hint">输入完整的 CSS 渐变值，如 linear-gradient(135deg, #667eea, #764ba2)</div>
          </div>

          <div v-if="themeConfig.bg_type === 'image'" class="theme-row">
            <label class="form-label">背景图片</label>
            <div class="upload-area" @click="$refs.bgFileInput.click()" @dragover.prevent @drop.prevent="handleBgDrop">
              <input ref="bgFileInput" type="file" accept="image/*" style="display:none" @change="handleBgUpload" />
              <div v-if="!themeConfig.bg_value" class="upload-placeholder">
                <div style="font-size: 36px; margin-bottom: 8px;">📁</div>
                <div>点击或拖拽上传背景图片</div>
                <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">支持 JPG / PNG / WebP，建议 1920x1080 以上</div>
              </div>
              <div v-else class="upload-preview">
                <img :src="themeConfig.bg_value" alt="背景预览" />
                <button class="remove-bg-btn" @click.stop="themeConfig.bg_value = ''">移除图片</button>
              </div>
            </div>
            <div v-if="bgUploading" style="color: #f59e0b; font-size: 13px; margin-top: 8px;">上传中...</div>

            <div class="theme-row" style="margin-top: 16px;">
              <label class="form-label">背景透明度: {{ Math.round((themeConfig.bg_opacity ?? 1) * 100) }}%</label>
              <input type="range" min="0.1" max="1" step="0.05" v-model.number="themeConfig.bg_opacity" class="opacity-slider" />
            </div>

            <div class="theme-row">
              <label class="form-label">缩放模式</label>
              <div class="bg-type-group">
                <button :class="{ active: themeConfig.bg_size === 'cover' }" @click="themeConfig.bg_size = 'cover'">铺满 (Cover)</button>
                <button :class="{ active: themeConfig.bg_size === 'contain' }" @click="themeConfig.bg_size = 'contain'">适应 (Contain)</button>
                <button :class="{ active: themeConfig.bg_size === 'auto' }" @click="themeConfig.bg_size = 'auto'">平铺 (Tile)</button>
              </div>
            </div>
          </div>

          <div class="theme-preview" :style="previewStyle">
            <div class="preview-label">预览效果</div>
            <div v-if="themeConfig.bg_type === 'image' && themeConfig.bg_value" class="preview-thumbnail">
              <img :src="themeConfig.bg_value" alt="背景缩略图" />
            </div>
            <div class="preview-card" :style="{ borderColor: themeConfig.primary_color }">
              <div class="preview-header" :style="{ background: themeConfig.primary_color }">标题栏</div>
              <div class="preview-body">内容区域示例文本</div>
            </div>
          </div>

          <button @click="saveTheme" class="btn-primary" style="margin-top: 20px;">保存主题配置</button>
          <button @click="resetTheme" class="btn-secondary" style="margin-top: 20px; margin-left: 10px;">恢复默认主题</button>
        </div>
      </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const activeTab = ref('users')
const themeConfig = ref({ primary_color: '#3b82f6', bg_type: 'color', bg_value: '#f1f5f9', bg_opacity: 1, bg_size: 'cover' })
const bgUploading = ref(false)
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
const testingAll = ref(false)
const testAllResult = ref(null)
const testAllResults = ref({})

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
    loadTheme()
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
      loadTheme()
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

const testAllConfigs = async () => {
  testingAll.value = true
  testAllResult.value = null
  testAllResults.value = {}

  try {
    const username = getAdminUsername()
    const res = await fetch('/api/admin/api_configs/test_all', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ admin_username: username })
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

const previewStyle = computed(() => {
  const t = themeConfig.value
  if (t.bg_type === 'image' && t.bg_value) {
    return {
      backgroundImage: `url(${t.bg_value})`,
      backgroundSize: t.bg_size || 'cover',
      backgroundPosition: 'center',
      backgroundRepeat: t.bg_size === 'auto' ? 'repeat' : 'no-repeat',
      opacity: t.bg_opacity ?? 1
    }
  } else if (t.bg_type === 'gradient' && t.bg_value) {
    return { backgroundImage: t.bg_value }
  }
  return { backgroundColor: t.bg_value || '#f1f5f9' }
})

const loadTheme = async () => {
  const username = getAdminUsername()
  try {
    const res = await fetch(`/api/admin/theme?admin_username=${username}`)
    if (res.ok) {
      const data = await res.json()
      themeConfig.value = { primary_color: '#3b82f6', bg_type: 'color', bg_value: '#f1f5f9', bg_opacity: 1, bg_size: 'cover', ...data }
    }
  } catch (e) { /* ignore */ }
}

const saveTheme = async () => {
  const username = getAdminUsername()
  const res = await fetch('/api/admin/theme', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ admin_username: username, ...themeConfig.value })
  })
  if (res.ok) alert('主题保存成功，刷新用户页面即可生效')
  else alert('保存失败')
}

const resetTheme = async () => {
  if (!confirm('确认恢复为默认主题？将清除所有自定义设置。')) return
  themeConfig.value = { primary_color: '#3b82f6', bg_type: 'color', bg_value: '#f1f5f9', bg_opacity: 1, bg_size: 'cover' }
  await saveTheme()
}

const handleBgUpload = async (event) => {
  const file = event.target.files[0]
  if (!file) return
  await uploadBgFile(file)
  event.target.value = ''
}

const handleBgDrop = async (event) => {
  const file = event.dataTransfer.files[0]
  if (file && file.type.startsWith('image/')) await uploadBgFile(file)
}

const uploadBgFile = async (file) => {
  bgUploading.value = true
  try {
    const username = getAdminUsername()
    const formData = new FormData()
    formData.append('file', file)
    formData.append('admin_username', username)
    const res = await fetch('/api/admin/theme/upload', { method: 'POST', body: formData })
    if (res.ok) {
      const data = await res.json()
      themeConfig.value.bg_value = data.url
    } else {
      alert('上传失败')
    }
  } catch (e) {
    alert('上传出错: ' + e.message)
  } finally {
    bgUploading.value = false
  }
}

onMounted(() => { checkLoginStatus() })
</script>

<style scoped>
#admin-app { min-height: 100vh; background: linear-gradient(135deg, #f5f7fa 0%, #e4e9f0 100%); }
.admin-header { background: linear-gradient(135deg, #1e3a5f, #2c3e50, #34495e); color: white; padding: 20px 30px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 12px rgba(0,0,0,0.15); }
.admin-header h1 { font-size: 20px; font-weight: 600; }
.logout-btn { background: #e74c3c; color: white; border: none; padding: 8px 18px; border-radius: 6px; cursor: pointer; transition: all 0.2s; }
.logout-btn:hover { background: #c0392b; transform: translateY(-1px); }
.admin-container { max-width: 1200px; margin: 24px auto; background: white; padding: 24px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }
.tabs { display: flex; gap: 6px; margin-bottom: 24px; padding-bottom: 0; border-bottom: none; background: #f1f5f9; border-radius: 8px; padding: 4px; }
.tabs button { padding: 10px 20px; border: none; background: transparent; cursor: pointer; font-size: 14px; border-radius: 6px; transition: all 0.2s; color: #64748b; font-weight: 500; }
.tabs button.active { background: white; color: #3498db; box-shadow: 0 1px 4px rgba(0,0,0,0.1); }
.tabs button:hover:not(.active) { color: #334155; }
.tab-content h2 { margin-bottom: 20px; font-size: 18px; color: #1e293b; }
.data-table { width: 100%; border-collapse: separate; border-spacing: 0; margin-top: 16px; border-radius: 8px; overflow: hidden; border: 1px solid #e2e8f0; }
.data-table th, .data-table td { padding: 12px 16px; text-align: left; }
.data-table th { background: #f8fafc; font-weight: 600; color: #475569; font-size: 13px; border-bottom: 2px solid #e2e8f0; }
.data-table td { border-bottom: 1px solid #f1f5f9; }
.data-table tbody tr:nth-child(even) { background: #fafbfc; }
.data-table tbody tr:hover { background: #f0f7ff; }
.btn-primary { background: linear-gradient(135deg, #3498db, #2980b9); color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; margin-bottom: 16px; transition: all 0.2s; font-weight: 500; }
.btn-primary:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(52,152,219,0.3); }
.btn-danger { background: #e74c3c; color: white; border: none; padding: 6px 14px; border-radius: 6px; cursor: pointer; transition: all 0.2s; }
.btn-danger:hover { background: #c0392b; }
.btn-secondary { background: #95a5a6; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; transition: all 0.2s; }
.btn-secondary:hover { background: #7f8c8d; }
.modal { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.4); backdrop-filter: blur(4px); display: flex; justify-content: center; align-items: center; z-index: 1000; animation: fadeIn 0.2s ease; }
.modal-content { background: white; padding: 30px; border-radius: 12px; min-width: 420px; box-shadow: 0 20px 60px rgba(0,0,0,0.2); animation: slideUp 0.3s ease; }
.modal-content h3 { margin-bottom: 20px; font-size: 16px; color: #1e293b; }
.modal-content input, .modal-content select { width: 100%; padding: 10px; margin-bottom: 15px; border: 1px solid #e2e8f0; border-radius: 6px; transition: border-color 0.2s; }
.modal-content input:focus { border-color: #3498db; outline: none; box-shadow: 0 0 0 3px rgba(52,152,219,0.1); }
.modal-actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 10px; }
.form-label { display: block; margin-bottom: 6px; font-weight: 500; color: #334155; font-size: 14px; }
.form-select { width: 100%; padding: 10px; margin-bottom: 15px; border: 1px solid #e2e8f0; border-radius: 6px; background: white; }
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
.test-result { padding: 12px; border-radius: 6px; margin-bottom: 15px; font-size: 14px; }
.test-result.success { background: #e8f5e9; color: #2e7d32; border: 1px solid #4caf50; }
.test-result.error { background: #ffebee; color: #c62828; border: 1px solid #f44336; }
.login-container { max-width: 400px; margin: 100px auto; padding: 40px; background: white; border-radius: 16px; box-shadow: 0 8px 32px rgba(0,0,0,0.12); }
.login-container h2 { margin-bottom: 30px; text-align: center; color: #1e293b; }
.login-container input { width: 100%; padding: 12px; margin-bottom: 16px; border: 1px solid #e2e8f0; border-radius: 8px; transition: border-color 0.2s; }
.login-container input:focus { border-color: #3498db; outline: none; box-shadow: 0 0 0 3px rgba(52,152,219,0.1); }
.error-msg { color: #e74c3c; margin-top: 10px; font-size: 14px; }
.header-right { display: flex; align-items: center; gap: 15px; }
.username { color: #ecf0f1; font-size: 14px; }
.required { color: #e74c3c; margin-left: 2px; }
.field-hint { font-size: 12px; color: #94a3b8; margin: 4px 0 15px 0; }
.toolbar { display: flex; gap: 10px; align-items: center; }
.inline-select { padding: 6px 10px; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 13px; background: white; min-width: 120px; }
.switch { position: relative; display: inline-block; width: 40px; height: 22px; }
.switch input { opacity: 0; width: 0; height: 0; }
.slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background: #ccc; border-radius: 22px; transition: 0.3s; }
.slider:before { content: ""; position: absolute; height: 16px; width: 16px; left: 3px; bottom: 3px; background: white; border-radius: 50%; transition: 0.3s; }
.switch input:checked + .slider { background: #2ecc71; }
.switch input:checked + .slider:before { transform: translateX(18px); }
.btn-sm { padding: 6px 12px; font-size: 12px; border: 1px solid #e2e8f0; background: white; border-radius: 6px; cursor: pointer; color: #64748b; transition: all 0.2s; }
.btn-sm:hover { background: #f1f5f9; }
.color-picker { width: 40px; height: 36px; border: none; border-radius: 6px; cursor: pointer; padding: 0; }
.color-input { width: 100px; padding: 8px; border: 1px solid #e2e8f0; border-radius: 6px; font-family: monospace; }
.theme-form { max-width: 600px; }
.theme-row { margin-bottom: 24px; }
.bg-type-group { display: flex; gap: 4px; background: #f1f5f9; border-radius: 8px; padding: 4px; }
.bg-type-group button { padding: 8px 20px; border: none; background: transparent; cursor: pointer; border-radius: 6px; font-size: 13px; color: #64748b; transition: all 0.2s; }
.bg-type-group button.active { background: white; color: #3498db; box-shadow: 0 1px 4px rgba(0,0,0,0.1); }
.upload-area { border: 2px dashed #d1d5db; border-radius: 12px; padding: 30px; text-align: center; cursor: pointer; transition: all 0.2s; min-height: 160px; display: flex; align-items: center; justify-content: center; }
.upload-area:hover { border-color: #3498db; background: #f8faff; }
.upload-placeholder { color: #64748b; font-size: 14px; }
.upload-preview { position: relative; width: 100%; }
.upload-preview img { max-width: 100%; max-height: 200px; border-radius: 8px; object-fit: cover; }
.remove-bg-btn { position: absolute; top: 8px; right: 8px; background: rgba(239,68,68,0.9); color: white; border: none; padding: 4px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; }
.theme-preview { margin-top: 24px; padding: 24px; border-radius: 12px; border: 1px solid #e2e8f0; min-height: 160px; position: relative; display: flex; align-items: flex-start; gap: 20px; }
.preview-label { position: absolute; top: -10px; left: 12px; background: white; padding: 0 8px; font-size: 12px; color: #94a3b8; }
.preview-thumbnail { width: 160px; height: 100px; border-radius: 8px; overflow: hidden; border: 1px solid #e2e8f0; flex-shrink: 0; }
.preview-thumbnail img { width: 100%; height: 100%; object-fit: cover; }
.preview-card { border: 2px solid; border-radius: 8px; overflow: hidden; max-width: 300px; }
.preview-header { color: white; padding: 10px 16px; font-size: 14px; font-weight: 500; }
.preview-body { padding: 16px; font-size: 13px; color: #475569; background: white; }
.opacity-slider { width: 100%; height: 6px; -webkit-appearance: none; appearance: none; background: linear-gradient(90deg, #e2e8f0, #3498db); border-radius: 3px; outline: none; cursor: pointer; }
.opacity-slider::-webkit-slider-thumb { -webkit-appearance: none; width: 18px; height: 18px; border-radius: 50%; background: white; border: 2px solid #3498db; cursor: pointer; box-shadow: 0 1px 4px rgba(0,0,0,0.15); }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
@keyframes slideUp { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
</style>
