<template>
  <div id="app">
    <LoginView v-if="!isLoggedIn" @login="handleLogin" />
    <MainView v-else :username="username" @logout="handleLogout" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import LoginView from './views/LoginView.vue'
import MainView from './views/MainView.vue'

const USER_KEY = 'user_username'
const isLoggedIn = ref(false)
const username = ref('')

onMounted(() => {
  const savedUsername = localStorage.getItem(USER_KEY)
  if (savedUsername) {
    username.value = savedUsername
    isLoggedIn.value = true
  }
})

const handleLogin = (user) => {
  username.value = user
  localStorage.setItem(USER_KEY, user)
  isLoggedIn.value = true
}

const handleLogout = () => {
  localStorage.removeItem(USER_KEY)
  username.value = ''
  isLoggedIn.value = false
}
</script>

<style>
@import './assets/style.css';
</style>
