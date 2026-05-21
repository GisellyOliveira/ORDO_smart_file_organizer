// This module uses browser-only APIs (navigator.serviceWorker).
// It must NEVER be imported statically in a Next.js page or layout.
// Always activate via dynamic import inside a typeof window !== 'undefined' guard.
import { setupWorker } from 'msw/browser'
import { handlers } from './handlers'

export const worker = setupWorker(...handlers)
