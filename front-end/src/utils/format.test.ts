import { describe, expect, it } from 'vitest'
import { formatAuditChange, quantityLabel } from './format'

describe('quantityLabel', () => {
  it.each([
    [0, 'vials', '0 vials'],
    [1, 'vials', '1 vial'],
    [2, 'vials', '2 vials'],
    [1, 'vial', '1 vial'],
    [2, 'vial', '2 vials'],
    [1, 'box', '1 box'],
    [2, 'box', '2 boxes'],
    [1, 'mL', '1 mL'],
    [2, 'mL', '2 mL'],
  ])('formats %s %s as %s', (quantity, unit, expected) => {
    expect(quantityLabel(quantity, unit)).toBe(expected)
  })
})

describe('formatAuditChange', () => {
  it('renders quantity audit JSON as labeled changes', () => {
    expect(formatAuditChange(
      '{"quantity_available":3,"quantity_reserved":2}',
      '{"quantity_available":1,"quantity_reserved":0}',
    )).toBe('Available: 3 → 1 · Reserved: 2 → 0')
  })

  it('preserves non-JSON values', () => {
    expect(formatAuditChange('Shelf A', 'Shelf B')).toBe('Shelf A → Shelf B')
  })
})
