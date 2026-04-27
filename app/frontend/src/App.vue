<template>
  <div id="app">
    <LoginView v-if="!isLoggedIn" @login="handleLogin" />
    <MainView v-else :username="username" :user-role="userRole" @logout="handleLogout" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import LoginView from './views/LoginView.vue'
import MainView from './views/MainView.vue'

const USER_KEY = 'user_username'
const ROLE_KEY = 'user_role'
const isLoggedIn = ref(false)
const username = ref('')
const userRole = ref('')

onMounted(async () => {
  const savedUsername = localStorage.getItem(USER_KEY)
  if (savedUsername) {
    username.value = savedUsername
    userRole.value = localStorage.getItem(ROLE_KEY) || ''
    isLoggedIn.value = true
  }
  await loadTheme()
})

const handleLogin = (loginData) => {
  username.value = loginData.username
  userRole.value = loginData.role || ''
  localStorage.setItem(USER_KEY, loginData.username)
  localStorage.setItem(ROLE_KEY, loginData.role || '')
  isLoggedIn.value = true
}

const handleLogout = () => {
  localStorage.removeItem(USER_KEY)
  localStorage.removeItem(ROLE_KEY)
  username.value = ''
  userRole.value = ''
  isLoggedIn.value = false
}

const loadTheme = async () => {
  try {
    const res = await fetch('/api/auth/theme')
    if (!res.ok) return
    const theme = await res.json()
    const root = document.documentElement

    if (theme.primary_color) {
      root.style.setProperty('--primary-color', theme.primary_color)
      root.style.setProperty('--primary-hover', darkenColor(theme.primary_color, 15))
    }

    if (theme.bg_type === 'image' && theme.bg_value) {
      document.body.style.backgroundImage = `url(${theme.bg_value})`
      document.body.style.backgroundSize = theme.bg_size || 'cover'
      document.body.style.backgroundPosition = 'center'
      document.body.style.backgroundAttachment = 'fixed'
      document.body.style.backgroundRepeat = theme.bg_size === 'auto' ? 'repeat' : 'no-repeat'
      document.body.classList.add('bg-image-mode')
      const opacity = theme.bg_opacity ?? 1
      root.style.setProperty('--panel-opacity', Math.min(1, 1.05 - opacity * 0.3).toFixed(2))
    } else if (theme.bg_type === 'gradient' && theme.bg_value) {
      document.body.style.backgroundImage = theme.bg_value
      document.body.classList.remove('bg-image-mode')
    } else if (theme.bg_type === 'color' && theme.bg_value) {
      root.style.setProperty('--bg-color', theme.bg_value)
      document.body.style.backgroundImage = 'none'
      document.body.classList.remove('bg-image-mode')
    }
  } catch (e) {
    // theme load is best-effort
  }
}

const darkenColor = (hex, percent) => {
  const num = parseInt(hex.replace('#', ''), 16)
  const r = Math.max(0, (num >> 16) - Math.round(2.55 * percent))
  const g = Math.max(0, ((num >> 8) & 0x00FF) - Math.round(2.55 * percent))
  const b = Math.max(0, (num & 0x0000FF) - Math.round(2.55 * percent))
  return `#${(r << 16 | g << 8 | b).toString(16).padStart(6, '0')}`
}
</script>

<style>
@import './assets/style.css';
</style>
