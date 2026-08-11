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
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'secret123' } })
    fireEvent.change(screen.getByLabelText('Confirm password'), { target: { value: 'different' } })
    fireEvent.submit(screen.getByRole('button', { name: 'Create account' }).closest('form')!)

    expect(await screen.findByRole('alert')).toHaveTextContent('Passwords do not match.')
  })

  it('shows an API error when registration is rejected', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({ detail: 'Username or email already exists' }, 409)))
    render(<MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><AuthProvider><RegisterPage /></AuthProvider></MemoryRouter>)

    fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'lina' } })
    fireEvent.change(screen.getByLabelText('Email address'), { target: { value: 'lina@example.com' } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'secret123' } })
    fireEvent.change(screen.getByLabelText('Confirm password'), { target: { value: 'secret123' } })
    fireEvent.submit(screen.getByRole('button', { name: 'Create account' }).closest('form')!)

    expect(await screen.findByRole('alert')).toHaveTextContent('Username or email already exists')
  })

  it('shows username and password policy validation', async () => {
    render(<MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><AuthProvider><RegisterPage /></AuthProvider></MemoryRouter>)

    fireEvent.change(screen.getByLabelText('Username'), { target: { value: '1bad' } })
    fireEvent.change(screen.getByLabelText('Email address'), { target: { value: 'lina@example.com' } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'secret123' } })
    fireEvent.change(screen.getByLabelText('Confirm password'), { target: { value: 'secret123' } })
    fireEvent.submit(screen.getByRole('button', { name: 'Create account' }).closest('form')!)

    expect(await screen.findByRole('alert')).toHaveTextContent('Username must be 3-30 characters')

    fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'lina_user' } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'password' } })
    fireEvent.change(screen.getByLabelText('Confirm password'), { target: { value: 'password' } })
    fireEvent.submit(screen.getByRole('button', { name: 'Create account' }).closest('form')!)

    expect(await screen.findByRole('alert')).toHaveTextContent('Password must include at least one letter and one number.')
  })
})
