<template>
  <div class="top-header">
    <h2 class="system-title">AI 极速学术润色系统</h2>
    <div class="user-info">
      当前用户: <span style="font-weight: bold; color: #1e293b;">{{ username }}</span>
      <button class="logout-btn" @click="$emit('logout')">退出</button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  username: String
})

defineEmits(['logout'])
</script>
