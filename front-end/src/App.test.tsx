import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { App } from './App'
import { AuthProvider } from './auth/AuthContext'

const viewer = { id: 7, username: 'mira', email: 'mira@example.com', role: 'viewer', profile_picture: null }
const admin = { id: 1, username: 'admin', email: 'admin@example.com', role: 'admin', profile_picture: null }

function json(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response
}

function renderApp(path = '/account') {
  return render(
    <MemoryRouter initialEntries={[path]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AuthProvider><App /></AuthProvider>
    </MemoryRouter>,
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('application routes', () => {
  it('redirects an anonymous visitor to login', async () => {
    renderApp()
    expect(await screen.findByRole('heading', { name: 'Sign in to your account' })).toBeInTheDocument()
  })

  it('restores a persisted session and signs out', async () => {
    window.localStorage.setItem('lab-storage-management.auth-token', 'valid-token')
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(json(viewer))
      .mockResolvedValueOnce(json({ message: 'Logout received.' }))
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()

    renderApp()
    expect(await screen.findByRole('heading', { name: 'Profile settings' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Sign out' }))

    expect(await screen.findByRole('heading', { name: 'Sign in to your account' })).toBeInTheDocument()
    expect(window.localStorage.getItem('lab-storage-management.auth-token')).toBeNull()
    expect(fetchMock.mock.calls[1][0]).toBe('/api/users/logout')
  })

  it('lets admins load the user directory', async () => {
    window.localStorage.setItem('lab-storage-management.auth-token', 'admin-token')
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce(json(admin))
      .mockResolvedValueOnce(json([admin, viewer])))

    renderApp('/account/users')
    expect(await screen.findByRole('heading', { name: 'User directory' })).toBeInTheDocument()
    expect(await screen.findByText('mira@example.com')).toBeInTheDocument()
  })

  it('clears and restores one previous profile picture', async () => {
    const oldPicture = 'data:image/png;base64,old-picture'
    window.localStorage.setItem('lab-storage-management.auth-token', 'valid-token')
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(json({ ...viewer, profile_picture: oldPicture }))
      .mockResolvedValueOnce(json({ ...viewer, profile_picture: null }))
      .mockResolvedValueOnce(json({ ...viewer, profile_picture: oldPicture }))
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()

    renderApp()

    expect(await screen.findByRole('heading', { name: 'Profile settings' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Clear picture' }))
    await waitFor(() => expect(JSON.parse(fetchMock.mock.calls[1][1].body as string).profile_picture).toBeNull())

    await user.click(screen.getByRole('button', { name: 'Use previous' }))
    await waitFor(() => expect(JSON.parse(fetchMock.mock.calls[2][1].body as string).profile_picture).toBe(oldPicture))
  })

  it('clears an expired session and returns to login', async () => {
    window.localStorage.setItem('lab-storage-management.auth-token', 'expired-token')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json({ detail: 'Invalid or expired token' }, 401)))

    renderApp()
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Sign in to your account' })).toBeInTheDocument())
    expect(window.localStorage.getItem('lab-storage-management.auth-token')).toBeNull()
  })

  it('blocks viewers from staff-only routes', async () => {
    window.localStorage.setItem('lab-storage-management.auth-token', 'viewer-token')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json(viewer)))

    renderApp('/reports')

    expect(await screen.findByRole('heading', { name: 'You do not have permission to view this page.' })).toBeInTheDocument()
  })
})
