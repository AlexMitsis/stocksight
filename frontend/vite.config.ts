import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    host: true, // Listen on all addresses (needed for Docker)
    // The repo lives on the Windows filesystem (/mnt/c), where file-change events don't fire
    // in WSL or in Docker bind mounts, so poll for changes instead.
    watch: { usePolling: true, interval: 300 },
    proxy: {
      '/api': {
        target: process.env.VITE_API_PROXY_TARGET || 'http://localhost:8888',
        changeOrigin: true
      }
    }
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'json'],
      exclude: [
        'node_modules/',
        'src/test/',
        '**/*.config.{js,ts}',
        '**/main.tsx'
      ],
      // Set just below current coverage so it can't silently drop; raise as tests are added
      thresholds: {
        lines: 15,
        functions: 10,
        branches: 3,
        statements: 15
      }
    }
  }
})
