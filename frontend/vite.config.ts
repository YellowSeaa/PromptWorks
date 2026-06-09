import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  build: {
    chunkSizeWarningLimit: 800,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return

          const normalizedId = id.replaceAll('\\', '/')
          if (
            normalizedId.includes('/node_modules/vue/') ||
            normalizedId.includes('/node_modules/vue-router/') ||
            normalizedId.includes('/node_modules/vue-i18n/')
          ) {
            return 'vendor-vue'
          }

          if (normalizedId.includes('/node_modules/@element-plus/icons-vue/')) {
            return 'vendor-element-plus-icons'
          }

          if (normalizedId.includes('/node_modules/element-plus/')) {
            return 'vendor-element-plus'
          }

          if (normalizedId.includes('/node_modules/element-plus-x/')) {
            return 'vendor-element-plus-x'
          }

          if (normalizedId.includes('/node_modules/echarts/')) {
            return 'vendor-echarts'
          }

          if (
            normalizedId.includes('/node_modules/markdown-it/') ||
            normalizedId.includes('/node_modules/diff/')
          ) {
            return 'vendor-text'
          }

          return 'vendor'
        }
      }
    }
  },
  server: {
    host: true,
    port: 5173
  }
})
