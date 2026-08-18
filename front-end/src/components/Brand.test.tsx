import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { Brand } from './Brand'

describe('Brand', () => {
  it('links the Lab Storage brand to the dashboard', () => {
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Brand />
      </MemoryRouter>,
    )

    expect(screen.getByRole('link', { name: 'Lab Storage Management' })).toHaveAttribute('href', '/dashboard')
  })
})
