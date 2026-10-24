import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
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
