import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { AuthProvider } from '../auth/AuthContext'
import { RegisterPage } from './RegisterPage'

function response(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response
}

describe('RegisterPage', () => {
  it('shows client-side password confirmation validation', async () => {
    const user = userEvent.setup()
    render(<MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><AuthProvider><RegisterPage /></AuthProvider></MemoryRouter>)

    await user.type(screen.getByLabelText('Username'), 'lina')
    await user.type(screen.getByLabelText('Email address'), 'lina@example.com')
    await user.type(screen.getByLabelText('Password'), 'secret1')
    await user.type(screen.getByLabelText('Confirm password'), 'different')
    await user.click(screen.getByRole('button', { name: 'Create account' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Passwords do not match.')
  })

  it('shows an API error when registration is rejected', async () => {
    const user = userEvent.setup()
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({ detail: 'Username or email already exists' }, 409)))
    render(<MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><AuthProvider><RegisterPage /></AuthProvider></MemoryRouter>)

    await user.type(screen.getByLabelText('Username'), 'lina')
    await user.type(screen.getByLabelText('Email address'), 'lina@example.com')
    await user.type(screen.getByLabelText('Password'), 'secret1')
    await user.type(screen.getByLabelText('Confirm password'), 'secret1')
    await user.click(screen.getByRole('button', { name: 'Create account' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Username or email already exists')
  })
})
