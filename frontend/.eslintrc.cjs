/*
 * Minimal ESLint config for the TEP Copilot frontend.
 *
 * Goal: make `npm run lint` actually do something useful without drowning
 * the team in stylistic noise. We lean on TypeScript's own type checker
 * (run via `tsc --noEmit` in `npm run build`) for type errors and ask
 * ESLint only to catch the bugs that the compiler can't see:
 *   - React hook violations (most common foot-gun)
 *   - dead code, unused vars (downgraded to warnings so they don't block)
 *   - Fast-Refresh hostile exports during dev
 *
 * Prettier is kept separate (`npm run format`) and disables stylistic
 * lint rules via eslint-config-prettier.
 */
module.exports = {
  root: true,
  env: { browser: true, es2020: true },
  extends: [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:react-hooks/recommended",
    "prettier",
  ],
  parser: "@typescript-eslint/parser",
  parserOptions: {
    ecmaVersion: "latest",
    sourceType: "module",
  },
  plugins: ["@typescript-eslint", "react-refresh"],
  ignorePatterns: ["dist", "node_modules", ".eslintrc.cjs"],
  rules: {
    "react-refresh/only-export-components": [
      "warn",
      { allowConstantExport: true },
    ],
    // `_underscore` prefix opts out of unused-var noise — matches React/TS
    // convention for intentionally-unused destructured props.
    "@typescript-eslint/no-unused-vars": [
      "warn",
      { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
    ],
    // `any` shows up around EventSource MessageEvent, fetch responses,
    // and recharts/d3 generics. Downgrade rather than refuse-to-lint so
    // CI doesn't break on legitimate use.
    "@typescript-eslint/no-explicit-any": "warn",
    // We deliberately use empty `catch {}` for "ignore failure" branches
    // (e.g. localStorage in privacy modes); annotate-via-comment is enough.
    "no-empty": ["warn", { allowEmptyCatch: true }],
  },
};
