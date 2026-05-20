import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  css: {
    preprocessorOptions: {
      scss: {
        // Element Plus 主题覆盖入口
        // 排除 element-theme.scss 自身以避免循环引用
        additionalData: (source: string, filename: string) => {
          if (filename.includes('element-theme.scss')) return source
          return `@use "@/styles/element-theme.scss" as *;\n${source}`
        },
      },
    },
  },
})
