import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Docker Desktop on Windows doesn't reliably propagate filesystem change
    // events through the bind mount into the container, so chokidar's default
    // watcher silently never fires and Vite keeps serving stale transforms.
    watch: {
      usePolling: true,
      interval: 300,
    },
  },
})
