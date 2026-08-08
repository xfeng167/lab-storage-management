interface MetricCardProps {
  label: string
  value: string | number
  detail: string
  tone?: 'blue' | 'teal' | 'amber' | 'violet'
}

const toneStyles = {
  blue: 'from-lab-700 to-lab-800 text-white',
  teal: 'from-teal-600 to-emerald-700 text-white',
  amber: 'from-amber-100 to-amber-50 text-amber-950',
  violet: 'from-violet-100 to-violet-50 text-violet-950',
}

export function MetricCard({ label, value, detail, tone = 'blue' }: MetricCardProps) {
  return (
    <article className={`rounded-2xl bg-gradient-to-br p-5 shadow-panel ${toneStyles[tone]}`}>
      <p className="text-sm font-medium opacity-80">{label}</p>
      <p className="mt-4 text-3xl font-semibold tracking-tight">{value}</p>
      <p className="mt-2 text-sm opacity-80">{detail}</p>
    </article>
  )
}
