import { fireEvent, render, screen } from '@testing-library/react'
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
    render(<MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><AuthProvider><RegisterPage /></AuthProvider></MemoryRouter>)

    fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'lina' } })
    fireEvent.change(screen.getByLabelText('Email address'), { target: { value: 'lina@example.com' } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'secret1' } })
    fireEvent.change(screen.getByLabelText('Confirm password'), { target: { value: 'different' } })
    fireEvent.submit(screen.getByRole('button', { name: 'Create account' }).closest('form')!)

    expect(await screen.findByRole('alert')).toHaveTextContent('Passwords do not match.')
  })

  it('shows an API error when registration is rejected', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({ detail: 'Username or email already exists' }, 409)))
    render(<MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><AuthProvider><RegisterPage /></AuthProvider></MemoryRouter>)

    fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'lina' } })
    fireEvent.change(screen.getByLabelText('Email address'), { target: { value: 'lina@example.com' } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'secret1' } })
    fireEvent.change(screen.getByLabelText('Confirm password'), { target: { value: 'secret1' } })
    fireEvent.submit(screen.getByRole('button', { name: 'Create account' }).closest('form')!)

    expect(await screen.findByRole('alert')).toHaveTextContent('Username or email already exists')
  })
})
