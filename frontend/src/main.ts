/**
 * Vue app entry point
 * Element Plus full import + all icons globally registered
 */
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'
import i18n from './i18n'

// Style import order: tokens -> element-plus -> element-theme (override) -> app (global utilities)
import '@/styles/tokens.css'
import 'element-plus/dist/index.css'
import '@/styles/element-theme.scss'
import '@/styles/app.css'

const app = createApp(App)

// Globally register all Element Plus icons
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(i18n)
app.use(createPinia())
app.use(router)
app.use(ElementPlus)

app.mount('#app')
