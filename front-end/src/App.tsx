import { Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import { AccountPage } from './pages/AccountPage'
import { AuthLayout } from './pages/AuthLayout'
import { LoginPage } from './pages/LoginPage'
import { RegisterPage } from './pages/RegisterPage'
import { UsersPage } from './pages/UsersPage'
import { AdminRoute, ProtectedRoute, PublicOnlyRoute } from './routes/RouteGuards'

export function App() {
  return (
    <Routes>
      <Route element={<PublicOnlyRoute />}>
        <Route element={<AuthLayout />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
        </Route>
      </Route>
      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route path="/account" element={<AccountPage />} />
          <Route element={<AdminRoute />}>
            <Route path="/account/users" element={<UsersPage />} />
          </Route>
        </Route>
      </Route>
      <Route path="/" element={<Navigate to="/account" replace />} />
      <Route path="*" element={<Navigate to="/account" replace />} />
    </Routes>
  )
}
