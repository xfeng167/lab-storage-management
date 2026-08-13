import { useCallback, useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { EmptyState } from '../components/EmptyState'
import { LoadingState } from '../components/LoadingState'
import { LocationFormModal } from '../components/LocationFormModal'
import { Modal } from '../components/Modal'
import { PageHeader } from '../components/PageHeader'
import type { Location, LocationPayload } from '../types'
import { formatDate } from '../utils/format'

export function LocationsPage() {
  const { token } = useAuth()
  const [locations, setLocations] = useState<Location[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [editingLocation, setEditingLocation] = useState<Location | undefined>()
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [detail, setDetail] = useState<Location | null>(null)

  const load = useCallback(async () => {
    if (!token) return
    setError(null)
    try { setLocations(await api.listLocations(token)) } catch (caughtError) { setError(caughtError instanceof Error ? caughtError.message : 'Unable to load locations.') }
  }, [token])

  useEffect(() => { void load() }, [load])

  const parentNames = useMemo(() => new Map((locations ?? []).map((location) => [location.id, location.name])), [locations])

  async function saveLocation(payload: LocationPayload) {
    if (!token) return
    if (editingLocation) await api.updateLocation(token, editingLocation.id, payload)
    else await api.createLocation(token, payload)
    await load()
  }

  async function openDetails(id: number) {
    if (!token) return
    try { setDetail(await api.getLocation(token, id)) } catch (caughtError) { setError(caughtError instanceof Error ? caughtError.message : 'Unable to load location details.') }
  }

  async function openEdit(id: number) {
    if (!token) return
    try { setEditingLocation(await api.getLocation(token, id)) } catch (caughtError) { setError(caughtError instanceof Error ? caughtError.message : 'Unable to load location details.') }
  }

  if (!locations && !error) return <LoadingState label="Loading storage locations…" />

  return (
    <section>
      <PageHeader eyebrow="Storage map" title="Locations" description="Maintain the rooms, freezers, shelves, and other storage points used by your inventory." actions={<button className="button-primary" onClick={() => setIsCreateOpen(true)}>Add location</button>} />
      {error && <p className="alert-error mt-8" role="alert">{error}</p>}
      <div className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {locations?.map((location) => <article key={location.id} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-panel"><div className="flex items-start justify-between gap-3"><div><p className="text-xs font-bold uppercase tracking-[0.16em] text-teal-700">{location.location_type}</p><h2 className="mt-2 text-lg font-semibold text-slate-950">{location.name}</h2></div><span className="grid h-10 w-10 place-items-center rounded-xl bg-lab-50 text-lg text-lab-700" aria-hidden="true">⌘</span></div><dl className="mt-6 space-y-3 text-sm"><div className="flex justify-between gap-4"><dt className="text-slate-500">Parent</dt><dd className="font-medium text-slate-900">{parentNames.get(location.parent_location_id ?? -1) ?? 'Root location'}</dd></div><div className="flex justify-between gap-4"><dt className="text-slate-500">Temperature</dt><dd className="font-medium text-slate-900">{location.temperature_zone || 'Not specified'}</dd></div></dl>{location.description && <p className="mt-5 border-t border-slate-100 pt-4 text-sm leading-6 text-slate-600">{location.description}</p>}<div className="mt-6 flex gap-4 border-t border-slate-100 pt-4"><button type="button" className="link text-sm" onClick={() => void openDetails(location.id)}>View details</button><button type="button" className="link text-sm" onClick={() => void openEdit(location.id)}>Edit</button></div></article>)}
      </div>
      {locations?.length === 0 && <div className="mt-8"><EmptyState title="No storage locations yet" description="Create a location before assigning materials to a physical storage point." action={<button className="button-primary" onClick={() => setIsCreateOpen(true)}>Add location</button>} /></div>}
      {isCreateOpen && <LocationFormModal locations={locations ?? []} onClose={() => setIsCreateOpen(false)} onSave={saveLocation} />}
      {editingLocation && <LocationFormModal location={editingLocation} locations={locations ?? []} onClose={() => setEditingLocation(undefined)} onSave={saveLocation} />}
      {detail && <Modal title={detail.name} onClose={() => setDetail(null)}><dl className="divide-y divide-slate-100"><LocationDetail label="Location type" value={detail.location_type} /><LocationDetail label="Temperature zone" value={detail.temperature_zone || 'Not specified'} /><LocationDetail label="Parent location" value={parentNames.get(detail.parent_location_id ?? -1) ?? 'Root location'} /><LocationDetail label="Description" value={detail.description || 'No description recorded.'} /><LocationDetail label="Last updated" value={formatDate(detail.updated_at)} /></dl></Modal>}
    </section>
  )
}

function LocationDetail({ label, value }: { label: string; value: string }) {
  return <div className="py-4"><dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</dt><dd className="mt-1 text-sm leading-6 text-slate-900">{value}</dd></div>
}
