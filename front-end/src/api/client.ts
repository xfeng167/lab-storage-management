import type {
  AuditLog,
  AuditSearchParams,
  InventoryActivity,
  Location,
  LocationInventorySummary,
  LocationPayload,
  LoginPayload,
  LoginResponse,
  LowStockMaterial,
  Material,
  MaterialPayload,
  MaterialSearchParams,
  MaterialUpdatePayload,
  Order,
  OrderCreatePayload,
  PendingOrder,
  RegisterPayload,
  User,
} from '../types'

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')
let unauthorizedHandler: (() => void) | undefined

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

interface ApiErrorBody {
  detail?: unknown
}

type QueryValue = string | number | boolean | null | undefined

function getErrorMessage(body: ApiErrorBody | null): string {
  if (typeof body?.detail === 'string') return body.detail
  return 'The request could not be completed. Please try again.'
}

function withQuery(path: string, params: object = {}): string {
  const searchParams = new URLSearchParams()
  Object.entries(params as Record<string, QueryValue>).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') searchParams.set(key, String(value))
  })
  const query = searchParams.toString()
  return query ? `${path}?${query}` : path
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${apiBaseUrl}${path}`, {
      ...init,
      headers: { Accept: 'application/json', ...init.headers },
    })
  } catch {
    throw new ApiError(0, 'Unable to reach the API. Check that the backend service is running.')
  }

  if (!response.ok) {
    let body: ApiErrorBody | null = null
    try {
      body = (await response.json()) as ApiErrorBody
    } catch {
      body = null
    }
    if (response.status === 401) unauthorizedHandler?.()
    throw new ApiError(response.status, getErrorMessage(body))
  }

  return (await response.json()) as T
}

function authenticatedHeaders(token: string): HeadersInit {
  return { Authorization: `Bearer ${token}` }
}

function jsonRequest(method: 'POST' | 'PATCH', body: unknown, token?: string): RequestInit {
  return {
    method,
    body: JSON.stringify(body),
    headers: { 'Content-Type': 'application/json', ...(token ? authenticatedHeaders(token) : {}) },
  }
}

export function setUnauthorizedHandler(handler: (() => void) | undefined): void {
  unauthorizedHandler = handler
}

export const api = {
  register: (payload: RegisterPayload) => request<User>('/users/register', jsonRequest('POST', payload)),
  login: (payload: LoginPayload) => request<LoginResponse>('/users/login', jsonRequest('POST', payload)),
  logout: (token: string) => request<{ message: string }>('/users/logout', jsonRequest('POST', { token })),
  getCurrentUser: (token: string) => request<User>('/users/me', { headers: authenticatedHeaders(token) }),
  listUsers: (token: string) => request<User[]>('/users', { headers: authenticatedHeaders(token) }),

  listMaterials: (token: string) => request<Material[]>('/materials', { headers: authenticatedHeaders(token) }),
  searchMaterials: (token: string, params: MaterialSearchParams) =>
    request<Material[]>(withQuery('/materials/search', params), { headers: authenticatedHeaders(token) }),
  getMaterial: (token: string, materialId: number) => request<Material>(`/materials/${materialId}`, { headers: authenticatedHeaders(token) }),
  createMaterial: (token: string, payload: MaterialPayload) => request<Material>('/materials', jsonRequest('POST', payload, token)),
  updateMaterial: (token: string, materialId: number, payload: MaterialUpdatePayload) =>
    request<Material>(`/materials/${materialId}`, jsonRequest('PATCH', payload, token)),
  archiveMaterial: (token: string, materialId: number, reason: string) =>
    request<{ message: string }>(withQuery(`/materials/${materialId}/archive`, { reason }), { method: 'POST', headers: authenticatedHeaders(token) }),
  restoreMaterial: (token: string, materialId: number) =>
    request<{ message: string }>(`/materials/${materialId}/restore`, { method: 'POST', headers: authenticatedHeaders(token) }),
  adjustMaterialQuantity: (token: string, materialId: number, quantityAvailable: number, reason: string) =>
    request<Material>(`/materials/${materialId}/adjust-quantity`, jsonRequest('POST', { quantity_available: quantityAvailable, reason }, token)),
  checkInMaterial: (token: string, materialId: number, quantity: number, reason: string) =>
    request<Material>(`/materials/${materialId}/check-in`, jsonRequest('POST', { quantity, reason }, token)),
  checkOutMaterial: (token: string, materialId: number, quantity: number, reason: string) =>
    request<Material>(`/materials/${materialId}/check-out`, jsonRequest('POST', { quantity, reason }, token)),
  moveMaterial: (token: string, materialId: number, locationId: number | null, reason: string) =>
    request<Material>(`/materials/${materialId}/move`, jsonRequest('POST', { location_id: locationId, reason }, token)),

  listLocations: (token: string) => request<Location[]>('/locations', { headers: authenticatedHeaders(token) }),
  getLocation: (token: string, locationId: number) => request<Location>(`/locations/${locationId}`, { headers: authenticatedHeaders(token) }),
  createLocation: (token: string, payload: LocationPayload) => request<Location>('/locations', jsonRequest('POST', payload, token)),
  updateLocation: (token: string, locationId: number, payload: Partial<LocationPayload>) =>
    request<Location>(`/locations/${locationId}`, jsonRequest('PATCH', payload, token)),

  listOrders: (token: string) => request<Order[]>('/orders', { headers: authenticatedHeaders(token) }),
  getOrder: (token: string, orderId: number) => request<Order>(`/orders/${orderId}`, { headers: authenticatedHeaders(token) }),
  createOrder: (token: string, payload: OrderCreatePayload) => request<Order>('/orders', jsonRequest('POST', payload, token)),
  approveOrder: (token: string, orderId: number, outcomeNotes: string | null) =>
    request<Order>(`/orders/${orderId}/approve`, jsonRequest('POST', { outcome_notes: outcomeNotes }, token)),
  rejectOrder: (token: string, orderId: number, outcomeNotes: string | null) =>
    request<Order>(`/orders/${orderId}/reject`, jsonRequest('POST', { outcome_notes: outcomeNotes }, token)),
  fulfillOrder: (token: string, orderId: number, outcomeNotes: string | null) =>
    request<Order>(`/orders/${orderId}/fulfill`, jsonRequest('POST', { outcome_notes: outcomeNotes }, token)),
  cancelOrder: (token: string, orderId: number, outcomeNotes: string | null) =>
    request<Order>(`/orders/${orderId}/cancel`, jsonRequest('POST', { outcome_notes: outcomeNotes }, token)),

  listLowStock: (token: string) => request<LowStockMaterial[]>('/reports/low-stock', { headers: authenticatedHeaders(token) }),
  listPendingOrders: (token: string) => request<PendingOrder[]>('/reports/pending-orders', { headers: authenticatedHeaders(token) }),
  listRecentActivity: (token: string) => request<InventoryActivity[]>('/reports/recent-inventory-activity', { headers: authenticatedHeaders(token) }),
  listMaterialsByLocation: (token: string) => request<LocationInventorySummary[]>('/reports/materials-by-location', { headers: authenticatedHeaders(token) }),
  listAuditLogs: (token: string, params: AuditSearchParams) =>
    request<AuditLog[]>(withQuery('/audit-logs', params), { headers: authenticatedHeaders(token) }),
}
