import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev proxy: when VITE_USE_MOCK=false the app calls the real FastAPI backend.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    proxy: {
      '/api': 'http://localhost:8000',
      '/uploads': 'http://localhost:8000',
    },
  },
})
