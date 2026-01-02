import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue()
  ],
  // Configure for static file serving
  base: './', // Use relative paths for Electron
  build: {
    assetsDir: 'assets', // Keep assets in assets folder
    rollupOptions: {
      output: {
        // Ensure consistent file naming
        assetFileNames: 'assets/[name]-[hash][extname]',
        chunkFileNames: 'assets/[name]-[hash].js',
        entryFileNames: 'assets/[name]-[hash].js',
      },
    },
  },
  server: {
    host: '127.0.0.1',
    port: 8080,
  },
  // Preview server configuration (for npm run preview)
  preview: {
    host: '127.0.0.1',
    port: 8081, // Different port for preview
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
})
