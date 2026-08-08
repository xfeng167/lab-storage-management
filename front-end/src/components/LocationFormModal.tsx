import { FormEvent, useState } from 'react'
import type { Location, LocationPayload } from '../types'
import { Modal } from './Modal'

interface LocationFormModalProps {
  location?: Location
  locations: Location[]
  onClose: () => void
  onSave: (payload: LocationPayload) => Promise<void>
}

export function LocationFormModal({ location, locations, onClose, onSave }: LocationFormModalProps) {
  const [form, setForm] = useState<LocationPayload>({
    name: location?.name ?? '',
    location_type: location?.location_type ?? '',
    parent_location_id: location?.parent_location_id ?? null,
    temperature_zone: location?.temperature_zone ?? '',
    description: location?.description ?? '',
  })
  const [error, setError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!form.name.trim() || !form.location_type.trim()) {
      setError('Name and location type are required.')
      return
    }
    setIsSaving(true)
    setError(null)
    try {
      await onSave({ ...form, name: form.name.trim(), location_type: form.location_type.trim(), temperature_zone: form.temperature_zone?.trim() || null, description: form.description?.trim() || null })
      onClose()
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Unable to save location.')
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <Modal title={location ? 'Edit location' : 'Add location'} onClose={onClose}>
      <form className="space-y-5" onSubmit={submit} noValidate>
        {error && <p className="alert-error" role="alert">{error}</p>}
        <label className="field-label" htmlFor="location-name">Name
          <input id="location-name" className="field-input" value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} />
        </label>
        <label className="field-label" htmlFor="location-type">Location type
          <input id="location-type" className="field-input" placeholder="e.g. freezer, room, shelf" value={form.location_type} onChange={(event) => setForm((current) => ({ ...current, location_type: event.target.value }))} />
        </label>
        <label className="field-label" htmlFor="parent-location">Parent location
          <select id="parent-location" className="field-select" value={form.parent_location_id ?? ''} onChange={(event) => setForm((current) => ({ ...current, parent_location_id: event.target.value ? Number(event.target.value) : null }))}>
            <option value="">No parent location</option>
            {locations.filter((entry) => entry.id !== location?.id).map((entry) => <option key={entry.id} value={entry.id}>{entry.name} · {entry.location_type}</option>)}
          </select>
        </label>
        <label className="field-label" htmlFor="temperature-zone">Temperature zone
          <input id="temperature-zone" className="field-input" placeholder="e.g. -20C" value={form.temperature_zone ?? ''} onChange={(event) => setForm((current) => ({ ...current, temperature_zone: event.target.value }))} />
        </label>
        <label className="field-label" htmlFor="location-description">Description
          <textarea id="location-description" className="field-textarea" value={form.description ?? ''} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} />
        </label>
        <div className="flex justify-end gap-3 border-t border-slate-100 pt-5">
          <button type="button" className="button-secondary" onClick={onClose}>Cancel</button>
          <button type="submit" className="button-primary" disabled={isSaving}>{isSaving ? 'Saving…' : location ? 'Save changes' : 'Create location'}</button>
        </div>
      </form>
    </Modal>
  )
}
