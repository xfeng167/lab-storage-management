import { act, render, screen, waitFor, within } from '@testing-library/react'
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
    await act(async () => { await user.click(screen.getByRole('button', { name: 'Sign out' })) })

    expect(await screen.findByRole('heading', { name: 'Sign in to your account' })).toBeInTheDocument()
    expect(window.localStorage.getItem('lab-storage-management.auth-token')).toBeNull()
    expect(fetchMock.mock.calls[1][0]).toBe('/api/users/logout')
  })

  it('places the username directly below the account avatar', async () => {
    window.localStorage.setItem('lab-storage-management.auth-token', 'valid-token')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json(viewer)))

    renderApp()

    expect(await screen.findByRole('heading', { name: 'Profile settings' })).toBeInTheDocument()
    const accountIdentity = screen.getByRole('group', { name: 'Account identity' })
    expect(accountIdentity).toHaveClass('flex-col', 'items-center')
    expect(within(accountIdentity).getByRole('link', { name: 'Open account profile' })).toBeInTheDocument()
    expect(within(accountIdentity).getByRole('link', { name: 'mira' })).toBeInTheDocument()
  })

  it('lets admins load the user directory', async () => {
    window.localStorage.setItem('lab-storage-management.auth-token', 'admin-token')
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce(json(admin))
      .mockResolvedValueOnce(json({ items: [admin, viewer], page: 1, size: 25, total: 2, pages: 1 })))

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
    await act(async () => { await user.click(screen.getByRole('button', { name: 'Clear picture' })) })
    await waitFor(() => expect(JSON.parse(fetchMock.mock.calls[1][1].body as string).profile_picture).toBeNull())

    await act(async () => { await user.click(screen.getByRole('button', { name: 'Use previous' })) })
    await waitFor(() => expect(JSON.parse(fetchMock.mock.calls[2][1].body as string).profile_picture).toBe(oldPicture))
  })

  it('changes the password from profile settings and clears the form', async () => {
    window.localStorage.setItem('lab-storage-management.auth-token', 'valid-token')
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(json(viewer))
      .mockResolvedValueOnce(json({ message: 'Password updated successfully.' }))
      .mockResolvedValueOnce(json({ message: 'Logout received.' }))
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()

    renderApp()

    expect(await screen.findByRole('heading', { name: 'Security' })).toBeInTheDocument()
    const accountSettings = screen.getByRole('region', { name: 'Account settings' })
    expect(within(accountSettings).getByRole('heading', { name: 'Profile details' })).toBeInTheDocument()
    expect(within(accountSettings).getByRole('heading', { name: 'Change password' })).toBeInTheDocument()
    expect(within(accountSettings).getByRole('list', { name: 'Password requirements' })).toBeInTheDocument()
    expect(within(accountSettings).getByText('All password fields are required.')).toBeInTheDocument()
    await act(async () => {
      await user.type(screen.getByLabelText('Current password'), 'password123')
      await user.type(screen.getByLabelText('New password'), 'newpassword456')
      await user.type(screen.getByLabelText('Confirm new password'), 'newpassword456')
      await user.click(screen.getByRole('button', { name: 'Update password' }))
    })

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3))
    expect(fetchMock.mock.calls[1][0]).toBe('/api/users/me/password')
    expect(JSON.parse(fetchMock.mock.calls[1][1].body as string)).toEqual({ current_password: 'password123', new_password: 'newpassword456' })
    expect(fetchMock.mock.calls[2][0]).toBe('/api/users/logout')
    expect(await screen.findByRole('heading', { name: 'Sign in to your account' })).toBeInTheDocument()
  })

  it('validates matching password confirmation before calling the API', async () => {
    window.localStorage.setItem('lab-storage-management.auth-token', 'valid-token')
    const fetchMock = vi.fn().mockResolvedValueOnce(json(viewer))
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()

    renderApp()

    expect(await screen.findByRole('heading', { name: 'Security' })).toBeInTheDocument()
    await act(async () => {
      await user.type(screen.getByLabelText('Current password'), 'password123')
      await user.type(screen.getByLabelText('New password'), 'newpassword456')
      await user.type(screen.getByLabelText('Confirm new password'), 'different789')
      await user.click(screen.getByRole('button', { name: 'Update password' }))
    })

    expect(await screen.findByRole('alert')).toHaveTextContent('New passwords do not match.')
    expect(fetchMock).toHaveBeenCalledTimes(1)
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
