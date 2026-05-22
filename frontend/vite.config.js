import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In production builds, VITE_API_URL points the frontend at the deployed
// backend directly (e.g. on Railway), so no dev proxy is needed. In local
// dev (no VITE_API_URL set), the fetch paths are relative — proxy them to
// the local backend at http://localhost:8000 (overridable for docker).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: '0.0.0.0',
    proxy: process.env.VITE_API_URL
      ? undefined
      : {
          '/trace': process.env.VITE_API_TARGET || 'http://localhost:8000',
          '/history': process.env.VITE_API_TARGET || 'http://localhost:8000',
          '/health': process.env.VITE_API_TARGET || 'http://localhost:8000',
        },
  },
})
