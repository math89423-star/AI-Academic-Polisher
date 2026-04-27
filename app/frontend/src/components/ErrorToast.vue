<template>
  <div class="error-toast">
    <div class="error-toast-title">错误类型: {{ error.type }}</div>
    <div class="error-toast-message">{{ error.message }}</div>
    <div v-if="error.suggestion" class="error-toast-message" style="margin-top: 8px; font-weight: 500;">
      💡 {{ error.suggestion }}
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'

const props = defineProps({
  error: Object
})

const emit = defineEmits(['close'])

onMounted(() => {
  setTimeout(() => {
    emit('close')
  }, 5000)
})
</script>

<style scoped>
.error-toast {
  position: fixed;
  top: 20px;
  right: 20px;
  background-color: #fee;
  border: 1px solid #fcc;
  border-radius: 8px;
  padding: 15px 20px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 9999;
  max-width: 400px;
  animation: slideIn 0.3s ease;
}

.error-toast-title {
  font-weight: bold;
  color: #c00;
  margin-bottom: 8px;
}

.error-toast-message {
  color: #333;
  font-size: 14px;
}

@keyframes slideIn {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}
</style>
