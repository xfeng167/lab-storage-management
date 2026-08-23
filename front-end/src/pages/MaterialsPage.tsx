import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { EmptyState } from '../components/EmptyState'
import { LoadingState } from '../components/LoadingState'
import { MaterialFormModal } from '../components/MaterialFormModal'
import { PageHeader } from '../components/PageHeader'
import { PaginationControls } from '../components/PaginationControls'
import { StatusBadge } from '../components/StatusBadge'
import { canManageOperations, isAdmin, type Location, type Material, type MaterialPayload, type MaterialSearchParams, type MaterialUpdatePayload, type Page } from '../types'
import { formatDate, quantityLabel } from '../utils/format'

interface MaterialFilters {
  keyword: string
  material_type: string
  qc_status: string
  availability_status: string
  location_id: string
  include_archived: boolean
}

const emptyFilters: MaterialFilters = { keyword: '', material_type: '', qc_status: '', availability_status: '', location_id: '', include_archived: false }

function filtersFromSearchParams(searchParams: URLSearchParams): MaterialFilters {
  return {
    keyword: searchParams.get('keyword') ?? '',
    material_type: searchParams.get('material_type') ?? '',
    qc_status: searchParams.get('qc_status') ?? '',
    availability_status: searchParams.get('availability_status') ?? '',
    location_id: searchParams.get('location_id') ?? '',
    include_archived: searchParams.get('include_archived') === 'true',
  }
}

function searchParamsFromFilters(filters: MaterialFilters, adminAccess: boolean): URLSearchParams {
  const searchParams = new URLSearchParams()
  if (filters.keyword.trim()) searchParams.set('keyword', filters.keyword.trim())
  if (filters.material_type) searchParams.set('material_type', filters.material_type)
  if (filters.qc_status) searchParams.set('qc_status', filters.qc_status)
  if (filters.availability_status) searchParams.set('availability_status', filters.availability_status)
  if (filters.location_id) searchParams.set('location_id', filters.location_id)
  if (adminAccess && filters.include_archived) searchParams.set('include_archived', 'true')
  return searchParams
}

function materialSearchParamsFromFilters(filters: MaterialFilters, adminAccess: boolean): MaterialSearchParams | undefined {
  const params: MaterialSearchParams = {
    keyword: filters.keyword.trim() || undefined,
    material_type: filters.material_type || undefined,
    qc_status: filters.qc_status || undefined,
    availability_status: filters.availability_status || undefined,
    location_id: filters.location_id ? Number(filters.location_id) : undefined,
    include_archived: adminAccess ? filters.include_archived : undefined,
  }
  return Object.values(params).some((value) => value !== undefined && value !== false) ? params : undefined
}

function directoryTitle(searchParams: URLSearchParams): string {
  if (searchParams.get('scope') === 'active') return 'Active materials'
  if (searchParams.get('availability_status') === 'available') return 'Total on-hand materials'
  if (searchParams.get('availability_status') === 'low_stock') return 'Low-stock items'
  return 'Materials catalogue'
}

function directoryDescription(searchParams: URLSearchParams, count: number): string {
  const materialLabel = count === 1 ? 'material' : 'materials'
  if (searchParams.get('scope') === 'active') return `Showing ${count} active ${materialLabel} from the overview count.`
  if (searchParams.get('availability_status') === 'available') return `Showing ${count} available ${materialLabel} with on-hand quantity.`
  if (searchParams.get('availability_status') === 'low_stock') return `Showing ${count} low-stock ${materialLabel} at or below minimum quantity.`
  return `Showing ${count} ${materialLabel} in the current catalogue view.`
}

export function MaterialsPage() {
  const { token, user } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const [materials, setMaterials] = useState<Material[] | null>(null)
  const [resultPage, setResultPage] = useState<Page<Material> | null>(null)
  const [page, setPage] = useState(1)
  const [filterOptionMaterials, setFilterOptionMaterials] = useState<Material[]>([])
  const [locations, setLocations] = useState<Location[]>([])
  const [error, setError] = useState<string | null>(null)
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [filters, setFilters] = useState<MaterialFilters>(() => filtersFromSearchParams(searchParams))
  const staffAccess = canManageOperations(user)
  const adminAccess = isAdmin(user)

  const load = useCallback(async (searchParams?: MaterialSearchParams, requestedPage = page) => {
    if (!token) return
    setError(null)
    try {
      const [materialResult, optionMaterialResult, locationResult] = await Promise.all([
        searchParams ? api.searchMaterials(token, { ...searchParams, page: requestedPage, size: 25 }) : api.listMaterials(token, { page: requestedPage, size: 25 }),
        api.listAllMaterials(token),
        api.listAllLocations(token),
      ])
      setMaterials(materialResult.items)
      setResultPage(materialResult)
      setFilterOptionMaterials(optionMaterialResult)
      setLocations(locationResult)
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Unable to load inventory.')
    }
  }, [page, token])

  useEffect(() => {
    const nextFilters = filtersFromSearchParams(searchParams)
    setFilters(nextFilters)
    void load(materialSearchParamsFromFilters(nextFilters, adminAccess), page)
  }, [adminAccess, load, page, searchParams])

  const locationNames = useMemo(() => new Map(locations.map((location) => [location.id, location.name])), [locations])
  const materialTypes = useMemo(() => [...new Set(filterOptionMaterials.map((material) => material.material_type))].sort(), [filterOptionMaterials])
  const currentDirectoryTitle = useMemo(() => directoryTitle(searchParams), [searchParams])
  const currentDirectoryDescription = useMemo(() => directoryDescription(searchParams, resultPage?.total ?? 0), [resultPage?.total, searchParams])

  function applyFilters() {
    setPage(1)
    setSearchParams(searchParamsFromFilters(filters, adminAccess))
  }

  function resetFilters() {
    setPage(1)
    setFilters(emptyFilters)
    setSearchParams({})
  }

  async function createMaterial(payload: MaterialPayload | MaterialUpdatePayload) {
    if (!token) return
    await api.createMaterial(token, payload as MaterialPayload)
    await load(undefined, page)
  }

  if (!materials && !error) return <LoadingState label="Loading inventory…" />

  return (
    <section>
      <PageHeader eyebrow="Inventory" title={currentDirectoryTitle} description="Search active lab materials, review their storage context, and monitor available quantities." actions={staffAccess ? <button className="button-primary" onClick={() => setIsCreateOpen(true)}>Add material</button> : undefined} />
      {error && <p className="alert-error mt-8" role="alert">{error}</p>}
      <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-5 shadow-panel">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
          <label className="field-label" htmlFor="filter-keyword">Search
            <input id="filter-keyword" className="field-input" placeholder="Name, code, or description" value={filters.keyword} onChange={(event) => setFilters((current) => ({ ...current, keyword: event.target.value }))} onKeyDown={(event) => { if (event.key === 'Enter') applyFilters() }} />
          </label>
          <label className="field-label" htmlFor="filter-type">Material type
            <select id="filter-type" className="field-select" value={filters.material_type} onChange={(event) => setFilters((current) => ({ ...current, material_type: event.target.value }))}><option value="">All types</option>{materialTypes.map((type) => <option key={type} value={type}>{type}</option>)}</select>
          </label>
          <label className="field-label" htmlFor="filter-qc">QC status
            <select id="filter-qc" className="field-select" value={filters.qc_status} onChange={(event) => setFilters((current) => ({ ...current, qc_status: event.target.value }))}><option value="">All statuses</option><option value="pending">Pending</option><option value="passed">Passed</option><option value="failed">Failed</option></select>
          </label>
          <label className="field-label" htmlFor="filter-availability">Availability
            <select id="filter-availability" className="field-select" value={filters.availability_status} onChange={(event) => setFilters((current) => ({ ...current, availability_status: event.target.value }))}><option value="">All availability</option><option value="available">Available</option><option value="unavailable">Unavailable</option><option value="low_stock">Low stock</option></select>
          </label>
          <label className="field-label" htmlFor="filter-location">Location
            <select id="filter-location" className="field-select" value={filters.location_id} onChange={(event) => setFilters((current) => ({ ...current, location_id: event.target.value }))}><option value="">All locations</option>{locations.map((location) => <option key={location.id} value={location.id}>{location.name}</option>)}</select>
          </label>
          <div className="flex items-end gap-3"><button type="button" className="button-primary flex-1" onClick={applyFilters}>Apply filters</button><button type="button" className="button-secondary" onClick={resetFilters}>Reset</button></div>
        </div>
        {adminAccess && <label className="mt-4 inline-flex items-center gap-2 text-sm font-medium text-slate-700"><input type="checkbox" className="h-4 w-4 rounded border-slate-300 text-lab-700 focus:ring-teal-500" checked={filters.include_archived} onChange={(event) => setFilters((current) => ({ ...current, include_archived: event.target.checked }))} /> Include archived materials</label>}
      </section>
      <section className="mt-6 rounded-2xl border border-teal-200 bg-teal-50 px-5 py-4 text-sm text-teal-900">
        <p className="font-semibold">{currentDirectoryTitle}</p>
        <p className="mt-1">{currentDirectoryDescription}</p>
      </section>
      <section className="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-panel">
        {materials?.length ? <div className="overflow-x-auto"><table className="min-w-full divide-y divide-slate-200"><thead className="bg-slate-50"><tr><th className="table-heading">#</th><th className="table-heading">Material</th><th className="table-heading">Quantity</th><th className="table-heading">QC</th><th className="table-heading">Location</th><th className="table-heading">Updated</th><th className="table-heading"><span className="sr-only">Open</span></th></tr></thead><tbody className="divide-y divide-slate-100">{materials.map((material, index) => <tr key={material.id} className="transition hover:bg-slate-50"><td className="table-cell whitespace-nowrap font-mono text-xs text-slate-500">{((resultPage?.page ?? 1) - 1) * (resultPage?.size ?? 25) + index + 1}</td><td className="table-cell"><p className="font-semibold text-slate-900">{material.material_name}</p><p className="mt-1 text-xs text-slate-500">{material.material_code} · {material.material_type}{material.is_archived ? ' · archived' : ''}</p></td><td className="table-cell"><p className={material.availability_status !== 'available' ? 'font-semibold text-amber-700' : 'font-semibold text-slate-900'}>{quantityLabel(material.quantity_available, material.unit)}</p><p className="mt-1 text-xs text-slate-500">{quantityLabel(material.quantity_reserved, material.unit)} reserved · min {quantityLabel(material.minimum_quantity, material.unit)}</p></td><td className="table-cell"><StatusBadge value={material.qc_status} kind="qc" /></td><td className="table-cell">{locationNames.get(material.location_id ?? -1) ?? 'Unassigned'}</td><td className="table-cell whitespace-nowrap text-xs">{formatDate(material.updated_at)}</td><td className="table-cell text-right"><Link className="link" to={`/inventory/${material.id}`}>Open</Link></td></tr>)}</tbody></table></div> : <EmptyState title="No materials found" description="Try clearing filters or add a material to begin building the catalogue." action={staffAccess ? <button className="button-primary" onClick={() => setIsCreateOpen(true)}>Add material</button> : undefined} />}
        {resultPage && <PaginationControls page={resultPage.page} pages={resultPage.pages} total={resultPage.total} label="materials" onPageChange={setPage} />}
      </section>
      {isCreateOpen && <MaterialFormModal locations={locations} onClose={() => setIsCreateOpen(false)} onSave={createMaterial} />}
    </section>
  )
}
