import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { MaterialFormModal } from './MaterialFormModal'

describe('MaterialFormModal units', () => {
  it('stores the selected standard unit in singular form', async () => {
    const onSave = vi.fn(() => new Promise<void>(() => {}))
    const onClose = vi.fn()
    const user = userEvent.setup()

    render(<MaterialFormModal locations={[]} onClose={onClose} onSave={onSave} />)

    await act(async () => {
      await user.type(screen.getByLabelText('Material code'), 'UNIT-TEST-001')
      await user.type(screen.getByPlaceholderText('e.g. Metformin Hydrochloride USP'), 'Unit test material')
      await user.type(screen.getByPlaceholderText('e.g. API, excipient, reagent, packaging component'), 'reagent')
      await user.selectOptions(screen.getByRole('combobox', { name: /Unit/ }), 'vial')
      await user.click(screen.getByRole('button', { name: 'Create material' }))
    })

    await waitFor(() => expect(onSave).toHaveBeenCalledTimes(1))
    expect(onSave).toHaveBeenCalledWith(expect.objectContaining({ unit: 'vial' }))
    expect(onClose).not.toHaveBeenCalled()
  })

  it('retains support for a custom unit', async () => {
    const onSave = vi.fn(() => new Promise<void>(() => {}))
    const user = userEvent.setup()

    render(<MaterialFormModal locations={[]} onClose={vi.fn()} onSave={onSave} />)

    await act(async () => {
      await user.type(screen.getByLabelText('Material code'), 'UNIT-TEST-002')
      await user.type(screen.getByPlaceholderText('e.g. Metformin Hydrochloride USP'), 'Custom unit material')
      await user.type(screen.getByPlaceholderText('e.g. API, excipient, reagent, packaging component'), 'reagent')
      await user.selectOptions(screen.getByRole('combobox', { name: /Unit/ }), 'custom')
      await user.type(screen.getByLabelText('Custom unit'), 'batch')
      await user.click(screen.getByRole('button', { name: 'Create material' }))
    })

    await waitFor(() => expect(onSave).toHaveBeenCalledTimes(1))
    expect(onSave).toHaveBeenCalledWith(expect.objectContaining({ unit: 'batch' }))
  })
})
