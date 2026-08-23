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
  return `${quantity.toLocaleString()} ${quantity === 1 ? singularizeUnit(unit) : unit}`
}

function singularizeUnit(unit: string): string {
  if (unit.endsWith('ies')) return `${unit.slice(0, -3)}y`
  if (unit.endsWith('s') && !unit.endsWith('ss')) return unit.slice(0, -1)
  return unit
}

type AuditValue = string | number | boolean | null
type AuditRecord = Record<string, AuditValue>

const auditFieldLabels: Record<string, string> = {
  quantity_available: 'Available',
  quantity_reserved: 'Reserved',
}

function parseAuditRecord(value: string): AuditRecord | null {
  try {
    const parsed: unknown = JSON.parse(value)
    if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') return null
    if (!Object.values(parsed).every((field) => field === null || ['string', 'number', 'boolean'].includes(typeof field))) return null
    return parsed as AuditRecord
  } catch {
    return null
  }
}

function auditFieldLabel(field: string): string {
  return auditFieldLabels[field] ?? humanize(field)
}

function auditValueLabel(value: AuditValue | undefined): string {
  if (value === null || value === undefined) return '—'
  return String(value)
}

export function formatAuditChange(beforeValue: string, afterValue: string): string {
  const before = parseAuditRecord(beforeValue)
  const after = parseAuditRecord(afterValue)
  if (!before || !after) return `${beforeValue} → ${afterValue}`

  const fields = [...new Set([...Object.keys(before), ...Object.keys(after)])]
  return fields.map((field) => `${auditFieldLabel(field)}: ${auditValueLabel(before[field])} → ${auditValueLabel(after[field])}`).join(' · ')
}
