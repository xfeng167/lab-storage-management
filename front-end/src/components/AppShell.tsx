import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { Brand } from './Brand'

function navClass({ isActive }: { isActive: boolean }): string {
  return `rounded-lg px-3 py-2 text-sm font-medium transition ${isActive ? 'bg-lab-50 text-lab-800' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-950'}`
}

export function AppShell() {
  const { user, logout } = useAuth()
  const [isOpen, setIsOpen] = useState(false)
  const isAdmin = user?.role === 'admin'

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-5 py-4 lg:px-8">
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
            <nav className="flex items-center gap-1" aria-label="Account navigation">
              <NavLink to="/account" end className={navClass}>Account</NavLink>
              {isAdmin && <NavLink to="/account/users" className={navClass}>Users</NavLink>}
            </nav>
            <div className="h-7 border-l border-slate-200" />
            <div className="text-right text-xs leading-5 text-slate-500">
              <p className="font-semibold text-slate-700">{user?.username}</p>
              <button type="button" className="font-medium text-teal-700 hover:text-teal-800" onClick={async () => { await logout() }}>Sign out</button>
            </div>
          </div>
        </div>
        {isOpen && (
          <div id="account-navigation" className="border-t border-slate-100 px-5 py-3 md:hidden">
            <nav className="flex flex-col gap-1" aria-label="Mobile account navigation">
              <NavLink to="/account" end className={navClass} onClick={() => setIsOpen(false)}>Account</NavLink>
              {isAdmin && <NavLink to="/account/users" className={navClass} onClick={() => setIsOpen(false)}>Users</NavLink>}
              <button type="button" className="mt-1 rounded-lg px-3 py-2 text-left text-sm font-medium text-teal-700" onClick={async () => { await logout() }}>Sign out</button>
            </nav>
          </div>
        )}
      </header>
      <main className="mx-auto max-w-6xl px-5 py-10 lg:px-8"><Outlet /></main>
    </div>
  )
}
