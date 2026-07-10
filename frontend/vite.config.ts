import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'      // ← 新增

export default defineConfig({
  plugins: [vue()],
  resolve: {                                        // ← 新增resolve配置
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
})