<template>
  <div class="app-layout">
    <Sidebar
      :tasks="taskStore.sortedTasks"
      :current-task-id="taskStore.currentTaskId"
      @new-task="taskStore.createNewTask"
      @switch-task="taskStore.switchTask"
    />

    <div class="main-workspace">
      <TopHeader :username="username" @logout="$emit('logout')" />

      <div class="comparison-region">
        <EditorPanel
          :username="username"
          :current-task="taskStore.currentTask"
          :strategies="taskStore.strategies"
          @task-created="handleTaskCreated"
        />

        <ResultPanel
          :current-task="taskStore.currentTask"
          @cancel="handleCancel"
          @resume="handleResume"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import { useTaskStore } from '../stores/taskStore'
import Sidebar from '../components/Sidebar.vue'
import TopHeader from '../components/TopHeader.vue'
import EditorPanel from '../components/EditorPanel.vue'
import ResultPanel from '../components/ResultPanel.vue'

const props = defineProps({
  username: String
})

const emit = defineEmits(['logout'])

const taskStore = useTaskStore()

onMounted(async () => {
  await taskStore.loadHistory(props.username)
  await taskStore.loadStrategies()
})

onUnmounted(() => {
  taskStore.stopSSE()
})

const handleTaskCreated = (taskId) => {
  taskStore.startSSE(taskId)
}

const handleCancel = async () => {
  if (taskStore.currentTaskId) {
    await taskStore.cancelTask(taskStore.currentTaskId)
  }
}

const handleResume = async () => {
  if (taskStore.currentTaskId) {
    await taskStore.resumeTask(taskStore.currentTaskId)
  }
}
</script>
