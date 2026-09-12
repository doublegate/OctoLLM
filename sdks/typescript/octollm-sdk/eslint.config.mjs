// ESLint flat configuration.
//
// Replaces the legacy .eslintrc.js. ESLint 9 dropped .eslintrc support by default, so
// `npm run lint` had been failing outright with "couldn't find eslint.config.(js|mjs|cjs)";
// ESLint 10 removes the legacy format entirely.
//
// Rule selection is carried over from the old .eslintrc.js unchanged.

import eslint from '@eslint/js';
import tseslint from 'typescript-eslint';
import globals from 'globals';

export default tseslint.config(
  {
    ignores: ['dist/**', 'node_modules/**', 'coverage/**']
  },
  eslint.configs.recommended,
  ...tseslint.configs.recommended,
  {
    languageOptions: {
      ecmaVersion: 2020,
      sourceType: 'module',
      globals: {
        ...globals.node,
        ...globals.es2020,
        ...globals.jest
      }
    },
    rules: {
      '@typescript-eslint/no-explicit-any': 'warn',
      '@typescript-eslint/explicit-function-return-type': 'off',
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }]
    }
  }
);
