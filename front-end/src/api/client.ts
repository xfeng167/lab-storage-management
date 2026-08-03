import type { LoginPayload, LoginResponse, RegisterPayload, User } from '../types'

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')

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

function getErrorMessage(body: ApiErrorBody | null): string {
  if (typeof body?.detail === 'string') {
    return body.detail
  }

  return 'The request could not be completed. Please try again.'
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers: {
      Accept: 'application/json',
      ...init.headers,
    },
  })

  if (!response.ok) {
    let body: ApiErrorBody | null = null
    try {
      body = (await response.json()) as ApiErrorBody
    } catch {
      body = null
    }
    throw new ApiError(response.status, getErrorMessage(body))
  }

  return (await response.json()) as T
}

function jsonRequest(method: 'POST', body: unknown, token?: string): RequestInit {
  return {
    method,
    body: JSON.stringify(body),
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  }
}

export const api = {
  register: (payload: RegisterPayload) => request<User>('/users/register', jsonRequest('POST', payload)),
  login: (payload: LoginPayload) => request<LoginResponse>('/users/login', jsonRequest('POST', payload)),
  logout: (token: string) => request<{ message: string }>('/users/logout', jsonRequest('POST', { token })),
  getCurrentUser: (token: string) =>
    request<User>('/users/me', { headers: { Authorization: `Bearer ${token}` } }),
  listUsers: (token: string) =>
    request<User[]>('/users', { headers: { Authorization: `Bearer ${token}` } }),
}
