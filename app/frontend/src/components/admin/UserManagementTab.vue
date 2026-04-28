<template>
  <div class="tab-content">
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
            <select class="inline-select" :value="user.api_config_id_standard"
              @change="updateUserConfig(user.username, 'standard', $event.target.value)">
              <option :value="null">系统默认</option>
              <option v-for="c in apiConfigs" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
          </td>
          <td>
            <select class="inline-select" :value="user.api_config_id_strict"
              @change="updateUserConfig(user.username, 'strict', $event.target.value)">
              <option :value="null">系统默认</option>
              <option v-for="c in apiConfigs" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
          </td>
          <td>
            <label class="switch">
              <input type="checkbox" :checked="user.can_use_strict"
                @change="toggleStrictPermission(user.username, $event.target.checked)" />
              <span class="slider"></span>
            </label>
          </td>
          <td><button @click="deleteUser(user.username)" class="btn-danger">删除</button></td>
        </tr>
      </tbody>
    </table>

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
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const props = defineProps({
  apiConfigs: { type: Array, required: true },
  adminUsername: { type: String, required: true }
})

const users = ref([])
const showAddUser = ref(false)
const newUser = ref({ username: '', password: '', role: 'user' })
const selectedUsers = ref([])
const showBatchAssign = ref(false)
const batchMode = ref('standard')
const batchConfigId = ref(null)

const isAllSelected = computed(() => {
  return users.value.length > 0 && selectedUsers.value.length === users.value.length
})

const toggleSelectAll = (e) => {
  selectedUsers.value = e.target.checked ? users.value.map(u => u.username) : []
}

const loadUsers = async () => {
  const res = await fetch(`/api/admin/users?admin_username=${props.adminUsername}`)
  if (res.ok) users.value = await res.json()
}

const addUser = async () => {
  const res = await fetch('/api/admin/users', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ admin_username: props.adminUsername, new_username: newUser.value.username, ...newUser.value })
  })
  if (res.ok) {
    alert('添加成功')
    showAddUser.value = false
    newUser.value = { username: '', password: '', role: 'user' }
    loadUsers()
  }
}

const updateUserConfig = async (targetUsername, mode, configId) => {
  const res = await fetch('/api/admin/users/update_config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      admin_username: props.adminUsername,
      target_username: targetUsername,
      mode,
      api_config_id: configId === 'null' ? null : Number(configId)
    })
  })
  if (res.ok) loadUsers()
}

const toggleStrictPermission = async (targetUsername, canUseStrict) => {
  await fetch('/api/admin/users/update_strict_permission', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ admin_username: props.adminUsername, target_username: targetUsername, can_use_strict: canUseStrict })
  })
}

const batchAssign = async () => {
  const res = await fetch('/api/admin/users/batch_update_config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      admin_username: props.adminUsername,
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

const deleteUser = async (username) => {
  if (!confirm(`确认删除 ${username}?`)) return
  const res = await fetch(`/api/admin/users/${username}?admin_username=${props.adminUsername}`, { method: 'DELETE' })
  if (res.ok) { alert('删除成功'); loadUsers() }
}

onMounted(() => { loadUsers() })
</script>

<style scoped>
.toolbar { display: flex; gap: 10px; align-items: center; }
.inline-select { padding: 6px 10px; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 13px; background: white; min-width: 120px; }
.switch { position: relative; display: inline-block; width: 40px; height: 22px; }
.switch input { opacity: 0; width: 0; height: 0; }
.slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background: #ccc; border-radius: 22px; transition: 0.3s; }
.slider:before { content: ""; position: absolute; height: 16px; width: 16px; left: 3px; bottom: 3px; background: white; border-radius: 50%; transition: 0.3s; }
.switch input:checked + .slider { background: #2ecc71; }
.switch input:checked + .slider:before { transform: translateX(18px); }
</style>
