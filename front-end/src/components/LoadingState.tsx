export function LoadingState({ label = 'Loading your workspace…' }: { label?: string }) {
  return (
    <div className="grid min-h-[240px] place-items-center" role="status" aria-live="polite">
      <div className="flex items-center gap-3 text-sm font-medium text-slate-600">
        <span className="h-5 w-5 animate-spin rounded-full border-2 border-slate-200 border-t-teal-600" aria-hidden="true" />
        {label}
      </div>
    </div>
  )
}
