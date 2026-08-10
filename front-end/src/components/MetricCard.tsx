import { Link } from 'react-router-dom'

interface MetricCardProps {
  label: string
  value: string | number
  detail: string
  tone?: 'blue' | 'teal' | 'amber' | 'violet'
  to?: string
}

const toneStyles = {
  blue: 'from-lab-700 to-lab-800 text-white',
  teal: 'from-teal-600 to-emerald-700 text-white',
  amber: 'from-amber-100 to-amber-50 text-amber-950',
  violet: 'from-violet-100 to-violet-50 text-violet-950',
}

export function MetricCard({ label, value, detail, tone = 'blue', to }: MetricCardProps) {
  const className = `block rounded-2xl bg-gradient-to-br p-5 shadow-panel transition ${toneStyles[tone]} ${to ? 'hover:-translate-y-0.5 hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2' : ''}`
  const content = (
    <>
      <p className="text-sm font-medium opacity-80">{label}</p>
      <p className="mt-4 text-3xl font-semibold tracking-tight">{value}</p>
      <p className="mt-2 text-sm opacity-80">{detail}</p>
    </>
  )

  if (to) {
    return (
      <Link className={className} to={to} aria-label={`${label}: ${detail}`}>
        {content}
      </Link>
    )
  }

  return (
    <article className={className}>
      {content}
    </article>
  )
}
