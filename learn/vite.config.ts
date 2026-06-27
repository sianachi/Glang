import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// React 19 + Tailwind v4 (via the first-party Vite plugin).
//
// Dev proxy: the SPA calls same-origin paths (/api/run, /lsp). In dev those are
// forwarded to the local GLang services; in production nginx does the same. Set
// RUN_TARGET / LSP_TARGET to point at running services (defaults below).
const RUN_TARGET = process.env.RUN_TARGET ?? 'http://localhost:8081'
const LSP_TARGET = process.env.LSP_TARGET ?? 'ws://localhost:8082'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    open: true,
    proxy: {
      '/api': { target: RUN_TARGET, changeOrigin: true },
      '/lsp': { target: LSP_TARGET, ws: true, changeOrigin: true },
    },
  },
  // monaco-editor ships many ESM entrypoints; let Vite pre-bundle it.
  optimizeDeps: { include: ['monaco-editor'] },
})
