export type UserRole = 'viewer' | 'staff' | 'admin' | string

export interface User {
  id: number
  username: string
  email: string
  role: UserRole
  profile_picture: string | null
}

export interface LoginPayload {
  username: string
  password: string
}

export interface RegisterPayload extends LoginPayload {
  email: string
}

export interface UserProfilePayload {
  username: string
  email: string
  profile_picture: string | null
}

export interface LoginResponse {
  user: User
  token: string
}

export interface Location {
  id: number
  name: string
  location_type: string
  parent_location_id: number | null
  temperature_zone: string | null
  description: string | null
  created_at: string | null
  updated_at: string | null
}

export interface LocationPayload {
  name: string
  location_type: string
  parent_location_id: number | null
  temperature_zone: string | null
  description: string | null
}

export interface Material {
  id: number
  material_code: string
  material_name: string
  material_type: string
  description: string | null
  source: string | null
  quantity_available: number
  quantity_reserved: number
  unit: string
  minimum_quantity: number
  availability_status: string
  qc_status: string
  storage_condition: string | null
  location_id: number | null
  is_archived: boolean
  archived_at: string | null
  archived_by_user_id: number | null
  archive_reason: string | null
  created_at: string | null
  updated_at: string | null
}

export interface MaterialPayload {
  material_code: string
  material_name: string
  material_type: string
  description: string
  source: string
  quantity_available: number
  unit: string
  minimum_quantity: number
  qc_status: string
  storage_condition: string
  location_id: number | null
}

export type MaterialUpdatePayload = Partial<Omit<MaterialPayload, 'material_code' | 'quantity_available'>>

export interface MaterialSearchParams {
  keyword?: string
  material_type?: string
  source?: string
  qc_status?: string
  availability_status?: string
  location_id?: number
  low_stock?: boolean
  include_archived?: boolean
}

export interface Order {
  id: number
  requested_by_user_id: number
  material_id: number
  requested_quantity: number
  reserved_quantity: number
  status: string
  request_notes: string | null
  reviewed_by_user_id: number | null
  reviewed_at: string | null
  outcome_notes: string | null
  is_archived: boolean
  archived_at: string | null
  archived_by_user_id: number | null
  archive_reason: string | null
  created_at: string | null
  updated_at: string | null
}

export interface OrderCreatePayload {
  material_id: number
  requested_quantity: number
  request_notes: string | null
}

export interface LowStockMaterial {
  id: number
  material_code: string
  material_name: string
  quantity_available: number
  quantity_reserved: number
  minimum_quantity: number
  unit: string
  location_id: number | null
}

export interface PendingOrder {
  id: number
  requested_by_user_id: number
  requested_by_username: string
  material_id: number
  material_code: string
  material_name: string
  requested_quantity: number
  status: string
  request_notes: string | null
  created_at: string | null
}

export interface InventoryActivity {
  id: number
  user_id: number
  username: string
  material_id: number
  material_code: string
  material_name: string
  operation_type: string
  before_value: string
  after_value: string
  reason: string
  created_at: string | null
}

export interface LocationInventorySummary {
  location_id: number | null
  location_name: string
  material_count: number
  total_quantity_available: number
  total_quantity_reserved: number
}

export interface AuditLog {
  id: number
  user_id: number
  material_id: number
  operation_type: string
  before_value: string
  after_value: string
  reason: string
  created_at: string | null
}

export interface AuditSearchParams {
  user_id?: number
  material_id?: number
  operation_type?: string
}

export function isAdmin(user: User | null | undefined): boolean {
  return user?.role === 'admin'
}

export function canManageOperations(user: User | null | undefined): boolean {
  return user?.role === 'admin' || user?.role === 'staff'
}
