import nextCoreWebVitals from 'eslint-config-next/core-web-vitals'
import nextTypescript from 'eslint-config-next/typescript'
import eslintConfigPrettier from 'eslint-config-prettier'

const config = [
  ...nextCoreWebVitals,
  ...nextTypescript,
  eslintConfigPrettier,
  {
    settings: {
      react: { version: '18' },
    },
    rules: {
      'react-hooks/exhaustive-deps': 'error',
    },
  },
]

export default config
