import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0', // Allow external connections (Safari compatible)
    port: 5173,
    open: false,  // The START_TEP_COPILOT.command launcher opens the right URL itself; Vite must not also open a tab.
    headers: {
      "Cache-Control": "no-store",
    },
    proxy: {
      // -- New Live Copilot routes (Phase 1 backend) --
      // These are mounted under /api/* on the FastAPI backend, so the
      // /api prefix MUST be preserved. Vite matches longest-prefix-first,
      // so these are listed before the legacy /api catch-all below.
      '/api/agent':   { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
      '/api/anomaly': { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
      '/api/sim':     { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },

      // -- Legacy routes --
      // The original /explain backend mounts its endpoints at /foo (no /api
      // prefix). The legacy App.tsx calls them as /api/foo expecting Vite
      // to strip the prefix. Preserve that for backwards compat.
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },

      // -- Bare-path legacy SSE / ingest --
      '/stream':  { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
      '/ingest':  { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
      '/explain': { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
    },
  },
});
