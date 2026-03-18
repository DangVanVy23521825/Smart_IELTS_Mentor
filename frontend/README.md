# Smart IELTS Mentor Frontend (React + Vite)

Frontend MVP for the Writing Task 2 flow:

1. Register / login
2. Submit writing essay
3. Poll job status
4. View assessment result
5. Send feedback

## 1) Setup

```bash
cd frontend
cp .env.example .env
npm install
```

Environment variables:

- `VITE_API_BASE_URL` (default: `http://localhost:8000`)
- `VITE_API_PREFIX` (default: `/api/v1`)

## 2) Run

```bash
npm run dev
```

## 3) Quality checks

```bash
npm run lint
npm run test
npm run build
```

## 4) Manual E2E checklist

- Register and login successfully
- Submit writing and receive `submission_id` + `job_id`
- Job status transitions `queued/running` -> `succeeded` or `failed`
- Submission result page renders overall band, criteria, errors, study plan
- Feedback submit returns success
- Error handling verified for 401/404/409/422/429/503

## 5) Key folders

- `src/app`: app shell, router, providers
- `src/features/auth`: auth UI and auth context
- `src/features/writing`: submit + result pages
- `src/features/jobs`: polling state + job page
- `src/features/feedback`: feedback form
- `src/shared/api`: HTTP client, API wrappers, error normalization
- `src/shared/auth`: token storage
- `src/shared/types`: typed API contracts
- `src/test`: test setup
# React + TypeScript + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...

      // Remove tseslint.configs.recommended and replace with this
      tseslint.configs.recommendedTypeChecked,
      // Alternatively, use this for stricter rules
      tseslint.configs.strictTypeChecked,
      // Optionally, add this for stylistic rules
      tseslint.configs.stylisticTypeChecked,

      // Other configs...
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```
