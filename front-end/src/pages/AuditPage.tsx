import { useCallback, useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { EmptyState } from '../components/EmptyState'
import { LoadingState } from '../components/LoadingState'
import { PageHeader } from '../components/PageHeader'
import { PaginationControls } from '../components/PaginationControls'
import type { AuditLog, Material, Page, UserDirectoryEntry } from '../types'
import { formatAuditChange, formatDate, humanize } from '../utils/format'

const emptyFilters = { userId: '', materialId: '', operation: '' }

export function AuditPage() {
  const { token } = useAuth()
  const [logs, setLogs] = useState<AuditLog[] | null>(null)
  const [resultPage, setResultPage] = useState<Page<AuditLog> | null>(null)
  const [page, setPage] = useState(1)
  const [users, setUsers] = useState<UserDirectoryEntry[]>([])
  const [materials, setMaterials] = useState<Material[]>([])
  const [filters, setFilters] = useState(emptyFilters)
  const [appliedFilters, setAppliedFilters] = useState(emptyFilters)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!token) return
    setError(null)
    try {
      const [logResult, userResult, materialResult] = await Promise.all([
        api.listAuditLogs(token, {
          user_id: appliedFilters.userId ? Number(appliedFilters.userId) : undefined,
          material_id: appliedFilters.materialId ? Number(appliedFilters.materialId) : undefined,
          operation_type: appliedFilters.operation || undefined,
          page,
          size: 25,
        }),
        api.listAllUsers(token),
        api.listAllMaterials(token, { include_archived: true }),
      ])
      setLogs(logResult.items)
      setResultPage(logResult)
      setUsers(userResult)
      setMaterials(materialResult)
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Unable to load the audit log.')
    }
  }, [appliedFilters, page, token])

  useEffect(() => { void load() }, [load])
  const userNames = useMemo(() => new Map(users.map((user) => [user.id, user.username])), [users])
  const materialNames = useMemo(() => new Map(materials.map((material) => [material.id, `${material.material_name} (${material.material_code})`])), [materials])

  if (!logs && !error) return <LoadingState label="Loading audit records…" />

  const applyFilters = () => { setPage(1); setAppliedFilters(filters) }
  const resetFilters = () => { setFilters(emptyFilters); setPage(1); setAppliedFilters(emptyFilters) }

  return (
    <section>
      <PageHeader eyebrow="Administration" title="Inventory and order audit log" description="Review immutable inventory, material archive, and order transition records." actions={<button className="button-secondary" onClick={() => void load()}>Refresh</button>} />
      {error && <p className="alert-error mt-8" role="alert">{error}</p>}
      <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-5 shadow-panel">
        <div className="grid gap-4 md:grid-cols-4">
          <label className="field-label" htmlFor="audit-user">User
            <select id="audit-user" className="field-select" value={filters.userId} onChange={(event) => setFilters((current) => ({ ...current, userId: event.target.value }))}>
              <option value="">All users</option>
              {users.map((user) => <option key={user.id} value={user.id}>{user.username}</option>)}
            </select>
          </label>
          <label className="field-label" htmlFor="audit-material">Material
            <select id="audit-material" className="field-select" value={filters.materialId} onChange={(event) => setFilters((current) => ({ ...current, materialId: event.target.value }))}>
              <option value="">All materials</option>
              {materials.map((material) => <option key={material.id} value={material.id}>{material.material_code} · {material.material_name}</option>)}
            </select>
          </label>
          <label className="field-label" htmlFor="audit-operation">Operation
            <select id="audit-operation" className="field-select" value={filters.operation} onChange={(event) => setFilters((current) => ({ ...current, operation: event.target.value }))}>
              <option value="">All operations</option>
              <option value="adjust_quantity">Adjust quantity</option>
              <option value="check_in">Check in</option>
              <option value="check_out">Check out</option>
              <option value="move">Move</option>
              <option value="order_reservation_created">Order approved</option>
              <option value="order_fulfilled">Order fulfilled</option>
              <option value="order_reservation_released">Order cancellation</option>
              <option value="order_archived">Order archived</option>
              <option value="archive_material">Material archived</option>
              <option value="restore_material">Material restored</option>
            </select>
          </label>
          <div className="flex items-end gap-3">
            <button className="button-primary flex-1" onClick={applyFilters}>Apply filters</button>
            <button className="button-secondary" onClick={resetFilters}>Reset</button>
          </div>
        </div>
      </section>
      <section className="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-panel">
        {logs?.length ? (
          <div className="overflow-x-auto"><table className="min-w-full divide-y divide-slate-200"><thead className="bg-slate-50"><tr><th className="table-heading">When</th><th className="table-heading">Material</th><th className="table-heading">Operation</th><th className="table-heading">Change</th><th className="table-heading">Reason</th><th className="table-heading">User</th></tr></thead><tbody className="divide-y divide-slate-100">{logs.map((log) => <tr key={log.id}><td className="table-cell whitespace-nowrap text-xs">{formatDate(log.created_at)}</td><td className="table-cell font-medium text-slate-900">{materialNames.get(log.material_id) ?? `Material #${log.material_id}`}</td><td className="table-cell">{humanize(log.operation_type)}</td><td className="table-cell text-xs"><p>{formatAuditChange(log.before_value, log.after_value)}</p><details className="mt-1 text-slate-500"><summary className="cursor-pointer">Technical details</summary><code className="mt-1 block whitespace-pre-wrap break-all">{log.before_value} → {log.after_value}</code></details></td><td className="table-cell"><p className="max-w-xl whitespace-normal break-words">{log.reason}</p></td><td className="table-cell">{userNames.get(log.user_id) ?? `User #${log.user_id}`}</td></tr>)}</tbody></table></div>
        ) : <EmptyState title="No matching audit records" description="Change filters or record an audited operation to create an entry." />}
        {resultPage && <PaginationControls page={resultPage.page} pages={resultPage.pages} total={resultPage.total} label="audit records" onPageChange={setPage} />}
      </section>
    </section>
  )
}
