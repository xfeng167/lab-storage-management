import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { ApiError, api, setUnauthorizedHandler } from '../api/client'
import type { LoginPayload, RegisterPayload, User } from '../types'
import { clearToken, readToken, saveToken } from './storage'

type AuthStatus = 'loading' | 'authenticated' | 'anonymous' | 'unavailable'

interface AuthContextValue {
  status: AuthStatus
  user: User | null
  token: string | null
  error: string | null
  login: (payload: LoginPayload) => Promise<void>
  register: (payload: RegisterPayload) => Promise<void>
  logout: () => Promise<void>
  retrySession: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

function getMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Unable to reach the service. Please try again.'
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>('loading')
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const expireSession = useCallback(() => {
    clearToken()
    setToken(null)
    setUser(null)
    setStatus('anonymous')
    setError('Your session has expired. Please sign in again.')
  }, [])

  useEffect(() => {
    setUnauthorizedHandler(expireSession)
    return () => setUnauthorizedHandler(undefined)
  }, [expireSession])

  const restoreSession = useCallback(async () => {
    const storedToken = readToken()
    if (!storedToken) {
      setToken(null)
      setUser(null)
      setError(null)
      setStatus('anonymous')
      return
    }

    setStatus('loading')
    setError(null)
    try {
      const currentUser = await api.getCurrentUser(storedToken)
      setToken(storedToken)
      setUser(currentUser)
      setStatus('authenticated')
    } catch (caughtError) {
      if (caughtError instanceof ApiError && caughtError.status === 401) {
        expireSession()
        return
      }

      setToken(storedToken)
      setUser(null)
      setStatus('unavailable')
      setError(getMessage(caughtError))
    }
  }, [expireSession])

  useEffect(() => {
    void restoreSession()
  }, [restoreSession])

  const login = useCallback(async (payload: LoginPayload) => {
    const result = await api.login(payload)
    saveToken(result.token)
    setToken(result.token)
    setUser(result.user)
    setError(null)
    setStatus('authenticated')
  }, [])

  const register = useCallback(async (payload: RegisterPayload) => {
    await api.register(payload)
  }, [])

  const logout = useCallback(async () => {
    const currentToken = token ?? readToken()
    try {
      if (currentToken) {
        await api.logout(currentToken)
      }
    } catch {
      return
    } finally {
      clearToken()
      setToken(null)
      setUser(null)
      setError(null)
      setStatus('anonymous')
    }
  }, [token])

  const value = useMemo<AuthContextValue>(
    () => ({ status, user, token, error, login, register, logout, retrySession: restoreSession }),
    [error, login, logout, register, restoreSession, status, token, user],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
