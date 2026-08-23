import { FormEvent, useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { EmptyState } from '../components/EmptyState'
import { LoadingState } from '../components/LoadingState'
import { Modal } from '../components/Modal'
import { PageHeader } from '../components/PageHeader'
import { PaginationControls } from '../components/PaginationControls'
import { StatusBadge } from '../components/StatusBadge'
import { isAdmin, type Material, type Order, type Page } from '../types'
import { formatDate, quantityLabel } from '../utils/format'

type ReviewAction = 'approve' | 'reject' | 'fulfill' | 'cancel' | 'archive'

function canArchiveOrder(order: Order): boolean {
  return !order.is_archived && !['submitted', 'approved'].includes(order.status)
}

export function OrdersPage() {
  const { token, user } = useAuth()
  const [orders, setOrders] = useState<Order[] | null>(null)
  const [resultPage, setResultPage] = useState<Page<Order> | null>(null)
  const [page, setPage] = useState(1)
  const [materials, setMaterials] = useState<Material[]>([])
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null)
  const [review, setReview] = useState<{ order: Order; action: ReviewAction } | null>(null)
  const [includeArchived, setIncludeArchived] = useState(false)
  const adminAccess = isAdmin(user)

  const load = useCallback(async () => {
    if (!token) return
    setError(null)
    try {
      const [orderResult, materialResult] = await Promise.all([api.listOrders(token, { include_archived: includeArchived, active_only: !includeArchived, page, size: 25 }), api.listAllMaterials(token)])
      setOrders(orderResult.items)
      setResultPage(orderResult)
      setMaterials(materialResult)
    } catch (caughtError) { setError(caughtError instanceof Error ? caughtError.message : 'Unable to load requests.') }
  }, [includeArchived, page, token])

  useEffect(() => { void load() }, [load])
  const materialMap = useMemo(() => new Map(materials.map((material) => [material.id, material])), [materials])
  const archivedOnPage = useMemo(() => (orders ?? []).filter((order) => order.is_archived).length, [orders])

  async function openOrder(id: number) {
    if (!token) return
    try { setSelectedOrder(await api.getOrder(token, id)) } catch (caughtError) { setError(caughtError instanceof Error ? caughtError.message : 'Unable to load request details.') }
  }

  if (!orders && !error) return <LoadingState label="Loading material requests…" />

  return (
    <section>
      <PageHeader eyebrow={adminAccess ? 'Administration' : 'Material requests'} title={adminAccess ? 'Request queue' : 'Your requests'} description={adminAccess ? 'Review, approve, fulfill, or cancel requests across the laboratory.' : 'Submit requests for available material and follow each decision through to fulfillment.'} actions={<button className="button-primary" onClick={() => setIsCreateOpen(true)}>New request</button>} />
      {notice && <p className="alert-info mt-6" role="status">{notice}</p>}
      {error && <p className="alert-error mt-6" role="alert">{error}</p>}
      <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-5 shadow-panel">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-sm font-semibold text-slate-950">{includeArchived ? 'All requests' : 'Active request queue'}</h2>
            <p className="mt-1 text-sm text-slate-500">{includeArchived ? `${resultPage?.total ?? 0} total requests. This page includes ${archivedOnPage} archived.` : `${resultPage?.total ?? 0} active requests. Submitted and approved requests need action.`}</p>
          </div>
          <label className="inline-flex items-center gap-2 text-sm font-medium text-slate-700">
            <input type="checkbox" className="h-4 w-4 rounded border-slate-300 text-lab-700 focus:ring-teal-500" checked={includeArchived} onChange={(event) => { setIncludeArchived(event.target.checked); setPage(1) }} />
            Include archived requests
          </label>
        </div>
      </section>
      <section className="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-panel">
        {orders?.length ? <div className="overflow-x-auto"><table className="min-w-full divide-y divide-slate-200"><thead className="bg-slate-50"><tr><th className="table-heading">Request</th>{adminAccess && <th className="table-heading">Requester</th>}<th className="table-heading">Material</th><th className="table-heading">Status</th><th className="table-heading">Created</th><th className="table-heading"><span className="sr-only">Actions</span></th></tr></thead><tbody className="divide-y divide-slate-100">{orders.map((order) => { const material = materialMap.get(order.material_id); return <tr key={order.id} className={order.is_archived ? 'bg-slate-50/70 text-slate-500 hover:bg-slate-100' : 'hover:bg-slate-50'}><td className="table-cell"><p className={order.is_archived ? 'font-semibold text-slate-600' : 'font-semibold text-slate-900'}>Request #{order.id}</p><p className="mt-1 text-xs text-slate-500">{quantityLabel(order.requested_quantity, material?.unit ?? 'units')}{order.reserved_quantity ? ` · ${quantityLabel(order.reserved_quantity, material?.unit ?? 'units')} reserved` : ''}</p></td>{adminAccess && <td className="table-cell">{order.requested_by_username} (#{order.requested_by_user_id})</td>}<td className="table-cell"><p className={order.is_archived ? 'font-medium text-slate-600' : 'font-medium text-slate-900'}>{material?.material_name ?? `Material #${order.material_id}`}</p><p className="mt-1 text-xs text-slate-500">{material?.material_code ?? 'Unavailable material record'}</p></td><td className="table-cell"><div className="flex flex-wrap gap-2"><StatusBadge value={order.status} kind="order" />{order.is_archived && <StatusBadge value="archived" kind="order" />}</div></td><td className="table-cell whitespace-nowrap text-xs">{formatDate(order.created_at)}</td><td className="table-cell"><div className="flex justify-end gap-3"><button type="button" className="link text-sm" onClick={() => void openOrder(order.id)}>View</button>{adminAccess && order.status === 'submitted' && <><button type="button" className="link text-sm" onClick={() => setReview({ order, action: 'approve' })}>Approve</button><button type="button" className="link text-sm" onClick={() => setReview({ order, action: 'reject' })}>Reject</button></>}{adminAccess && order.status === 'approved' && <button type="button" className="link text-sm" onClick={() => setReview({ order, action: 'fulfill' })}>Fulfill</button>}{(order.status === 'submitted' || order.status === 'approved') && <button type="button" className="link text-sm" onClick={() => setReview({ order, action: 'cancel' })}>Cancel</button>}{canArchiveOrder(order) && <button type="button" className="link text-sm" onClick={() => setReview({ order, action: 'archive' })}>Archive</button>}</div></td></tr> })}</tbody></table></div> : <EmptyState title={includeArchived ? 'No requests found' : 'No active requests'} description={includeArchived ? 'Create a request for any active material in the catalogue.' : 'Create a request or include archived requests to review older records.'} action={<button className="button-primary" onClick={() => setIsCreateOpen(true)}>New request</button>} />}
        {resultPage && <PaginationControls page={resultPage.page} pages={resultPage.pages} total={resultPage.total} label="requests" onPageChange={setPage} />}
      </section>
      {isCreateOpen && <CreateRequestDialog materials={materials} onClose={() => setIsCreateOpen(false)} onComplete={async () => { await load(); setNotice('Your material request was submitted.') }} />}
      {selectedOrder && <OrderDetailDialog order={selectedOrder} material={materialMap.get(selectedOrder.material_id)} onClose={() => setSelectedOrder(null)} />}
      {review && <ReviewDialog review={review} onClose={() => setReview(null)} onComplete={async (message) => { await load(); setNotice(message) }} />}
    </section>
  )
}

function CreateRequestDialog({ materials, onClose, onComplete }: { materials: Material[]; onClose: () => void; onComplete: () => Promise<void> }) {
  const { token } = useAuth()
  const requestableMaterials = materials.filter((material) => !material.is_archived && material.quantity_available > material.quantity_reserved)
  const [materialId, setMaterialId] = useState('')
  const [quantity, setQuantity] = useState('1')
  const [notes, setNotes] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const requestedQuantity = Number(quantity)
    if (!materialId) { setError('Choose a material.'); return }
    if (!Number.isInteger(requestedQuantity) || requestedQuantity < 1) { setError('Enter a whole quantity of at least 1.'); return }
    const selectedMaterial = requestableMaterials.find((material) => material.id === Number(materialId))
    if (!selectedMaterial || requestedQuantity > selectedMaterial.quantity_available - selectedMaterial.quantity_reserved) { setError('Requested quantity exceeds unreserved inventory.'); return }
    if (!token) return
    setIsSubmitting(true)
    setError(null)
    try { await api.createOrder(token, { material_id: Number(materialId), requested_quantity: requestedQuantity, request_notes: notes.trim() || null }); await onComplete(); onClose() } catch (caughtError) { setError(caughtError instanceof Error ? caughtError.message : 'Unable to submit request.') } finally { setIsSubmitting(false) }
  }

  return <Modal title="New material request" onClose={onClose}><form className="space-y-5" onSubmit={submit} noValidate>{error && <p className="alert-error" role="alert">{error}</p>}<label className="field-label" htmlFor="request-material">Material<select id="request-material" className="field-select" value={materialId} onChange={(event) => setMaterialId(event.target.value)}><option value="">Choose a material</option>{requestableMaterials.map((material) => <option key={material.id} value={material.id}>{material.material_name} · {quantityLabel(material.quantity_available - material.quantity_reserved, material.unit)} unreserved</option>)}</select></label><label className="field-label" htmlFor="new-request-quantity">Requested quantity<input id="new-request-quantity" className="field-input" type="number" min="1" value={quantity} onChange={(event) => setQuantity(event.target.value)} /></label><label className="field-label" htmlFor="new-request-notes">Notes <span className="font-normal text-slate-500">(optional)</span><textarea id="new-request-notes" className="field-textarea" value={notes} onChange={(event) => setNotes(event.target.value)} /></label><div className="flex justify-end gap-3 border-t border-slate-100 pt-5"><button type="button" className="button-secondary" onClick={onClose}>Cancel</button><button type="submit" className="button-primary" disabled={isSubmitting}>{isSubmitting ? 'Submitting…' : 'Submit request'}</button></div></form></Modal>
}

function OrderDetailDialog({ order, material, onClose }: { order: Order; material: Material | undefined; onClose: () => void }) {
  return <Modal title={`Request #${order.id}`} onClose={onClose}><dl className="divide-y divide-slate-100"><OrderDetail label="Requested by" value={`${order.requested_by_username} (#${order.requested_by_user_id})`} /><OrderDetail label="Material" value={material ? `${material.material_name} (${material.material_code})` : `Material #${order.material_id}`} /><OrderDetail label="Requested quantity" value={quantityLabel(order.requested_quantity, material?.unit ?? 'units')} /><OrderDetail label="Reserved quantity" value={quantityLabel(order.reserved_quantity, material?.unit ?? 'units')} /><OrderDetail label="Status" value={<StatusBadge value={order.status} kind="order" />} /><OrderDetail label="Request notes" value={order.request_notes || 'None'} /><OrderDetail label="Outcome notes" value={order.outcome_notes || 'No outcome recorded'} /><OrderDetail label="Archived" value={order.is_archived ? `Yes${order.archived_at ? ` · ${formatDate(order.archived_at)}` : ''}` : 'No'} /><OrderDetail label="Archive reason" value={order.archive_reason || 'None'} /><OrderDetail label="Reviewed" value={formatDate(order.reviewed_at)} /><OrderDetail label="Created" value={formatDate(order.created_at)} /></dl></Modal>
}

function OrderDetail({ label, value }: { label: string; value: ReactNode }) {
  return <div className="py-4"><dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</dt><dd className="mt-1 text-sm text-slate-900">{value}</dd></div>
}

function ReviewDialog({ review, onClose, onComplete }: { review: { order: Order; action: ReviewAction }; onClose: () => void; onComplete: (message: string) => Promise<void> }) {
  const { token } = useAuth()
  const [notes, setNotes] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const actionLabel = review.action.charAt(0).toUpperCase() + review.action.slice(1)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!token) return
    setIsSubmitting(true)
    setError(null)
    try {
      const outcomeNotes = notes.trim() || null
      if (review.action === 'archive' && !outcomeNotes) { setError('Archive reason is required.'); setIsSubmitting(false); return }
      if (review.action === 'approve') await api.approveOrder(token, review.order.id, outcomeNotes)
      if (review.action === 'reject') await api.rejectOrder(token, review.order.id, outcomeNotes)
      if (review.action === 'fulfill') await api.fulfillOrder(token, review.order.id, outcomeNotes)
      if (review.action === 'cancel') await api.cancelOrder(token, review.order.id, outcomeNotes)
      if (review.action === 'archive') await api.archiveOrder(token, review.order.id, outcomeNotes as string)
      const outcome = review.action === 'fulfill' ? 'fulfilled' : review.action === 'cancel' ? 'canceled' : review.action === 'archive' ? 'archived' : `${review.action}d`
      await onComplete(`Request #${review.order.id} was ${outcome}.`)
      onClose()
    } catch (caughtError) { setError(caughtError instanceof Error ? caughtError.message : 'Unable to update request.') } finally { setIsSubmitting(false) }
  }

  return <Modal title={`${actionLabel} request #${review.order.id}`} onClose={onClose}><form className="space-y-5" onSubmit={submit}>{error && <p className="alert-error" role="alert">{error}</p>}<p className="text-sm leading-6 text-slate-600">{review.action === 'archive' ? 'This permanently archives the request from the default queue. Archived orders are retained for audit and cannot be restored.' : 'This action updates the request lifecycle and may affect reserved inventory.'}</p><label className="field-label" htmlFor="review-notes">{review.action === 'archive' ? 'Archive reason' : 'Outcome notes'} {review.action !== 'archive' && <span className="font-normal text-slate-500">(optional)</span>}<textarea id="review-notes" className="field-textarea" value={notes} onChange={(event) => setNotes(event.target.value)} /></label><div className="flex justify-end gap-3 border-t border-slate-100 pt-5"><button type="button" className="button-secondary" onClick={onClose}>Cancel</button><button type="submit" className="button-primary" disabled={isSubmitting}>{isSubmitting ? 'Saving…' : `${actionLabel} request`}</button></div></form></Modal>
}
