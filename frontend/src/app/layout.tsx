import { Link, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../features/auth/use-auth'
import { RequestIdPanel } from '../shared/debug/request-id-panel'

export function AppLayout() {
  const { isAuthenticated, logout } = useAuth()
  const navigate = useNavigate()

  const onLogout = async () => {
    await logout()
    navigate('/login')
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">Smart IELTS Mentor</div>
        {isAuthenticated && (
          <nav className="topbar-nav">
            <Link to="/writing/new">Writing</Link>
          </nav>
        )}
        {isAuthenticated ? (
          <button type="button" onClick={onLogout}>
            Logout
          </button>
        ) : null}
      </header>
      <main className="page-container">
        <Outlet />
      </main>
      <RequestIdPanel />
    </div>
  )
}
