import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import { registerServiceWorker } from './pwa/registerSW'
import './styles/index.css'

const rootElement = document.getElementById('root')
if (!rootElement) {
  throw new Error('Root element #root is missing from index.html')
}

// PWA (stage 6e): no-op outside production builds and in unsupported
// browsers; never throws (see src/pwa/registerSW.ts).
registerServiceWorker()

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
