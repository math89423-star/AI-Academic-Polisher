<template>
  <div class="app-layout">
    <Sidebar
      :tasks="taskStore.sortedTasks"
      :current-task-id="taskStore.currentTaskId"
      @new-task="taskStore.createNewTask"
      @switch-task="taskStore.switchTask"
      @delete-task="handleDeleteTask"
      @delete-all="handleDeleteAll"
    />

    <div class="main-workspace">
      <TopHeader :username="username" :user-role="userRole" @logout="$emit('logout')" />
      <ConfigSwitcher :username="username" :user-role="userRole" />

      <div class="queue-status">
        当前排队任务: {{ taskStore.pendingCount }} 个
      </div>

      <div class="comparison-region">
        <EditorPanel
          :username="username"
          :current-task="taskStore.currentTask"
          :strategies="taskStore.strategies"
          @task-created="handleTaskCreated"
          @cancel="handleCancel"
          @resume="handleResume"
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
import ConfigSwitcher from '../components/ConfigSwitcher.vue'
import EditorPanel from '../components/EditorPanel.vue'
import ResultPanel from '../components/ResultPanel.vue'

const props = defineProps({
  username: String,
  userRole: String
})

const emit = defineEmits(['logout'])

const taskStore = useTaskStore()

onMounted(async () => {
  await taskStore.loadHistory(props.username)
  await taskStore.loadStrategies(props.username)
  taskStore.startQueuePolling()

  const activeTask = Object.values(taskStore.tasks).find(
    t => t.status === 'processing' || t.status === 'queued'
  )
  if (activeTask) {
    taskStore.switchTask(activeTask.id)
    taskStore.startSSE(activeTask.id)
  }
})

onUnmounted(() => {
  taskStore.stopSSE()
  taskStore.stopQueuePolling()
})

const handleTaskCreated = (taskId) => {
  taskStore.startSSE(taskId)
}

const handleCancel = async () => {
  if (taskStore.currentTaskId) {
    await taskStore.cancelTask(taskStore.currentTaskId, props.username)
  }
}

const handleResume = async () => {
  if (taskStore.currentTaskId) {
    await taskStore.resumeTask(taskStore.currentTaskId, props.username)
  }
}

const handleDeleteTask = async (taskId) => {
  try {
    await taskStore.deleteTask(taskId, props.username)
  } catch (err) {
    alert(err.message || '删除失败')
  }
}

const handleDeleteAll = async () => {
  try {
    await taskStore.deleteAllTasks(props.username)
  } catch (err) {
    alert(err.message || '清空失败')
  }
}
</script>

<style scoped>
.queue-status { padding: 8px 20px; background: linear-gradient(135deg, #fef3c7, #fde68a); color: #92400e; font-size: 13px; border-bottom: 1px solid #fde68a; font-weight: 500; }
</style>
