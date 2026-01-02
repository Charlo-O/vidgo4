import { defineConfig } from 'vite'
import electron from 'vite-plugin-electron'

// Configuration for electron main process build
export default defineConfig({
  plugins: [
    electron({
      entry: 'electron/main.ts',
      vite: {
        build: {
          outDir: 'dist-electron',
          // Build for Node.js environment, not browser
          target: 'node18',
        },
      },
    })
  ],
  // Build for Node.js environment
  resolve: {
    // Don't externalize Node.js core modules
    alias: {
      // Map Node.js core modules to their actual implementations
      'url': 'node:url',
      'path': 'node:path',
    },
  },
  build: {
    // Build for Node.js environment
    ssr: true,
    target: 'node18',
    rollupOptions: {
      // Only build the electron main process
      input: 'electron/main.ts',
      // Don't externalize Node.js core modules
      external: [
        // Externalize electron itself
        'electron',
      ],
    },
  },
})