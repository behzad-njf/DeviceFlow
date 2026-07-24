import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@fontsource/vazirmatn/400.css'
import '@fontsource/vazirmatn/500.css'
import '@fontsource/vazirmatn/600.css'
import '@fontsource/vazirmatn/700.css'
import './shared/i18n'
import './styles/tokens.css'
import './styles/app.css'
import { AppRouter } from './app/AppRouter'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AppRouter />
  </StrictMode>,
)
