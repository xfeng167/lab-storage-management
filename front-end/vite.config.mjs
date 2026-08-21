import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
  preview: {
    allowedHosts: [
      'lab-storage-management-production.up.railway.app',
      'healthcheck.railway.app',
    ],
  },
  test: {
    environment: 'jsdom',
    threads: false,
    globals: true,
    setupFiles: './src/test/setup.ts',
    css: true,
  },
})
