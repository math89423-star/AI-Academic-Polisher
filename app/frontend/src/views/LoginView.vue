<template>
  <div id="login-container">
    <div class="login-card">
      <div class="login-brand">AI Polish</div>
      <h2>内部系统登录</h2>
      <p style="color: rgba(255,255,255,0.7); margin-top: 0; margin-bottom: 20px; font-size: 14px;">请输入您的授权用户名</p>
      <input
        v-model="username"
        type="text"
        placeholder="请输入用户名..."
        @keyup.enter="handleLogin"
      >
      <button @click="handleLogin">验证登录</button>
      <div v-if="errorMsg" style="color: #fca5a5; margin-top: 10px; font-size: 14px;">
        {{ errorMsg }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { authAPI } from '../api'

const emit = defineEmits(['login'])

const username = ref('')
const errorMsg = ref('')

const handleLogin = async () => {
  const user = username.value.trim()
  if (!user) {
    errorMsg.value = '用户名不能为空'
    return
  }

  try {
    const data = await authAPI.login(user)
    emit('login', { username: data.username, role: data.role })
  } catch (err) {
    errorMsg.value = err.message || '验证失败'
  }
}
</script>

<style scoped>
.login-card { text-align: center; }
.login-brand { font-size: 32px; font-weight: 700; color: white; margin-bottom: 8px; letter-spacing: -0.5px; }
</style>
