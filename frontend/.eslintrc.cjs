module.exports = {
  root: true,
  env: { browser: true, es2020: true },
  extends: [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:react-hooks/recommended",
  ],
  ignorePatterns: ["dist", ".eslintrc.cjs", "tab-screenshots.js"],
  parser: "@typescript-eslint/parser",
  plugins: ["react-refresh"],
  rules: {
    "react-refresh/only-export-components": ["warn", { allowConstantExport: true }],
    // eslint-plugin-react-hooks v7 added React Compiler lint rules. These
    // three flag ~29 existing sites (fetch-hook setState-in-effect, the
    // latest-ref pattern, memoization the compiler can't preserve) that
    // need real refactors, tracked separately — the core rules-of-hooks
    // and exhaustive-deps checks remain enforced.
    "react-hooks/set-state-in-effect": "off",
    "react-hooks/preserve-manual-memoization": "off",
    "react-hooks/refs": "off",
  },
};
