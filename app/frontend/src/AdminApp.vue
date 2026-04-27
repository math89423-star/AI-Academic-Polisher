<template>
  <div id="admin-app">
    <div class="admin-header">
      <h1>系统管理后台</h1>
      <button @click="logout" class="logout-btn">退出登录</button>
    </div>

    <div class="admin-container">
      <div class="tabs">
        <button :class="{ active: activeTab === 'users' }" @click="activeTab = 'users'">用户管理</button>
        <button :class="{ active: activeTab === 'api' }" @click="activeTab = 'api'">API 配置</button>
      </div>

      <div v-if="activeTab === 'users'" class="tab-content">
        <h2>用户列表</h2>
        <button @click="showAddUser = true" class="btn-primary">添加用户</button>
        <table class="data-table">
          <thead>
            <tr><th>用户名</th><th>角色</th><th>使用次数</th><th>操作</th></tr>
          </thead>
          <tbody>
            <tr v-for="user in users" :key="user.id">
              <td>{{ user.username }}</td>
              <td>{{ user.role }}</td>
              <td>{{ user.usage_count }}</td>
              <td><button @click="deleteUser(user.username)" class="btn-danger">删除</button></td>
            </tr>
          </tbody>
        </table>

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
            <tr><th>名称</th><th>Base URL</th><th>模型</th><th>操作</th></tr>
          </thead>
          <tbody>
            <tr v-for="config in apiConfigs" :key="config.id">
              <td>{{ config.name }}</td>
              <td>{{ config.base_url }}</td>
              <td>{{ config.model_name }}</td>
              <td><button @click="deleteApiConfig(config.id)" class="btn-danger">删除</button></td>
            </tr>
          </tbody>
        </table>

        <div v-if="showAddApi" class="modal">
          <div class="modal-content">
            <h3>添加 API 配置</h3>
            <input v-model="newApi.name" placeholder="配置名称" />
            <input v-model="newApi.api_key" placeholder="API Key" />
            <input v-model="newApi.base_url" placeholder="Base URL" />
            <input v-model="newApi.model_name" placeholder="模型名称" />
            <div class="modal-actions">
              <button @click="addApiConfig" class="btn-primary">确认</button>
              <button @click="showAddApi = false" class="btn-secondary">取消</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const activeTab = ref('users')
const users = ref([])
const apiConfigs = ref([])
const showAddUser = ref(false)
const showAddApi = ref(false)
const newUser = ref({ username: '', password: '', role: 'user' })
const newApi = ref({ name: '', api_key: '', base_url: '', model_name: 'gpt-3.5-turbo' })

const loadUsers = async () => {
  const res = await fetch('/api/admin/users')
  if (res.ok) users.value = await res.json()
}

const loadApiConfigs = async () => {
  const res = await fetch('/api/admin/api_configs')
  if (res.ok) apiConfigs.value = await res.json()
}

const addUser = async () => {
  const res = await fetch('/api/admin/users', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ new_username: newUser.value.username, ...newUser.value })
  })
  if (res.ok) {
    alert('添加成功')
    showAddUser.value = false
    newUser.value = { username: '', password: '', role: 'user' }
    loadUsers()
  }
}

const deleteUser = async (username) => {
  if (!confirm(`确认删除 ${username}?`)) return
  const res = await fetch(`/api/admin/users/${username}`, { method: 'DELETE' })
  if (res.ok) { alert('删除成功'); loadUsers() }
}

const addApiConfig = async () => {
  const res = await fetch('/api/admin/api_configs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(newApi.value)
  })
  if (res.ok) {
    alert('添加成功')
    showAddApi.value = false
    newApi.value = { name: '', api_key: '', base_url: '', model_name: 'gpt-3.5-turbo' }
    loadApiConfigs()
  }
}

const deleteApiConfig = async (id) => {
  if (!confirm('确认删除?')) return
  const res = await fetch(`/api/admin/api_configs/${id}`, { method: 'DELETE' })
  if (res.ok) { alert('删除成功'); loadApiConfigs() }
}

const logout = () => {
  localStorage.removeItem('user_username')
  window.location.href = '/'
}

onMounted(() => { loadUsers(); loadApiConfigs() })
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
</style>
