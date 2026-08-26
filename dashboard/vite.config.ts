import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Production behind nginx on smsgateway.behzaaad.ir uses /app/.
// Local: leave unset (serves at http://localhost:5173/).
// Deploy: VITE_BASE_PATH=/app/ npm run build
const base = process.env.VITE_BASE_PATH || '/'

export default defineConfig({
  base,
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true,
        changeOrigin: true,
      },
    },
  },
})
