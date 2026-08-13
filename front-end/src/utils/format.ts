export function formatDate(value: string | null | undefined, options: Intl.DateTimeFormatOptions = {}): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    ...options,
  }).format(date)
}

export function formatRole(role: string): string {
  return role.charAt(0).toUpperCase() + role.slice(1)
}

export function humanize(value: string | null | undefined): string {
  if (!value) return '—'
  return value.replace(/[_-]/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}

export function quantityLabel(quantity: number, unit: string): string {
  return `${quantity.toLocaleString()} ${unit}`
}
