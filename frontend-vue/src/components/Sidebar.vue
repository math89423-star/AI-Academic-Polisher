<template>
  <div class="sidebar">
    <div class="sidebar-header">
      <button class="new-task-btn" @click="$emit('new-task')">
        + 新建润色任务
      </button>
    </div>
    <div class="history-list">
      <div
        v-for="task in tasks"
        :key="task.id"
        class="history-item"
        :class="{ active: task.id === currentTaskId }"
        @click="$emit('switch-task', task.id)"
      >
        <div class="history-time">
          <span>{{ task.time }}</span>
          <span>{{ getStatusIcon(task.status) }}</span>
        </div>
        <div class="history-preview">
          {{ getTaskIcon(task.task_type) }} {{ getTaskPreview(task) }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  tasks: Array,
  currentTaskId: Number
})

defineEmits(['new-task', 'switch-task'])

const getStatusIcon = (status) => {
  if (['completed', 'done'].includes(status)) return '✅'
  if (['failed', 'cancelled'].includes(status)) return '❌'
  return '⏳'
}

const getTaskIcon = (taskType) => {
  return taskType === 'docx' ? '📄' : '📝'
}

const getTaskPreview = (task) => {
  if (task.task_type === 'docx') {
    return task.title || 'Word文档'
  }
  return task.original ? task.original.substring(0, 10) + '...' : '新任务'
}
</script>
