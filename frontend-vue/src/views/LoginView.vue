<template>
  <div id="login-container">
    <h2>AIpolish 内部系统登录</h2>
    <p style="color: #64748b; margin-top: 0;">请输入您的授权用户名</p>
    <input
      v-model="username"
      type="text"
      placeholder="请输入用户名..."
      @keyup.enter="handleLogin"
    >
    <button @click="handleLogin">验证登录</button>
    <div v-if="errorMsg" style="color: red; margin-top: 10px; font-size: 14px;">
      {{ errorMsg }}
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
    await authAPI.login(user)
    emit('login', user)
  } catch (err) {
    errorMsg.value = err.message || '验证失败'
  }
}
</script>
