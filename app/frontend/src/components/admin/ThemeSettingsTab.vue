<template>
  <div class="tab-content">
    <h2>主题设置</h2>
    <p style="color: #64748b; margin-bottom: 20px;">自定义系统主题色和页面背景，保存后对所有用户生效</p>

    <div class="theme-form">
      <div class="theme-row">
        <label class="form-label">主题主色调</label>
        <div style="display: flex; align-items: center; gap: 12px;">
          <input type="color" v-model="themeConfig.primary_color" class="color-picker" />
          <input type="text" v-model="themeConfig.primary_color" class="color-input" placeholder="#3b82f6" />
          <button class="btn-sm" @click="themeConfig.primary_color = '#3b82f6'">重置</button>
        </div>
      </div>

      <div class="theme-row">
        <label class="form-label">背景类型</label>
        <div class="bg-type-group">
          <button :class="{ active: themeConfig.bg_type === 'color' }" @click="themeConfig.bg_type = 'color'">纯色</button>
          <button :class="{ active: themeConfig.bg_type === 'gradient' }" @click="themeConfig.bg_type = 'gradient'">渐变</button>
          <button :class="{ active: themeConfig.bg_type === 'image' }" @click="themeConfig.bg_type = 'image'">背景图</button>
        </div>
      </div>

      <div v-if="themeConfig.bg_type === 'color'" class="theme-row">
        <label class="form-label">背景颜色</label>
        <div style="display: flex; align-items: center; gap: 12px;">
          <input type="color" v-model="themeConfig.bg_value" class="color-picker" />
          <input type="text" v-model="themeConfig.bg_value" class="color-input" />
        </div>
      </div>

      <div v-if="themeConfig.bg_type === 'gradient'" class="theme-row">
        <label class="form-label">渐变 CSS</label>
        <input type="text" v-model="themeConfig.bg_value" placeholder="linear-gradient(135deg, #667eea, #764ba2)" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px;" />
        <div class="field-hint">输入完整的 CSS 渐变值，如 linear-gradient(135deg, #667eea, #764ba2)</div>
      </div>

      <div v-if="themeConfig.bg_type === 'image'" class="theme-row">
        <label class="form-label">背景图片</label>
        <div class="upload-area" @click="bgFileInput.click()" @dragover.prevent @drop.prevent="handleBgDrop">
          <input ref="bgFileInput" type="file" accept="image/*" style="display:none" @change="handleBgUpload" />
          <div v-if="!themeConfig.bg_value" class="upload-placeholder">
            <div style="font-size: 36px; margin-bottom: 8px;">📁</div>
            <div>点击或拖拽上传背景图片</div>
            <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">支持 JPG / PNG / WebP，建议 1920x1080 以上</div>
          </div>
          <div v-else class="upload-preview">
            <img :src="themeConfig.bg_value" alt="背景预览" />
            <button class="remove-bg-btn" @click.stop="themeConfig.bg_value = ''">移除图片</button>
          </div>
        </div>
        <div v-if="bgUploading" style="color: #f59e0b; font-size: 13px; margin-top: 8px;">上传中...</div>

        <div class="theme-row" style="margin-top: 16px;">
          <label class="form-label">背景透明度: {{ Math.round((themeConfig.bg_opacity ?? 1) * 100) }}%</label>
          <input type="range" min="0.1" max="1" step="0.05" v-model.number="themeConfig.bg_opacity" class="opacity-slider" />
        </div>

        <div class="theme-row">
          <label class="form-label">缩放模式</label>
          <div class="bg-type-group">
            <button :class="{ active: themeConfig.bg_size === 'cover' }" @click="themeConfig.bg_size = 'cover'">铺满 (Cover)</button>
            <button :class="{ active: themeConfig.bg_size === 'contain' }" @click="themeConfig.bg_size = 'contain'">适应 (Contain)</button>
            <button :class="{ active: themeConfig.bg_size === 'auto' }" @click="themeConfig.bg_size = 'auto'">平铺 (Tile)</button>
          </div>
        </div>
      </div>

      <div class="theme-preview" :style="previewStyle">
        <div class="preview-label">预览效果</div>
        <div v-if="themeConfig.bg_type === 'image' && themeConfig.bg_value" class="preview-thumbnail">
          <img :src="themeConfig.bg_value" alt="背景缩略图" />
        </div>
        <div class="preview-card" :style="{ borderColor: themeConfig.primary_color }">
          <div class="preview-header" :style="{ background: themeConfig.primary_color }">标题栏</div>
          <div class="preview-body">内容区域示例文本</div>
        </div>
      </div>

      <button @click="saveTheme" class="btn-primary" style="margin-top: 20px;">保存主题配置</button>
      <button @click="resetTheme" class="btn-secondary" style="margin-top: 20px; margin-left: 10px;">恢复默认主题</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const props = defineProps({
  adminUsername: { type: String, required: true }
})

const themeConfig = ref({ primary_color: '#3b82f6', bg_type: 'color', bg_value: '#f1f5f9', bg_opacity: 1, bg_size: 'cover' })
const bgUploading = ref(false)
const bgFileInput = ref(null)

const previewStyle = computed(() => {
  const t = themeConfig.value
  if (t.bg_type === 'image' && t.bg_value) {
    return {
      backgroundImage: `url(${t.bg_value})`,
      backgroundSize: t.bg_size || 'cover',
      backgroundPosition: 'center',
      backgroundRepeat: t.bg_size === 'auto' ? 'repeat' : 'no-repeat',
      opacity: t.bg_opacity ?? 1
    }
  } else if (t.bg_type === 'gradient' && t.bg_value) {
    return { backgroundImage: t.bg_value }
  }
  return { backgroundColor: t.bg_value || '#f1f5f9' }
})

const loadTheme = async () => {
  try {
    const res = await fetch(`/api/admin/theme?admin_username=${props.adminUsername}`)
    if (res.ok) {
      const data = await res.json()
      themeConfig.value = { primary_color: '#3b82f6', bg_type: 'color', bg_value: '#f1f5f9', bg_opacity: 1, bg_size: 'cover', ...data }
    }
  } catch (e) { /* ignore */ }
}
const saveTheme = async () => {
  const res = await fetch('/api/admin/theme', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ admin_username: props.adminUsername, ...themeConfig.value })
  })
  if (res.ok) alert('主题保存成功，刷新用户页面即可生效')
  else alert('保存失败')
}

const resetTheme = async () => {
  if (!confirm('确认恢复为默认主题？将清除所有自定义设置。')) return
  themeConfig.value = { primary_color: '#3b82f6', bg_type: 'color', bg_value: '#f1f5f9', bg_opacity: 1, bg_size: 'cover' }
  await saveTheme()
}

const handleBgUpload = async (event) => {
  const file = event.target.files[0]
  if (!file) return
  await uploadBgFile(file)
  event.target.value = ''
}

const handleBgDrop = async (event) => {
  const file = event.dataTransfer.files[0]
  if (file && file.type.startsWith('image/')) await uploadBgFile(file)
}

const uploadBgFile = async (file) => {
  bgUploading.value = true
  try {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('admin_username', props.adminUsername)
    const res = await fetch('/api/admin/theme/upload', { method: 'POST', body: formData })
    if (res.ok) {
      const data = await res.json()
      themeConfig.value.bg_value = data.url
    } else {
      alert('上传失败')
    }
  } catch (e) {
    alert('上传出错: ' + e.message)
  } finally {
    bgUploading.value = false
  }
}

onMounted(() => { loadTheme() })
</script>

<style scoped>
.btn-sm { padding: 6px 12px; font-size: 12px; border: 1px solid #e2e8f0; background: white; border-radius: 6px; cursor: pointer; color: #64748b; transition: all 0.2s; }
.btn-sm:hover { background: #f1f5f9; }
.color-picker { width: 40px; height: 36px; border: none; border-radius: 6px; cursor: pointer; padding: 0; }
.color-input { width: 100px; padding: 8px; border: 1px solid #e2e8f0; border-radius: 6px; font-family: monospace; }
.theme-form { max-width: 600px; }
.theme-row { margin-bottom: 24px; }
.bg-type-group { display: flex; gap: 4px; background: #f1f5f9; border-radius: 8px; padding: 4px; }
.bg-type-group button { padding: 8px 20px; border: none; background: transparent; cursor: pointer; border-radius: 6px; font-size: 13px; color: #64748b; transition: all 0.2s; }
.bg-type-group button.active { background: white; color: #3498db; box-shadow: 0 1px 4px rgba(0,0,0,0.1); }
.upload-area { border: 2px dashed #d1d5db; border-radius: 12px; padding: 30px; text-align: center; cursor: pointer; transition: all 0.2s; min-height: 160px; display: flex; align-items: center; justify-content: center; }
.upload-area:hover { border-color: #3498db; background: #f8faff; }
.upload-placeholder { color: #64748b; font-size: 14px; }
.upload-preview { position: relative; width: 100%; }
.upload-preview img { max-width: 100%; max-height: 200px; border-radius: 8px; object-fit: cover; }
.remove-bg-btn { position: absolute; top: 8px; right: 8px; background: rgba(239,68,68,0.9); color: white; border: none; padding: 4px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; }
.theme-preview { margin-top: 24px; padding: 24px; border-radius: 12px; border: 1px solid #e2e8f0; min-height: 160px; position: relative; display: flex; align-items: flex-start; gap: 20px; }
.preview-label { position: absolute; top: -10px; left: 12px; background: white; padding: 0 8px; font-size: 12px; color: #94a3b8; }
.preview-thumbnail { width: 160px; height: 100px; border-radius: 8px; overflow: hidden; border: 1px solid #e2e8f0; flex-shrink: 0; }
.preview-thumbnail img { width: 100%; height: 100%; object-fit: cover; }
.preview-card { border: 2px solid; border-radius: 8px; overflow: hidden; max-width: 300px; }
.preview-header { color: white; padding: 10px 16px; font-size: 14px; font-weight: 500; }
.preview-body { padding: 16px; font-size: 13px; color: #475569; background: white; }
.opacity-slider { width: 100%; height: 6px; -webkit-appearance: none; appearance: none; background: linear-gradient(90deg, #e2e8f0, #3498db); border-radius: 3px; outline: none; cursor: pointer; }
.opacity-slider::-webkit-slider-thumb { -webkit-appearance: none; width: 18px; height: 18px; border-radius: 50%; background: white; border: 2px solid #3498db; cursor: pointer; box-shadow: 0 1px 4px rgba(0,0,0,0.15); }
</style>
