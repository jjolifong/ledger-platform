import { useEffect, useState } from 'react'
import { useAuth } from './contexts/AuthContext'
import LoginPage from './pages/LoginPage'
import LedgerPage from './pages/LedgerPage'
import AdminPage from './pages/AdminPage'
import './App.css'

function usePathname() {
  const [pathname, setPathname] = useState(window.location.pathname)

  useEffect(() => {
    const onChange = () => setPathname(window.location.pathname)
    window.addEventListener('popstate', onChange)
    return () => window.removeEventListener('popstate', onChange)
  }, [])

  return pathname
}

export default function App() {
  const { user, loading } = useAuth()
  const pathname = usePathname()

  if (loading) {
    return (
      <div className="app-loading" role="status">
        세션 확인 중…
      </div>
    )
  }

  if (!user) {
    return <LoginPage />
  }

  if (pathname.startsWith('/admin')) {
    return <AdminPage />
  }

  return <LedgerPage />
}
