import { Link } from 'react-router-dom'
import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { EmptyState } from '../components/EmptyState'
import { LoadingState } from '../components/LoadingState'
import { MetricCard } from '../components/MetricCard'
import { PageHeader } from '../components/PageHeader'
import { StatusBadge } from '../components/StatusBadge'
import { canManageOperations, type InventoryActivity, type LowStockMaterial, type Material, type Order, type PendingOrder } from '../types'
import { formatDate, quantityLabel } from '../utils/format'

interface DashboardData {
  materials: Material[]
  orders: Order[]
  lowStock: LowStockMaterial[]
  pendingOrders: PendingOrder[]
  activity: InventoryActivity[]
}

export function DashboardPage() {
  const { token, user } = useAuth()
  const [data, setData] = useState<DashboardData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const staffAccess = canManageOperations(user)

  const load = useCallback(async () => {
    if (!token) return
    setError(null)
    try {
      const [materials, orders, lowStock, pendingOrders, activity] = await Promise.all([
        api.listMaterials(token),
        api.listOrders(token),
        staffAccess ? api.listLowStock(token) : Promise.resolve([]),
        staffAccess ? api.listPendingOrders(token) : Promise.resolve([]),
        staffAccess ? api.listRecentActivity(token) : Promise.resolve([]),
      ])
      setData({ materials, orders, lowStock, pendingOrders, activity })
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Unable to load the overview.')
    }
  }, [staffAccess, token])

  useEffect(() => { void load() }, [load])

  if (!data && !error) return <LoadingState label="Loading workspace overview…" />
  if (error) return <section><PageHeader eyebrow="Workspace" title="Overview unavailable" description="The latest operational data could not be loaded." actions={<button className="button-primary" onClick={() => void load()}>Try again</button>} /><p className="alert-error mt-8" role="alert">{error}</p></section>

  const materials = data?.materials ?? []
  const orders = data?.orders ?? []
  const lowStockCount = staffAccess ? data?.lowStock.length ?? 0 : materials.filter((material) => material.quantity_available <= material.minimum_quantity).length
  const totalQuantity = materials.reduce((total, material) => total + material.quantity_available, 0)
  const submittedOrders = orders.filter((order) => order.status === 'submitted').length

  return (
    <section>
      <PageHeader eyebrow="Workspace" title={`Good ${new Date().getHours() < 12 ? 'morning' : 'afternoon'}, ${user?.username ?? 'there'}`} description={staffAccess ? 'Monitor inventory health, pending requests, and the activity that needs your attention.' : 'Browse available materials and keep track of your requests.'} actions={<Link className="button-secondary" to="/inventory">Browse inventory</Link>} />
      <div className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Active materials" value={materials.length} detail="Available in the inventory catalogue" tone="blue" to="/inventory" />
        <MetricCard label="Total on hand" value={totalQuantity.toLocaleString()} detail="Combined quantity across active materials" tone="teal" to="/inventory" />
        <MetricCard label="Low-stock items" value={lowStockCount} detail={lowStockCount ? 'Needs attention before it runs out' : 'All material levels are healthy'} tone="amber" to={staffAccess ? '/reports' : '/inventory'} />
        <MetricCard label={staffAccess ? 'Submitted requests' : 'Open requests'} value={submittedOrders} detail={staffAccess ? 'Awaiting an administrative review' : 'Awaiting a review'} tone="violet" to="/requests" />
      </div>
      <div className="mt-8 grid gap-8 xl:grid-cols-[1.1fr_0.9fr]">
        <section className="rounded-2xl border border-slate-200 bg-white shadow-panel">
          <div className="flex items-center justify-between border-b border-slate-100 px-6 py-5"><div><h2 className="font-semibold text-slate-950">{staffAccess ? 'Low-stock watchlist' : 'Your requests'}</h2><p className="mt-1 text-sm text-slate-500">{staffAccess ? 'Items at or below their replenishment threshold.' : 'Recent material requests and their latest status.'}</p></div><Link className="link text-sm" to={staffAccess ? '/reports' : '/requests'}>View all</Link></div>
          {staffAccess ? (
            data?.lowStock.length ? <div className="divide-y divide-slate-100">{data.lowStock.slice(0, 5).map((material) => <Link key={material.id} to={`/inventory/${material.id}`} className="flex items-center justify-between gap-4 px-6 py-4 transition hover:bg-slate-50"><div><p className="font-semibold text-slate-900">{material.material_name}</p><p className="mt-1 text-xs text-slate-500">{material.material_code} · minimum {quantityLabel(material.minimum_quantity, material.unit)}</p></div><p className="text-sm font-semibold text-amber-700">{quantityLabel(material.quantity_available, material.unit)}</p></Link>)}</div> : <EmptyState title="No low-stock materials" description="Everything currently sits above its defined minimum quantity." />
          ) : (
            orders.length ? <div className="divide-y divide-slate-100">{orders.slice(0, 5).map((order) => <Link key={order.id} to="/requests" className="flex items-center justify-between gap-4 px-6 py-4 transition hover:bg-slate-50"><div><p className="font-semibold text-slate-900">Request #{order.id}</p><p className="mt-1 text-xs text-slate-500">{order.requested_quantity} requested · {formatDate(order.created_at)}</p></div><StatusBadge value={order.status} kind="order" /></Link>)}</div> : <EmptyState title="No requests yet" description="Create a request from the inventory catalogue when you need material." action={<Link className="button-primary" to="/inventory">Explore materials</Link>} />
          )}
        </section>
        <section className="rounded-2xl border border-slate-200 bg-white shadow-panel">
          <div className="flex items-center justify-between border-b border-slate-100 px-6 py-5"><div><h2 className="font-semibold text-slate-950">{staffAccess ? 'Recent inventory activity' : 'Quick actions'}</h2><p className="mt-1 text-sm text-slate-500">{staffAccess ? 'The latest recorded quantity and location changes.' : 'Start where your work needs you most.'}</p></div>{staffAccess && <Link className="link text-sm" to="/audit">Audit log</Link>}</div>
          {staffAccess ? (data?.activity.length ? <div className="divide-y divide-slate-100">{data.activity.slice(0, 5).map((entry) => <div key={entry.id} className="px-6 py-4"><div className="flex items-start justify-between gap-3"><div><p className="font-semibold text-slate-900">{entry.material_name}</p><p className="mt-1 text-sm text-slate-600">{entry.operation_type.replace(/_/g, ' ')}: {entry.before_value} → {entry.after_value}</p></div><p className="whitespace-nowrap text-xs text-slate-500">{formatDate(entry.created_at)}</p></div><p className="mt-2 text-xs text-slate-500">{entry.reason} · by {entry.username}</p></div>)}</div> : <EmptyState title="No inventory activity" description="Quantity and movement updates will appear here once recorded." />
          ) : <div className="grid gap-3 p-6 sm:grid-cols-2"><Link className="rounded-xl border border-slate-200 p-4 transition hover:border-teal-300 hover:bg-teal-50" to="/inventory"><p className="font-semibold text-slate-900">Explore inventory</p><p className="mt-1 text-sm text-slate-600">Find material availability and storage details.</p></Link><Link className="rounded-xl border border-slate-200 p-4 transition hover:border-teal-300 hover:bg-teal-50" to="/requests"><p className="font-semibold text-slate-900">Manage requests</p><p className="mt-1 text-sm text-slate-600">Review your submitted and approved requests.</p></Link></div>}
        </section>
      </div>
    </section>
  )
}
