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

export const materialUnitOptions = [
  { value: 'vial', label: 'Vial / vials' },
  { value: 'bottle', label: 'Bottle / bottles' },
  { value: 'tube', label: 'Tube / tubes' },
  { value: 'ampule', label: 'Ampule / ampules' },
  { value: 'bag', label: 'Bag / bags' },
  { value: 'box', label: 'Box / boxes' },
  { value: 'container', label: 'Container / containers' },
  { value: 'plate', label: 'Plate / plates' },
  { value: 'well', label: 'Well / wells' },
  { value: 'aliquot', label: 'Aliquot / aliquots' },
  { value: 'capsule', label: 'Capsule / capsules' },
  { value: 'tablet', label: 'Tablet / tablets' },
  { value: 'dose', label: 'Dose / doses' },
  { value: 'each', label: 'Each' },
  { value: 'µg', label: 'Microgram (µg)' },
  { value: 'mg', label: 'Milligram (mg)' },
  { value: 'g', label: 'Gram (g)' },
  { value: 'kg', label: 'Kilogram (kg)' },
  { value: 'µL', label: 'Microliter (µL)' },
  { value: 'mL', label: 'Milliliter (mL)' },
  { value: 'L', label: 'Liter (L)' },
] as const

const countedUnitForms = new Map<string, string>([
  ['vial', 'vials'],
  ['bottle', 'bottles'],
  ['tube', 'tubes'],
  ['ampule', 'ampules'],
  ['bag', 'bags'],
  ['box', 'boxes'],
  ['container', 'containers'],
  ['plate', 'plates'],
  ['well', 'wells'],
  ['aliquot', 'aliquots'],
  ['capsule', 'capsules'],
  ['tablet', 'tablets'],
  ['dose', 'doses'],
])
const unitAliases = new Map<string, string>()

function unitKey(unit: string): string {
  return unit.trim().toLocaleLowerCase().replace('μ', 'µ')
}

for (const [singular, plural] of countedUnitForms) {
  unitAliases.set(unitKey(singular), singular)
  unitAliases.set(unitKey(plural), singular)
}

for (const unit of ['each', 'µg', 'mg', 'g', 'kg', 'µL', 'mL', 'L']) {
  unitAliases.set(unitKey(unit), unit)
}
unitAliases.set('ug', 'µg')
unitAliases.set('mcg', 'µg')
unitAliases.set('ul', 'µL')

export function normalizeMaterialUnit(unit: string): string {
  const trimmed = unit.trim()
  return unitAliases.get(unitKey(trimmed)) ?? trimmed
}

export function isStandardMaterialUnit(unit: string): boolean {
  const normalized = normalizeMaterialUnit(unit)
  return materialUnitOptions.some((option) => option.value === normalized)
}

export function quantityLabel(quantity: number, unit: string): string {
  const normalizedUnit = normalizeMaterialUnit(unit)
  const plural = countedUnitForms.get(normalizedUnit)
  return `${quantity.toLocaleString()} ${quantity === 1 || !plural ? normalizedUnit : plural}`
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
