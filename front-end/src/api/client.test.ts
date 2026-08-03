import { afterEach, describe, expect, it, vi } from 'vitest'
import { api } from './client'

function response(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('API client', () => {
  it('sends registration data to the existing user endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue(response({ id: 1, username: 'lina', email: 'lina@example.com', role: 'viewer' }))
    vi.stubGlobal('fetch', fetchMock)

    await api.register({ username: 'lina', email: 'lina@example.com', password: 'secret1' })

    expect(fetchMock).toHaveBeenCalledWith('/api/users/register', expect.objectContaining({ method: 'POST' }))
    expect(JSON.parse(fetchMock.mock.calls[0][1].body as string)).toEqual({ username: 'lina', email: 'lina@example.com', password: 'secret1' })
  })

  it('adds a bearer token to protected requests', async () => {
    const fetchMock = vi.fn().mockResolvedValue(response({ id: 1, username: 'lina', email: 'lina@example.com', role: 'viewer' }))
    vi.stubGlobal('fetch', fetchMock)

    await api.getCurrentUser('stored-token')

    expect(fetchMock).toHaveBeenCalledWith('/api/users/me', expect.objectContaining({ headers: expect.objectContaining({ Authorization: 'Bearer stored-token' }) }))
  })

  it('returns the backend detail for failed requests', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({ detail: 'Invalid username or password' }, 401)))

    await expect(api.login({ username: 'lina', password: 'wrong' })).rejects.toEqual(expect.objectContaining({ status: 401, message: 'Invalid username or password' }))
  })
})
