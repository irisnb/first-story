import path from 'node:path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

/**
 * Manual chunks configuration for code splitting.
 * Groups heavy dependencies into separate vendor chunks.
 */
function manualChunks(id: string) {
  if (!id.includes('node_modules')) return

  // React core - always needed
  if (id.includes('react-dom') || id.includes('/react/')) {
    return 'react-vendor'
  }

  // Chat UI framework - only needed for chat feature
  if (id.includes('@assistant-ui')) {
    return 'chat-vendor'
  }

  // Code editor - only needed for manuscript feature
  if (
    id.includes('@uiw/react-codemirror') ||
    id.includes('@codemirror') ||
    id.includes('fountain-js')
  ) {
    return 'editor-vendor'
  }

  // Graph/Canvas - only needed for modules feature (future)
  if (
    id.includes('@xyflow/react') ||
    id.includes('d3-dag') ||
    id.includes('dagre') ||
    id.includes('graphology') ||
    id.includes('/sigma/')
  ) {
    return 'graph-vendor'
  }

  // Diff viewer - only needed for version comparison
  if (id.includes('react-diff-viewer-continued') || id.includes('/diff/')) {
    return 'diff-vendor'
  }

  // State management - core
  if (id.includes('@tanstack/react-query') || id.includes('zustand')) {
    return 'state-vendor'
  }

  // UI components - Radix, Lucide icons
  if (id.includes('@radix-ui') || id.includes('lucide-react')) {
    return 'ui-vendor'
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks,
      },
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
