import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { Brand } from './Brand'
import { canManageOperations, isAdmin } from '../types'
import { formatRole } from '../utils/format'

function navClass({ isActive }: { isActive: boolean }): string {
  return `rounded-lg px-3 py-2 text-sm font-medium transition ${isActive ? 'bg-lab-50 text-lab-800' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-950'}`
}

function initials(username: string | undefined): string {
  return (username || 'U').slice(0, 2).toUpperCase()
}

export function AppShell() {
  const { user, logout } = useAuth()
  const [isOpen, setIsOpen] = useState(false)
  const navigate = useNavigate()
  const hasOperationsAccess = canManageOperations(user)
  const hasAdminAccess = isAdmin(user)

  async function handleLogout() {
    await logout()
    navigate('/login', { replace: true })
  }

  const navigation = [
    { to: '/dashboard', label: 'Overview', visible: true },
    { to: '/inventory', label: 'Inventory', visible: true },
    { to: '/requests', label: 'Requests', visible: true },
    { to: '/locations', label: 'Locations', visible: hasOperationsAccess },
    { to: '/reports', label: 'Reports', visible: hasOperationsAccess },
    { to: '/audit', label: 'Audit log', visible: hasAdminAccess },
    { to: '/account/users', label: 'Users', visible: hasAdminAccess },
  ]

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-5 py-4 lg:px-8">
          <Brand />
          <button
            type="button"
            className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 md:hidden"
            aria-expanded={isOpen}
            aria-controls="account-navigation"
            onClick={() => setIsOpen((open) => !open)}
          >
            Menu
          </button>
          <div className="hidden items-center gap-4 md:flex">
            <nav className="flex items-center gap-1" aria-label="Primary navigation">
              {navigation.filter((item) => item.visible).map((item) => <NavLink key={item.to} to={item.to} className={navClass}>{item.label}</NavLink>)}
            </nav>
            <div className="h-7 border-l border-slate-200" />
            <div className="flex items-center gap-3">
              <div className="flex min-w-12 flex-col items-center gap-1" role="group" aria-label="Account identity">
                <NavLink to="/account" className="grid h-10 w-10 place-items-center overflow-hidden rounded-xl bg-lab-50 text-sm font-semibold text-lab-800 ring-1 ring-slate-200 transition hover:ring-teal-300" aria-label="Open account profile">
                  {user?.profile_picture ? <img className="h-full w-full object-cover" src={user.profile_picture} alt="" /> : <span>{initials(user?.username)}</span>}
                </NavLink>
                <NavLink to="/account" className="max-w-24 truncate text-xs font-semibold leading-none text-slate-700 hover:text-lab-800">{user?.username}</NavLink>
              </div>
              <div className="text-left text-xs leading-5 text-slate-500">
                <span className="block">{formatRole(user?.role ?? '')}</span>
                <button type="button" className="font-medium text-teal-700 hover:text-teal-800" onClick={handleLogout}>Sign out</button>
              </div>
            </div>
          </div>
        </div>
        {isOpen && (
          <div id="account-navigation" className="border-t border-slate-100 px-5 py-3 md:hidden">
            <nav className="flex flex-col gap-1" aria-label="Mobile navigation">
              {navigation.filter((item) => item.visible).map((item) => <NavLink key={item.to} to={item.to} className={navClass} onClick={() => setIsOpen(false)}>{item.label}</NavLink>)}
              <NavLink to="/account" className={`${navClass({ isActive: false })} flex items-center gap-3`} onClick={() => setIsOpen(false)}>
                <span className="grid h-8 w-8 place-items-center overflow-hidden rounded-lg bg-lab-50 text-xs font-semibold text-lab-800 ring-1 ring-slate-200">
                  {user?.profile_picture ? <img className="h-full w-full object-cover" src={user.profile_picture} alt="" /> : initials(user?.username)}
                </span>
                Account
              </NavLink>
              <button type="button" className="mt-1 rounded-lg px-3 py-2 text-left text-sm font-medium text-teal-700" onClick={handleLogout}>Sign out</button>
            </nav>
          </div>
        )}
      </header>
      <main className="mx-auto max-w-7xl px-5 py-10 lg:px-8"><Outlet /></main>
    </div>
  )
}
