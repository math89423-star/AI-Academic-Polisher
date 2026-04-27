<template>
  <div v-if="userRole === 'admin' && configs.length > 0" class="config-switcher">
    <label class="switcher-label">
      平衡:
      <select class="switcher-select" :value="currentStandard" @change="switchConfig('standard', $event.target.value)">
        <option :value="''">默认</option>
        <option v-for="c in configs" :key="c.id" :value="c.id">{{ c.name }}</option>
      </select>
    </label>
    <label class="switcher-label">
      极致:
      <select class="switcher-select" :value="currentStrict" @change="switchConfig('strict', $event.target.value)">
        <option :value="''">默认</option>
        <option v-for="c in configs" :key="c.id" :value="c.id">{{ c.name }}</option>
      </select>
    </label>
    <span v-if="switchMsg" class="switch-msg">{{ switchMsg }}</span>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const props = defineProps({
  username: String,
  userRole: String
})

const configs = ref([])
const currentStandard = ref('')
const currentStrict = ref('')
const switchMsg = ref('')

const loadConfigs = async () => {
  try {
    const res = await fetch('/api/admin/api_configs')
    if (res.ok) configs.value = await res.json()
  } catch (e) { /* ignore */ }
}

const switchConfig = async (mode, configId) => {
  try {
    const res = await fetch('/api/admin/users/update_config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        admin_username: props.username,
        target_username: props.username,
        mode,
        api_config_id: configId ? Number(configId) : null
      })
    })
    if (res.ok) {
      if (mode === 'standard') currentStandard.value = configId
      else currentStrict.value = configId
      switchMsg.value = '已切换'
      setTimeout(() => { switchMsg.value = '' }, 1500)
    }
  } catch (e) { /* ignore */ }
}

onMounted(loadConfigs)
</script>

<style scoped>
.config-switcher { display: flex; align-items: center; gap: 12px; padding: 6px 16px; background: #eef2ff; border-bottom: 1px solid #e2e8f0; font-size: 13px; }
.switcher-label { display: flex; align-items: center; gap: 4px; color: #475569; white-space: nowrap; }
.switcher-select { padding: 2px 6px; border: 1px solid #c7d2fe; border-radius: 4px; font-size: 12px; background: white; max-width: 140px; }
.switch-msg { color: #10b981; font-size: 12px; font-weight: 500; }
</style>
