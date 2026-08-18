interface PaginationControlsProps {
  page: number
  pages: number
  total: number
  label: string
  onPageChange: (page: number) => void
}

export function PaginationControls({ page, pages, total, label, onPageChange }: PaginationControlsProps) {
  if (pages <= 1) return total ? <p className="border-t border-slate-100 px-6 py-4 text-sm text-slate-500">{total} {label}</p> : null
  return (
    <nav className="flex items-center justify-between gap-4 border-t border-slate-100 px-6 py-4" aria-label={`${label} pagination`}>
      <p className="text-sm text-slate-500">Page {page} of {pages} · {total} {label}</p>
      <div className="flex gap-2">
        <button type="button" className="button-secondary" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>Previous</button>
        <button type="button" className="button-secondary" disabled={page >= pages} onClick={() => onPageChange(page + 1)}>Next</button>
      </div>
    </nav>
  )
}
