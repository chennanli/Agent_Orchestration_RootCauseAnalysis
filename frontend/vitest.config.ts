/**
 * Vitest config for the TEP Live Copilot frontend.
 *
 * Why a separate file (not the `test` block in vite.config.ts):
 *   - vite.config.ts is loaded by `vite dev` and `vite build` too; putting
 *     vitest config in there pulls jsdom + RTL into the production graph,
 *     which Vite then tries to type-check during `npm run build`.
 *   - vitest.config.ts gets picked up only by `vitest`, so test deps stay
 *     dev-only.
 */
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react-swc";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/setupTests.ts"],
    // The tests are colocated under src/**/__tests__/ (matches the
    // convention RTL docs recommend) so they live next to the component
    // they're testing.
    include: ["src/**/__tests__/**/*.{test,spec}.{ts,tsx}"],
    css: false,
  },
});
