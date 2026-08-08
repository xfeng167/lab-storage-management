import { FormEvent, useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { LoadingState } from '../components/LoadingState'
import { MaterialFormModal } from '../components/MaterialFormModal'
import { Modal } from '../components/Modal'
import { PageHeader } from '../components/PageHeader'
import { StatusBadge } from '../components/StatusBadge'
import { canManageOperations, isAdmin, type Location, type Material, type MaterialUpdatePayload } from '../types'
import { formatDate, quantityLabel } from '../utils/format'

type Dialog = 'request' | 'operation' | 'archive' | null
type Operation = 'adjust' | 'check_in' | 'check_out' | 'move'

export function MaterialDetailPage() {
  const { materialId } = useParams()
  const { token, user } = useAuth()
  const [material, setMaterial] = useState<Material | null>(null)
  const [locations, setLocations] = useState<Location[]>([])
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [dialog, setDialog] = useState<Dialog>(null)
  const [isEditOpen, setIsEditOpen] = useState(false)
  const staffAccess = canManageOperations(user)
  const adminAccess = isAdmin(user)
  const id = Number(materialId)

  const load = useCallback(async () => {
    if (!token || !Number.isInteger(id)) return
    setError(null)
    try {
      const [materialResult, locationResult] = await Promise.all([api.getMaterial(token, id), api.listLocations(token)])
      setMaterial(materialResult)
      setLocations(locationResult)
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Unable to load material details.')
    }
  }, [id, token])

  useEffect(() => { void load() }, [load])

  const locationName = useMemo(() => locations.find((location) => location.id === material?.location_id)?.name ?? 'Unassigned', [locations, material?.location_id])

  async function updateMaterial(payload: MaterialUpdatePayload) {
    if (!token || !material) return
    await api.updateMaterial(token, material.id, payload)
    await load()
    setNotice('Material details updated.')
  }

  if (!material && !error) return <LoadingState label="Loading material details…" />
  if (error || !material) return <section><Link className="link text-sm" to="/inventory">← Back to inventory</Link><p className="alert-error mt-6" role="alert">{error ?? 'Material not found.'}</p></section>

  return (
    <section>
      <Link className="link text-sm" to="/inventory">← Back to inventory</Link>
      <div className="mt-5"><PageHeader eyebrow={material.material_code} title={material.material_name} description={material.description || 'No description has been recorded for this material.'} actions={<><button className="button-secondary" onClick={() => setDialog('request')} disabled={material.is_archived}>Request material</button>{staffAccess && <button className="button-secondary" onClick={() => setIsEditOpen(true)}>Edit details</button>}{adminAccess && <button className={material.is_archived ? 'button-primary' : 'button-secondary'} onClick={() => setDialog('archive')}>{material.is_archived ? 'Restore material' : 'Archive material'}</button>}</>} /></div>
      {notice && <p className="alert-info mt-6" role="status">{notice}</p>}
      <div className="mt-8 grid gap-5 lg:grid-cols-[1.2fr_0.8fr]">
        <section className="rounded-2xl border border-slate-200 bg-white shadow-panel">
          <div className="border-b border-slate-100 px-6 py-5"><h2 className="font-semibold text-slate-950">Material profile</h2></div>
          <dl className="divide-y divide-slate-100 px-6"><DetailRow label="Material type" value={material.material_type} /><DetailRow label="Source" value={material.source || '—'} /><DetailRow label="Storage condition" value={material.storage_condition || '—'} /><DetailRow label="Location" value={locationName} /><DetailRow label="QC status" value={<StatusBadge value={material.qc_status} kind="qc" />} /><DetailRow label="Availability" value={<StatusBadge value={material.availability_status} kind="availability" />} /><DetailRow label="Last updated" value={formatDate(material.updated_at)} /></dl>
        </section>
        <section className="rounded-2xl bg-lab-800 p-6 text-white shadow-panel"><p className="text-sm font-medium text-teal-100">Available now</p><p className="mt-4 text-4xl font-semibold tracking-tight">{quantityLabel(material.quantity_available, material.unit)}</p><p className="mt-2 text-sm text-lab-100">{quantityLabel(material.quantity_reserved, material.unit)} currently reserved</p><div className="mt-6 border-t border-white/15 pt-5 text-sm text-lab-100"><p>Replenishment threshold</p><p className="mt-1 text-lg font-semibold text-white">{quantityLabel(material.minimum_quantity, material.unit)}</p></div>{adminAccess && !material.is_archived && <button className="mt-7 w-full rounded-xl bg-white px-4 py-3 text-sm font-semibold text-lab-800 transition hover:bg-teal-50" onClick={() => setDialog('operation')}>Manage inventory</button>}</section>
      </div>
      {material.is_archived && <p className="alert-error mt-6" role="status">This material was archived on {formatDate(material.archived_at)}. {material.archive_reason ? `Reason: ${material.archive_reason}` : ''}</p>}
      {isEditOpen && <MaterialFormModal material={material} locations={locations} onClose={() => setIsEditOpen(false)} onSave={updateMaterial} />}
      {dialog === 'request' && <RequestDialog material={material} onClose={() => setDialog(null)} onComplete={async () => { await load(); setNotice('Your material request was submitted.') }} />}
      {dialog === 'operation' && <OperationDialog material={material} locations={locations} onClose={() => setDialog(null)} onComplete={async (message) => { await load(); setNotice(message) }} />}
      {dialog === 'archive' && <ArchiveDialog material={material} onClose={() => setDialog(null)} onComplete={async (message) => { await load(); setNotice(message) }} />}
    </section>
  )
}

function DetailRow({ label, value }: { label: string; value: ReactNode }) {
  return <div className="grid gap-1 py-4 sm:grid-cols-3 sm:gap-6"><dt className="text-sm font-medium text-slate-500">{label}</dt><dd className="text-sm font-medium text-slate-900 sm:col-span-2">{value}</dd></div>
}

function RequestDialog({ material, onClose, onComplete }: { material: Material; onClose: () => void; onComplete: () => Promise<void> }) {
  const { token } = useAuth()
  const [quantity, setQuantity] = useState('1')
  const [notes, setNotes] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const requestedQuantity = Number(quantity)
    if (!Number.isInteger(requestedQuantity) || requestedQuantity < 1) { setError('Enter a whole quantity of at least 1.'); return }
    if (requestedQuantity > material.quantity_available - material.quantity_reserved) { setError('Requested quantity exceeds unreserved inventory.'); return }
    setIsSubmitting(true)
    setError(null)
    try {
      if (!token) return
      await api.createOrder(token, { material_id: material.id, requested_quantity: requestedQuantity, request_notes: notes.trim() || null })
      await onComplete()
      onClose()
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Unable to submit request.')
    } finally { setIsSubmitting(false) }
  }

  return <Modal title={`Request ${material.material_name}`} onClose={onClose}><form className="space-y-5" onSubmit={submit} noValidate>{error && <p className="alert-error" role="alert">{error}</p>}<p className="rounded-xl bg-slate-50 p-4 text-sm text-slate-600">{quantityLabel(material.quantity_available, material.unit)} available · {quantityLabel(material.quantity_reserved, material.unit)} reserved</p><label className="field-label" htmlFor="request-quantity">Requested quantity<input id="request-quantity" className="field-input" type="number" min="1" max={Math.max(0, material.quantity_available - material.quantity_reserved)} value={quantity} onChange={(event) => setQuantity(event.target.value)} /></label><label className="field-label" htmlFor="request-notes">Notes <span className="font-normal text-slate-500">(optional)</span><textarea id="request-notes" className="field-textarea" value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Describe the intended use or timing." /></label><div className="flex justify-end gap-3 border-t border-slate-100 pt-5"><button type="button" className="button-secondary" onClick={onClose}>Cancel</button><button type="submit" className="button-primary" disabled={isSubmitting}>{isSubmitting ? 'Submitting…' : 'Submit request'}</button></div></form></Modal>
}

function OperationDialog({ material, locations, onClose, onComplete }: { material: Material; locations: Location[]; onClose: () => void; onComplete: (message: string) => Promise<void> }) {
  const { token } = useAuth()
  const [operation, setOperation] = useState<Operation>('adjust')
  const [quantity, setQuantity] = useState(String(material.quantity_available))
  const [locationId, setLocationId] = useState(material.location_id ? String(material.location_id) : '')
  const [reason, setReason] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!reason.trim()) { setError('A reason is required for every inventory operation.'); return }
    const amount = Number(quantity)
    if ((operation !== 'move' && (!Number.isInteger(amount) || amount < (operation === 'adjust' ? 0 : 1)))) { setError('Enter a valid quantity for this operation.'); return }
    if (!token) return
    setIsSubmitting(true)
    setError(null)
    try {
      if (operation === 'adjust') await api.adjustMaterialQuantity(token, material.id, amount, reason.trim())
      if (operation === 'check_in') await api.checkInMaterial(token, material.id, amount, reason.trim())
      if (operation === 'check_out') await api.checkOutMaterial(token, material.id, amount, reason.trim())
      if (operation === 'move') await api.moveMaterial(token, material.id, locationId ? Number(locationId) : null, reason.trim())
      await onComplete('Inventory operation recorded.')
      onClose()
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Unable to record inventory operation.')
    } finally { setIsSubmitting(false) }
  }

  const quantityLabelText = operation === 'adjust' ? 'New available quantity' : 'Quantity'
  return <Modal title="Manage inventory" onClose={onClose}><form className="space-y-5" onSubmit={submit} noValidate>{error && <p className="alert-error" role="alert">{error}</p>}<label className="field-label" htmlFor="operation-type">Operation<select id="operation-type" className="field-select" value={operation} onChange={(event) => setOperation(event.target.value as Operation)}><option value="adjust">Set available quantity</option><option value="check_in">Check in quantity</option><option value="check_out">Check out quantity</option><option value="move">Move material</option></select></label>{operation === 'move' ? <label className="field-label" htmlFor="move-location">New location<select id="move-location" className="field-select" value={locationId} onChange={(event) => setLocationId(event.target.value)}><option value="">Unassigned</option>{locations.map((location) => <option key={location.id} value={location.id}>{location.name}</option>)}</select></label> : <label className="field-label" htmlFor="operation-quantity">{quantityLabelText}<input id="operation-quantity" className="field-input" type="number" min={operation === 'adjust' ? 0 : 1} value={quantity} onChange={(event) => setQuantity(event.target.value)} /></label>}<label className="field-label" htmlFor="operation-reason">Reason<textarea id="operation-reason" className="field-textarea" value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Explain why this change is needed." /></label><div className="flex justify-end gap-3 border-t border-slate-100 pt-5"><button type="button" className="button-secondary" onClick={onClose}>Cancel</button><button type="submit" className="button-primary" disabled={isSubmitting}>{isSubmitting ? 'Recording…' : 'Record operation'}</button></div></form></Modal>
}

function ArchiveDialog({ material, onClose, onComplete }: { material: Material; onClose: () => void; onComplete: (message: string) => Promise<void> }) {
  const { token } = useAuth()
  const [reason, setReason] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!token) return
    if (!material.is_archived && !reason.trim()) { setError('Provide an archive reason.'); return }
    setIsSubmitting(true)
    setError(null)
    try {
      if (material.is_archived) await api.restoreMaterial(token, material.id)
      else await api.archiveMaterial(token, material.id, reason.trim())
      await onComplete(material.is_archived ? 'Material restored to the active catalogue.' : 'Material archived.')
      onClose()
    } catch (caughtError) { setError(caughtError instanceof Error ? caughtError.message : 'Unable to update archive state.') } finally { setIsSubmitting(false) }
  }

  return <Modal title={material.is_archived ? 'Restore material' : 'Archive material'} onClose={onClose}><form className="space-y-5" onSubmit={submit}>{error && <p className="alert-error" role="alert">{error}</p>}<p className="text-sm leading-6 text-slate-600">{material.is_archived ? 'Restoring returns this material to the active catalogue.' : 'Archived materials remain in the audit trail but are hidden from the active catalogue.'}</p>{!material.is_archived && <label className="field-label" htmlFor="archive-reason">Archive reason<textarea id="archive-reason" className="field-textarea" value={reason} onChange={(event) => setReason(event.target.value)} /></label>}<div className="flex justify-end gap-3 border-t border-slate-100 pt-5"><button type="button" className="button-secondary" onClick={onClose}>Cancel</button><button type="submit" className="button-primary" disabled={isSubmitting}>{isSubmitting ? 'Saving…' : material.is_archived ? 'Restore material' : 'Archive material'}</button></div></form></Modal>
}
