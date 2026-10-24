import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './App.css'
import App from './App.jsx'
import LoginPage from './pages/login-page.jsx'
import DashboardPage from './pages/dashboard.jsx'

const page =
  window.location.pathname === '/login' ? <LoginPage /> :
  window.location.pathname === '/dashboard' ? <DashboardPage /> :
  <App />

createRoot(document.getElementById('root')).render(
  <StrictMode>
    {page}
  </StrictMode>,
)

// Fade out the Check Am splash once the app has drawn (shown for at least 600ms so it doesn't flash)
const splash = document.getElementById('splash')
if (splash) {
  const wait = Math.max(0, 600 - performance.now())
  window.setTimeout(() => {
    splash.classList.add('hide')
    window.setTimeout(() => splash.remove(), 400)
  }, wait)
}
