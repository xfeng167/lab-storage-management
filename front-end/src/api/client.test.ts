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

  it('serializes material search filters and inventory operations', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response([]))
      .mockResolvedValueOnce(response({ id: 2 }))
    vi.stubGlobal('fetch', fetchMock)

    await api.searchMaterials('stored-token', { qc_status: 'pending', location_id: 4, include_archived: true })
    await api.checkInMaterial('stored-token', 2, 5, 'Received shipment')

    expect(fetchMock.mock.calls[0][0]).toBe('/api/materials/search?qc_status=pending&location_id=4&include_archived=true')
    expect(fetchMock.mock.calls[0][1].headers).toEqual(expect.objectContaining({ Authorization: 'Bearer stored-token' }))
    expect(fetchMock.mock.calls[1][0]).toBe('/api/materials/2/check-in')
    expect(JSON.parse(fetchMock.mock.calls[1][1].body as string)).toEqual({ quantity: 5, reason: 'Received shipment' })
  })

  it('uses request review and audit filter endpoints', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response({ id: 3, status: 'approved' }))
      .mockResolvedValueOnce(response([]))
    vi.stubGlobal('fetch', fetchMock)

    await api.approveOrder('admin-token', 3, 'Approved for use')
    await api.listAuditLogs('admin-token', { user_id: 1, operation_type: 'check_in' })

    expect(fetchMock.mock.calls[0][0]).toBe('/api/orders/3/approve')
    expect(JSON.parse(fetchMock.mock.calls[0][1].body as string)).toEqual({ outcome_notes: 'Approved for use' })
    expect(fetchMock.mock.calls[1][0]).toBe('/api/audit-logs?user_id=1&operation_type=check_in')
  })
})
