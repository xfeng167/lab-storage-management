export type UserRole = 'viewer' | 'staff' | 'admin' | string

export interface User {
  id: number
  username: string
  email: string
  role: UserRole
}

export interface LoginPayload {
  username: string
  password: string
}

export interface RegisterPayload extends LoginPayload {
  email: string
}

export interface LoginResponse {
  user: User
  token: string
}
