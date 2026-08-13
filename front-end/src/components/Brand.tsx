import { Link } from 'react-router-dom'

export function Brand() {
  return (
    <Link to="/account" className="group flex items-center gap-3 rounded-md focus:outline-none focus:ring-2 focus:ring-teal-400">
      <span className="grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-lab-700 to-teal-500 text-lg font-bold text-white shadow-panel" aria-hidden="true">
        L
      </span>
      <span className="leading-tight">
        <span className="block text-sm font-semibold tracking-tight text-slate-950">Lab Storage</span>
        <span className="block text-xs font-medium text-slate-500">Management</span>
      </span>
    </Link>
  )
}
