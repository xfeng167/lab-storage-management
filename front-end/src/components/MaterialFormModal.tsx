import { FormEvent, useState } from 'react'
import type { Location, Material, MaterialPayload, MaterialUpdatePayload } from '../types'
import { Modal } from './Modal'

interface MaterialFormModalProps {
  material?: Material
  locations: Location[]
  onClose: () => void
  onSave: (payload: MaterialPayload | MaterialUpdatePayload) => Promise<void>
}

interface MaterialFormState {
  material_code: string
  material_name: string
  material_type: string
  description: string
  source: string
  quantity_available: string
  unit: string
  minimum_quantity: string
  qc_status: string
  storage_condition: string
  location_id: string
}

const pharmaMaterialNameOptions = [
  'Acetaminophen USP',
  'Ibuprofen USP',
  'Metformin Hydrochloride USP',
  'Sodium Chloride USP',
  'Lactose Monohydrate NF',
  'Microcrystalline Cellulose PH 102',
  'Magnesium Stearate NF',
  'Povidone K30',
  'Croscarmellose Sodium NF',
  'Purified Water USP',
  'Ethanol 200 Proof USP',
  'Sodium Hydroxide NF',
  'Hydrochloric Acid NF',
  'Phosphate Buffered Saline',
  'Dimethyl Sulfoxide USP',
]

const quickMaterialNameOptions = pharmaMaterialNameOptions.slice(0, 6)

function createState(material?: Material): MaterialFormState {
  return {
    material_code: material?.material_code ?? '',
    material_name: material?.material_name ?? '',
    material_type: material?.material_type ?? '',
    description: material?.description ?? '',
    source: material?.source ?? '',
    quantity_available: String(material?.quantity_available ?? 0),
    unit: material?.unit ?? '',
    minimum_quantity: String(material?.minimum_quantity ?? 0),
    qc_status: material?.qc_status ?? 'pending',
    storage_condition: material?.storage_condition ?? '',
    location_id: material?.location_id ? String(material.location_id) : '',
  }
}

export function MaterialFormModal({ material, locations, onClose, onSave }: MaterialFormModalProps) {
  const [form, setForm] = useState<MaterialFormState>(() => createState(material))
  const [error, setError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)

  function update(name: keyof MaterialFormState, value: string) {
    setForm((current) => ({ ...current, [name]: value }))
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!form.material_name.trim() || !form.material_type.trim() || !form.unit.trim()) {
      setError('Name, type, and unit are required.')
      return
    }
    if (!material && !form.material_code.trim()) {
      setError('Material code is required when creating a material.')
      return
    }
    if (Number(form.quantity_available) < 0 || Number(form.minimum_quantity) < 0) {
      setError('Quantities cannot be negative.')
      return
    }

    const sharedPayload: MaterialUpdatePayload = {
      material_name: form.material_name.trim(),
      material_type: form.material_type.trim(),
      description: form.description.trim(),
      source: form.source.trim(),
      unit: form.unit.trim(),
      minimum_quantity: Number(form.minimum_quantity),
      qc_status: form.qc_status,
      storage_condition: form.storage_condition.trim(),
      location_id: form.location_id ? Number(form.location_id) : null,
    }
    const payload: MaterialPayload | MaterialUpdatePayload = material
      ? sharedPayload
      : { ...sharedPayload, material_code: form.material_code.trim(), quantity_available: Number(form.quantity_available) } as MaterialPayload

    setIsSaving(true)
    setError(null)
    try {
      await onSave(payload)
      onClose()
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Unable to save material.')
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <Modal title={material ? 'Edit material' : 'Add material'} onClose={onClose} width="wide">
      <form className="space-y-5" onSubmit={submit} noValidate>
        {error && <p className="alert-error" role="alert">{error}</p>}
        <div className="grid gap-5 sm:grid-cols-2">
          <label className="field-label" htmlFor="material-code">Material code
            <input id="material-code" className="field-input" value={form.material_code} disabled={Boolean(material)} onChange={(event) => update('material_code', event.target.value)} />
          </label>
          <label className="field-label" htmlFor="material-name">Material name
            <input id="material-name" className="field-input" list="pharma-material-name-options" placeholder="e.g. Metformin Hydrochloride USP" value={form.material_name} onChange={(event) => update('material_name', event.target.value)} />
            <datalist id="pharma-material-name-options">
              {pharmaMaterialNameOptions.map((name) => <option key={name} value={name} />)}
            </datalist>
            <span className="mt-2 text-xs font-medium text-slate-500">Common pharma names</span>
            <div className="mt-2 flex flex-wrap gap-2">
              {quickMaterialNameOptions.map((name) => (
                <button
                  key={name}
                  type="button"
                  className="rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-left text-xs font-semibold text-slate-700 transition hover:border-teal-300 hover:bg-teal-50 hover:text-teal-800 focus:outline-none focus:ring-2 focus:ring-teal-500"
                  onClick={() => update('material_name', name)}
                >
                  {name}
                </button>
              ))}
            </div>
          </label>
          <label className="field-label" htmlFor="material-type">Material type
            <input id="material-type" className="field-input" placeholder="e.g. API, excipient, reagent, packaging component" value={form.material_type} onChange={(event) => update('material_type', event.target.value)} />
          </label>
          <label className="field-label" htmlFor="material-unit">Unit
            <input id="material-unit" className="field-input" placeholder="e.g. bottles" value={form.unit} onChange={(event) => update('unit', event.target.value)} />
          </label>
          {!material && <label className="field-label" htmlFor="quantity-available">Starting quantity
            <input id="quantity-available" className="field-input" type="number" min="0" value={form.quantity_available} onChange={(event) => update('quantity_available', event.target.value)} />
          </label>}
          <label className="field-label" htmlFor="minimum-quantity">Minimum quantity
            <input id="minimum-quantity" className="field-input" type="number" min="0" value={form.minimum_quantity} onChange={(event) => update('minimum_quantity', event.target.value)} />
          </label>
          <label className="field-label" htmlFor="qc-status">QC status
            <select id="qc-status" className="field-select" value={form.qc_status} onChange={(event) => update('qc_status', event.target.value)}>
              <option value="pending">Pending</option><option value="passed">Passed</option><option value="failed">Failed</option>
            </select>
          </label>
          <label className="field-label" htmlFor="storage-condition">Storage condition
            <input id="storage-condition" className="field-input" placeholder="e.g. -80C" value={form.storage_condition} onChange={(event) => update('storage_condition', event.target.value)} />
          </label>
          <label className="field-label sm:col-span-2" htmlFor="material-location">Location
            <select id="material-location" className="field-select" value={form.location_id} onChange={(event) => update('location_id', event.target.value)}>
              <option value="">Unassigned</option>
              {locations.map((location) => <option key={location.id} value={location.id}>{location.name} · {location.location_type}</option>)}
            </select>
          </label>
        </div>
        <label className="field-label" htmlFor="material-description">Description
          <textarea id="material-description" className="field-textarea" value={form.description} onChange={(event) => update('description', event.target.value)} />
        </label>
        <label className="field-label" htmlFor="material-source">Source
          <input id="material-source" className="field-input" placeholder="e.g. qualified vendor, CMO, internal manufacturing" value={form.source} onChange={(event) => update('source', event.target.value)} />
        </label>
        <div className="flex justify-end gap-3 border-t border-slate-100 pt-5">
          <button type="button" className="button-secondary" onClick={onClose}>Cancel</button>
          <button type="submit" className="button-primary" disabled={isSaving}>{isSaving ? 'Saving…' : material ? 'Save changes' : 'Create material'}</button>
        </div>
      </form>
    </Modal>
  )
}
