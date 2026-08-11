import { humanize } from '../utils/format'

interface StatusBadgeProps {
  value: string
  kind?: 'order' | 'qc' | 'availability' | 'role'
}

const styles: Record<string, string> = {
  submitted: 'bg-amber-50 text-amber-800 ring-amber-200',
  approved: 'bg-sky-50 text-sky-800 ring-sky-200',
  fulfilled: 'bg-emerald-50 text-emerald-800 ring-emerald-200',
  rejected: 'bg-rose-50 text-rose-800 ring-rose-200',
  canceled: 'bg-slate-100 text-slate-700 ring-slate-200',
  archived: 'bg-zinc-100 text-zinc-700 ring-zinc-200',
  passed: 'bg-emerald-50 text-emerald-800 ring-emerald-200',
  pending: 'bg-amber-50 text-amber-800 ring-amber-200',
  failed: 'bg-rose-50 text-rose-800 ring-rose-200',
  available: 'bg-emerald-50 text-emerald-800 ring-emerald-200',
  viewer: 'bg-slate-100 text-slate-700 ring-slate-200',
  staff: 'bg-sky-50 text-sky-800 ring-sky-200',
  admin: 'bg-violet-50 text-violet-800 ring-violet-200',
}

export function StatusBadge({ value }: StatusBadgeProps) {
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${styles[value.toLowerCase()] ?? 'bg-slate-100 text-slate-700 ring-slate-200'}`}>{humanize(value)}</span>
}
