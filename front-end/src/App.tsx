import { Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import { AccountPage } from './pages/AccountPage'
import { AuthLayout } from './pages/AuthLayout'
import { AuditPage } from './pages/AuditPage'
import { DashboardPage } from './pages/DashboardPage'
import { LoginPage } from './pages/LoginPage'
import { LocationsPage } from './pages/LocationsPage'
import { MaterialDetailPage } from './pages/MaterialDetailPage'
import { MaterialsPage } from './pages/MaterialsPage'
import { OrdersPage } from './pages/OrdersPage'
import { RegisterPage } from './pages/RegisterPage'
import { ReportsPage } from './pages/ReportsPage'
import { UsersPage } from './pages/UsersPage'
import { AdminRoute, ProtectedRoute, PublicOnlyRoute, StaffRoute } from './routes/RouteGuards'

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
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/inventory" element={<MaterialsPage />} />
          <Route path="/inventory/:materialId" element={<MaterialDetailPage />} />
          <Route path="/requests" element={<OrdersPage />} />
          <Route path="/account" element={<AccountPage />} />
          <Route element={<StaffRoute />}>
            <Route path="/locations" element={<LocationsPage />} />
            <Route path="/reports" element={<ReportsPage />} />
          </Route>
          <Route element={<AdminRoute />}>
            <Route path="/audit" element={<AuditPage />} />
            <Route path="/account/users" element={<UsersPage />} />
          </Route>
        </Route>
      </Route>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}
