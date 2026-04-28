import { createApp } from 'vue'
import { createPinia } from 'pinia'
import AdminApp from './AdminApp.vue'
import './assets/style.css'
import './assets/admin-shared.css'

const app = createApp(AdminApp)
app.use(createPinia())
app.mount('#app')
