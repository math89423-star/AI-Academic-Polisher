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
          <span class="history-right">
            <span>{{ getStatusIcon(task.status) }}</span>
            <button
              v-if="canDelete(task.status)"
              class="delete-btn"
              title="删除"
              @click.stop="handleDelete(task.id)"
            >×</button>
          </span>
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

const emit = defineEmits(['new-task', 'switch-task', 'delete-task'])

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

const canDelete = (status) => {
  return !['processing', 'queued'].includes(status)
}

const handleDelete = (taskId) => {
  if (confirm('确定要删除这条任务记录吗？')) {
    emit('delete-task', taskId)
  }
}
</script>

<style scoped>
.history-right { display: inline-flex; align-items: center; gap: 4px; }
.delete-btn { background: none; border: none; color: #94a3b8; cursor: pointer; font-size: 16px; padding: 0 2px; line-height: 1; }
.delete-btn:hover { color: #ef4444; }
</style>
