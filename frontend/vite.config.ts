import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// /api and /preview proxy to FastAPI — no CORS in dev, SSE streams pass through.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/preview': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
