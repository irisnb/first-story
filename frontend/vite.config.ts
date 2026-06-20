import path from 'node:path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    proxy: {
      // 后端 Base http://localhost:8000；开发期走代理避免 CORS 摩擦
      '/api': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
})
