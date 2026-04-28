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
          <button :class="{ active: activeTab === 'system' }" @click="activeTab = 'system'">系统设置</button>
        </div>

        <UserManagementTab v-if="activeTab === 'users'" :api-configs="apiConfigs" :admin-username="adminUsername" />
        <ApiConfigTab v-if="activeTab === 'api'" :admin-username="adminUsername" @configs-updated="apiConfigs = $event" />
        <ThemeSettingsTab v-if="activeTab === 'theme'" :admin-username="adminUsername" />
        <SystemSettingsTab v-if="activeTab === 'system'" :admin-username="adminUsername" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import UserManagementTab from './components/admin/UserManagementTab.vue'
import ApiConfigTab from './components/admin/ApiConfigTab.vue'
import ThemeSettingsTab from './components/admin/ThemeSettingsTab.vue'
import SystemSettingsTab from './components/admin/SystemSettingsTab.vue'
const activeTab = ref('users')
const apiConfigs = ref([])

const isLoggedIn = ref(false)
const currentUsername = ref('')
const loginUsername = ref('')
const loginPassword = ref('')
const loginError = ref('')

const adminUsername = computed(() => sessionStorage.getItem('admin_username') || '')

const loadApiConfigs = async () => {
  const res = await fetch(`/api/admin/api_configs?admin_username=${adminUsername.value}`)
  if (res.ok) apiConfigs.value = await res.json()
}

const checkLoginStatus = () => {
  const saved = sessionStorage.getItem('admin_username')
  if (saved) {
    isLoggedIn.value = true
    currentUsername.value = saved
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
      loadApiConfigs()
    } else {
      const data = await res.json()
      loginError.value = data.error || '用户名或密码错误'
    }
  } catch (error) {
    loginError.value = '服务尚未就绪或网络错误，请稍后重试'
  }
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
.login-container { max-width: 400px; margin: 100px auto; padding: 40px; background: white; border-radius: 16px; box-shadow: 0 8px 32px rgba(0,0,0,0.12); }
.login-container h2 { margin-bottom: 30px; text-align: center; color: #1e293b; }
.login-container input { width: 100%; padding: 12px; margin-bottom: 16px; border: 1px solid #e2e8f0; border-radius: 8px; transition: border-color 0.2s; }
.login-container input:focus { border-color: #3498db; outline: none; box-shadow: 0 0 0 3px rgba(52,152,219,0.1); }
.header-right { display: flex; align-items: center; gap: 15px; }
.username { color: #ecf0f1; font-size: 14px; }
</style>
