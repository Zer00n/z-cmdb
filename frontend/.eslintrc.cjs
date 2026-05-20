module.exports = {
  root: true,
  env: {
    browser: true,
    es2020: true,
    node: true,
  },
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:vue/vue3-recommended',
  ],
  parser: 'vue-eslint-parser',
  parserOptions: {
    parser: '@typescript-eslint/parser',
    ecmaVersion: 2020,
    sourceType: 'module',
  },
  plugins: ['@typescript-eslint'],
  rules: {
    // 允许 any（特殊场景需注释说明）
    '@typescript-eslint/no-explicit-any': 'warn',
    // Vue 组件名称多词
    'vue/multi-word-component-names': 'off',
    // 禁止 console（提交前清理）
    'no-console': 'warn',
  },
}
