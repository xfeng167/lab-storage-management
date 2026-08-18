import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { EmptyState } from '../components/EmptyState'
import { LoadingState } from '../components/LoadingState'
import { PageHeader } from '../components/PageHeader'
import { StatusBadge } from '../components/StatusBadge'
import { isAdmin, type InventoryActivity, type LocationInventorySummary, type LowStockMaterial, type PendingOrder } from '../types'
import { formatDate, quantityLabel } from '../utils/format'

interface ReportData {
  lowStock: LowStockMaterial[]
  pendingOrders: PendingOrder[]
  activity: InventoryActivity[]
  byLocation: LocationInventorySummary[]
}

export function ReportsPage() {
  const { token, user } = useAuth()
  const [data, setData] = useState<ReportData | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!token) return
    setError(null)
    try {
      const [lowStock, pendingOrders, activity, byLocation] = await Promise.all([api.listLowStock(token), api.listPendingOrders(token), api.listRecentActivity(token), api.listMaterialsByLocation(token)])
      setData({ lowStock, pendingOrders, activity, byLocation })
    } catch (caughtError) { setError(caughtError instanceof Error ? caughtError.message : 'Unable to load reports.') }
  }, [token])

  useEffect(() => { void load() }, [load])
  if (!data && !error) return <LoadingState label="Loading operations reports…" />

  return (
    <section>
      <PageHeader eyebrow="Operations intelligence" title="Reports" description="Use live inventory and order signals to prioritize replenishment, requests, and storage capacity." actions={<button className="button-secondary" onClick={() => void load()}>Refresh reports</button>} />
      {error && <p className="alert-error mt-8" role="alert">{error}</p>}
      {data && <div className="mt-8 space-y-8">
        <section className="rounded-2xl border border-slate-200 bg-white shadow-panel"><div className="border-b border-slate-100 px-6 py-5"><h2 className="font-semibold text-slate-950">Low-stock materials</h2><p className="mt-1 text-sm text-slate-500">Active materials at or below their configured minimum quantity.</p></div>{data.lowStock.length ? <div className="overflow-x-auto"><table className="min-w-full divide-y divide-slate-200"><thead className="bg-slate-50"><tr><th className="table-heading">Material</th><th className="table-heading">On hand</th><th className="table-heading">Reserved</th><th className="table-heading">Minimum</th><th className="table-heading"><span className="sr-only">Open</span></th></tr></thead><tbody className="divide-y divide-slate-100">{data.lowStock.map((material) => <tr key={material.id}><td className="table-cell"><p className="font-semibold text-slate-900">{material.material_name}</p><p className="mt-1 text-xs text-slate-500">{material.material_code}</p></td><td className="table-cell font-semibold text-amber-700">{quantityLabel(material.quantity_available, material.unit)}</td><td className="table-cell">{quantityLabel(material.quantity_reserved, material.unit)}</td><td className="table-cell">{quantityLabel(material.minimum_quantity, material.unit)}</td><td className="table-cell text-right"><Link className="link" to={`/inventory/${material.id}`}>Open</Link></td></tr>)}</tbody></table></div> : <EmptyState title="No low-stock items" description="Every active material is currently above its defined minimum level." />}</section>
        <div className="grid gap-8 xl:grid-cols-2">
          <section className="rounded-2xl border border-slate-200 bg-white shadow-panel"><div className="border-b border-slate-100 px-6 py-5"><h2 className="font-semibold text-slate-950">Pending requests</h2><p className="mt-1 text-sm text-slate-500">Submitted requests waiting for review.</p></div>{data.pendingOrders.length ? <div className="divide-y divide-slate-100">{data.pendingOrders.map((order) => <Link key={order.id} to="/requests" className="block px-6 py-4 transition hover:bg-slate-50"><div className="flex justify-between gap-3"><div><p className="font-semibold text-slate-900">{order.material_name}</p><p className="mt-1 text-sm text-slate-600">{order.requested_by_username} · {order.requested_quantity} requested</p></div><StatusBadge value={order.status} kind="order" /></div><p className="mt-2 text-xs text-slate-500">{formatDate(order.created_at)}</p></Link>)}</div> : <EmptyState title="No pending requests" description="There are no submitted requests awaiting an administrative review." />}</section>
          <section className="rounded-2xl border border-slate-200 bg-white shadow-panel"><div className="border-b border-slate-100 px-6 py-5"><h2 className="font-semibold text-slate-950">Inventory by location</h2><p className="mt-1 text-sm text-slate-500">Active material count and quantities by storage location.</p></div>{data.byLocation.length ? <div className="divide-y divide-slate-100">{data.byLocation.map((location) => <div key={location.location_id ?? 'unassigned'} className="px-6 py-4"><div className="flex items-center justify-between gap-4"><div><p className="font-semibold text-slate-900">{location.location_name}</p><p className="mt-1 text-sm text-slate-600">{location.material_count} material{location.material_count === 1 ? '' : 's'}</p></div><div className="text-right"><p className="font-semibold text-slate-900">{location.total_quantity_available.toLocaleString()} on hand</p><p className="mt-1 text-xs text-slate-500">{location.total_quantity_reserved.toLocaleString()} reserved</p></div></div></div>)}</div> : <EmptyState title="No location data" description="Assign active materials to locations to populate this report." />}</section>
        </div>
        <section className="rounded-2xl border border-slate-200 bg-white shadow-panel"><div className="flex items-center justify-between border-b border-slate-100 px-6 py-5"><div><h2 className="font-semibold text-slate-950">Recent inventory activity</h2><p className="mt-1 text-sm text-slate-500">The latest 20 logged inventory operations.</p></div>{isAdmin(user) && <Link className="link text-sm" to="/audit">Open audit log</Link>}</div>{data.activity.length ? <div className="overflow-x-auto"><table className="min-w-full divide-y divide-slate-200"><thead className="bg-slate-50"><tr><th className="table-heading">Material</th><th className="table-heading">Change</th><th className="table-heading">Reason</th><th className="table-heading">By</th><th className="table-heading">When</th></tr></thead><tbody className="divide-y divide-slate-100">{data.activity.map((entry) => <tr key={entry.id}><td className="table-cell"><p className="font-semibold text-slate-900">{entry.material_name}</p><p className="mt-1 text-xs text-slate-500">{entry.material_code}</p></td><td className="table-cell"><p className="font-medium text-slate-900">{entry.operation_type.replace(/_/g, ' ')}</p><p className="mt-1 text-xs text-slate-500">{entry.before_value} → {entry.after_value}</p></td><td className="table-cell max-w-xs truncate" title={entry.reason}>{entry.reason}</td><td className="table-cell">{entry.username}</td><td className="table-cell whitespace-nowrap text-xs">{formatDate(entry.created_at)}</td></tr>)}</tbody></table></div> : <EmptyState title="No activity logged" description="Inventory adjustments, movements, check-ins, and check-outs will appear here." />}</section>
      </div>}
    </section>
  )
}
