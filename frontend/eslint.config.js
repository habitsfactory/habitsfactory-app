import js from '@eslint/js'
import vue from 'eslint-plugin-vue'
import globals from 'globals'

export default [
  { ignores: ['dist/**', 'dev-dist/**', 'node_modules/**'] },

  js.configs.recommended,
  ...vue.configs['flat/recommended'],

  {
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: { ...globals.browser },
    },
    rules: {
      // `catch (err) {}` blocks that deliberately ignore the error are fine
      // …and so are `_`-prefixed variables (used to drop a key when destructuring)
      'no-unused-vars': ['error', { caughtErrors: 'none', varsIgnorePattern: '^_' }],

      // Formatting is left to the editor: only correctness rules are enforced
      'vue/html-indent': 'off',
      'vue/max-attributes-per-line': 'off',
      'vue/first-attribute-linebreak': 'off',
      'vue/html-closing-bracket-newline': 'off',
      'vue/html-self-closing': 'off',
      'vue/singleline-html-element-content-newline': 'off',
      'vue/multiline-html-element-content-newline': 'off',
      'vue/multi-word-component-names': 'off',
    },
  },

  // Build / tooling files run in Node
  {
    files: ['*.config.js'],
    languageOptions: { globals: { ...globals.node } },
  },
]
