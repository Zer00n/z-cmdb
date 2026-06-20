/**
 * Vue 应用入口
 * Element Plus 全量引入 + 全部图标全局注册
 */
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'
import i18n from './i18n'

// 样式引入顺序：token → element-plus → element-theme（覆盖）→ app（全局工具类）
import '@/styles/tokens.css'
import 'element-plus/dist/index.css'
import '@/styles/element-theme.scss'
import '@/styles/app.css'

const app = createApp(App)

// 全局注册所有 Element Plus 图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(i18n)
app.use(createPinia())
app.use(router)
app.use(ElementPlus)

app.mount('#app')
