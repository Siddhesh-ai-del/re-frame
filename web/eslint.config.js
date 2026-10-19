import js from '@eslint/js'
import reactHooks from 'eslint-plugin-react-hooks'
import tseslint from 'typescript-eslint'

export default tseslint.config(
  {
    ignores: [
      'dist',
      'coverage',
      'src/api/schema.d.ts',
      // Vendored third-party sources (stage 6d): not our code — upstream is
      // kept byte-comparable and its minimal adaptations are documented in
      // web/vendored/canvas-ui/NOTICE. Our own wrappers (src/effects/*) are
      // still linted.
      'vendored',
    ],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  ...reactHooks.configs['recommended-latest'],
  {
    // Stage 6e: `public/sw.js` runs in a service-worker global scope, not a
    // browser page and not Node — declare its real globals so `no-undef`
    // checks it against the environment it actually executes in.
    files: ['public/sw.js'],
    languageOptions: {
      globals: {
        self: 'readonly',
        caches: 'readonly',
        fetch: 'readonly',
        Response: 'readonly',
        Request: 'readonly',
        Headers: 'readonly',
        URL: 'readonly',
        console: 'readonly',
      },
    },
  },
)
