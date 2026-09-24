import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

// 1. 从 element-plus 完整引入组件和样式
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
// --- 【修改点 1】导入 Element Plus 的中文语言包 ---
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'

import App from './App.vue'
import router from './router'

const app = createApp(App)

app.use(createPinia())
app.use(router)

// --- 【修改点 2】在挂载 Element Plus 的同时，配置使用中文语言包 ---
app.use(ElementPlus, { locale: zhCn })

app.mount('#app')