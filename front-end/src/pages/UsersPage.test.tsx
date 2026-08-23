import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { App } from '../App'
import { AuthProvider } from '../auth/AuthContext'

const admin = { id: 1, username: 'admin', email: 'admin@example.com', role: 'admin', profile_picture: null }
const mira = { id: 2, username: 'mira', email: 'mira@example.com', role: 'viewer' }
const daniel = { id: 3, username: 'daniel', email: 'daniel@example.com', role: 'viewer' }

function json(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response
}

function deferred<T>() {
  let resolve: (value: T) => void
  const promise = new Promise<T>((resolvePromise) => { resolve = resolvePromise })
  return { promise, resolve: resolve! }
}

function renderUsersPage() {
  return render(
    <MemoryRouter initialEntries={['/account/users']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AuthProvider><App /></AuthProvider>
    </MemoryRouter>,
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('UsersPage role updates', () => {
  it('keeps concurrent role changes independent and restores only the failed row', async () => {
    const miraUpdate = deferred<Response>()
    const danielUpdate = deferred<Response>()
    const fetchMock = vi.fn((path: string) => {
      if (path === '/api/users/me') return Promise.resolve(json(admin))
      if (path === '/api/users?page=1&size=25') return Promise.resolve(json({ items: [admin, mira, daniel], page: 1, size: 25, total: 3, pages: 1 }))
      if (path === '/api/users/2/role') return miraUpdate.promise
      if (path === '/api/users/3/role') return danielUpdate.promise
      throw new Error(`Unexpected request: ${path}`)
    })
    window.localStorage.setItem('lab-storage-management.auth-token', 'admin-token')
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()

    renderUsersPage()

    await screen.findByText('mira@example.com')
    await user.selectOptions(screen.getByLabelText('Role for mira'), 'staff')
    await user.selectOptions(screen.getByLabelText('Role for daniel'), 'staff')

    expect(screen.getByLabelText('Role for mira')).toBeDisabled()
    expect(screen.getByLabelText('Role for daniel')).toBeDisabled()

    await act(async () => { danielUpdate.resolve(json({ ...daniel, role: 'staff' })) })
    await waitFor(() => expect(screen.getByLabelText('Role for daniel')).toHaveValue('staff'))
    expect(screen.getByLabelText('Role for mira')).toHaveValue('staff')

    await act(async () => {
      miraUpdate.resolve(json({ error: { code: 'USER_ROLE_UPDATE_BUSY', message: 'Retry Mira only.' } }, 409))
    })

    await waitFor(() => expect(screen.getByLabelText('Role for mira')).toHaveValue('viewer'))
    expect(screen.getByLabelText('Role for daniel')).toHaveValue('staff')
    expect(screen.getByRole('alert')).toHaveTextContent('Retry Mira only.')
    expect(fetchMock.mock.calls.filter(([path]) => path === '/api/users?page=1&size=25')).toHaveLength(1)
  })
})
