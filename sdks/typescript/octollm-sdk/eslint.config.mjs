// ESLint flat configuration.
//
// Replaces the legacy .eslintrc.js. ESLint 9 dropped .eslintrc support by default, so
// `npm run lint` had been failing outright with "couldn't find eslint.config.(js|mjs|cjs)";
// ESLint 10 removes the legacy format entirely.
//
// Uses @babel/eslint-parser + @babel/preset-typescript so ESLint 10 can parse TypeScript
// without @typescript-eslint/*'s <6.1.0 peer constraint against TypeScript 7.0 (`tsgo`).

import eslint from '@eslint/js';
import babelParser from '@babel/eslint-parser';
import globals from 'globals';

export default [
  {
    ignores: ['dist/**', 'node_modules/**', 'coverage/**']
  },
  eslint.configs.recommended,
  {
    languageOptions: {
      ecmaVersion: 2020,
      sourceType: 'module',
      globals: {
        ...globals.node,
        ...globals.es2020,
        ...globals.jest
      }
    }
  },
  {
    files: ['**/*.ts'],
    languageOptions: {
      parser: babelParser,
      parserOptions: {
        requireConfigFile: false,
        babelOptions: {
          presets: ['@babel/preset-typescript']
        }
      }
    },
    rules: {
      'no-undef': 'off',
      'no-unused-vars': 'off'
    }
  }
];
