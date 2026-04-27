<template>
  <div class="top-header">
    <h2 class="system-title">AI 极速学术润色系统</h2>
    <div class="user-info">
      当前用户: <span style="font-weight: bold; color: #1e293b;">{{ username }}</span>
      <span v-if="userRole === 'admin'" class="role-badge">管理员</span>
      <button class="logout-btn" @click="$emit('logout')">退出</button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  username: String,
  userRole: String
})

defineEmits(['logout'])
</script>

<style scoped>
.top-header { display: flex; justify-content: space-between; align-items: center; padding: 12px 20px; background: #f8fafc; border-bottom: 1px solid #e2e8f0; }
.system-title { margin: 0; font-size: 18px; color: #1e293b; white-space: nowrap; }
.user-info { display: flex; align-items: center; gap: 8px; font-size: 14px; white-space: nowrap; }
.role-badge { background: #dbeafe; color: #1d4ed8; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 500; }
.logout-btn { background: #ef4444; color: white; border: none; padding: 6px 14px; border-radius: 4px; cursor: pointer; font-size: 13px; }
</style>
