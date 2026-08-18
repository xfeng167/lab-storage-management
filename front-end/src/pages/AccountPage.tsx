import { ChangeEvent, FormEvent, useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'

interface ProfileForm {
  username: string
  email: string
  profile_picture: string | null
}

interface PasswordForm {
  currentPassword: string
  newPassword: string
  confirmPassword: string
}

const usernamePattern = /^[A-Za-z][A-Za-z0-9_]{2,29}$/
const emailPattern = /^\S+@\S+\.\S+$/

function formatRole(role: string): string {
  return role.charAt(0).toUpperCase() + role.slice(1)
}

function initials(username: string): string {
  return username.slice(0, 2).toUpperCase()
}

function validate(form: ProfileForm): string | null {
  const username = form.username.trim()
  const email = form.email.trim()
  if (!usernamePattern.test(username)) return 'Username must be 3-30 characters, start with a letter, and use only letters, numbers, or underscores.'
  if (!emailPattern.test(email) || email.length > 255) return 'Enter a valid email address up to 255 characters.'
  if (form.profile_picture && form.profile_picture.length > 500_000) return 'Profile picture is too large.'
  return null
}

function validatePassword(form: PasswordForm): string | null {
  if (!form.currentPassword) return 'Enter your current password.'
  if (form.newPassword.length < 8 || form.newPassword.length > 72) return 'New password must be 8-72 characters.'
  if (!/[A-Za-z]/.test(form.newPassword) || !/\d/.test(form.newPassword)) return 'New password must include at least one letter and one number.'
  if (form.newPassword === form.currentPassword) return 'New password must be different from your current password.'
  if (form.newPassword !== form.confirmPassword) return 'New passwords do not match.'
  return null
}

function readImageFile(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result))
    reader.onerror = () => reject(new Error('Unable to read profile picture.'))
    reader.readAsDataURL(file)
  })
}

export function AccountPage() {
  const { user, token, updateProfile, logout } = useAuth()
  const [form, setForm] = useState<ProfileForm>({ username: '', email: '', profile_picture: null })
  const [passwordForm, setPasswordForm] = useState<PasswordForm>({ currentPassword: '', newPassword: '', confirmPassword: '' })
  const [previousPicture, setPreviousPicture] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [passwordError, setPasswordError] = useState<string | null>(null)
  const [passwordNotice, setPasswordNotice] = useState<string | null>(null)
  const [isChangingPassword, setIsChangingPassword] = useState(false)
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  useEffect(() => {
    if (!user) return
    setForm({ username: user.username, email: user.email, profile_picture: user.profile_picture ?? null })
  }, [user])

  if (!user) return null

  function update(name: keyof ProfileForm, value: string | null) {
    setForm((current) => ({ ...current, [name]: value }))
  }

  function rememberPreviousPicture(candidate: string | null, nextPicture: string | null) {
    if (candidate && candidate !== nextPicture) setPreviousPicture(candidate)
  }

  function resetPictureInput() {
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  async function handlePictureChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (!file) return
    if (!file.type.startsWith('image/')) {
      setError('Choose an image file for your profile picture.')
      return
    }
    if (file.size > 350_000) {
      setError('Choose an image under 350 KB.')
      return
    }

    try {
      setError(null)
      const nextPicture = await readImageFile(file)
      rememberPreviousPicture(form.profile_picture, nextPicture)
      update('profile_picture', nextPicture)
      setNotice('New picture selected. Save profile to apply it.')
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Unable to read profile picture.')
    }
  }

  async function saveProfile(profilePicture = form.profile_picture) {
    const nextForm = { ...form, profile_picture: profilePicture }
    const validationError = validate(nextForm)
    if (validationError) {
      setError(validationError)
      return
    }

    setIsSaving(true)
    setError(null)
    setNotice(null)
    try {
      await updateProfile({
        username: nextForm.username.trim(),
        email: nextForm.email.trim(),
        profile_picture: nextForm.profile_picture,
      })
      setNotice(profilePicture ? 'Profile updated.' : 'Profile picture cleared.')
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Unable to update profile.')
    } finally {
      setIsSaving(false)
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    await saveProfile()
  }

  async function clearPicture() {
    rememberPreviousPicture(form.profile_picture, null)
    update('profile_picture', null)
    resetPictureInput()
    await saveProfile(null)
  }

  async function restorePreviousPicture() {
    if (!previousPicture) return
    rememberPreviousPicture(form.profile_picture, previousPicture)
    update('profile_picture', previousPicture)
    resetPictureInput()
    await saveProfile(previousPicture)
  }

  function updatePassword(name: keyof PasswordForm, value: string) {
    setPasswordForm((current) => ({ ...current, [name]: value }))
  }

  async function submitPassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const validationError = validatePassword(passwordForm)
    if (validationError) {
      setPasswordError(validationError)
      setPasswordNotice(null)
      return
    }
    if (!token) {
      setPasswordError('You must be signed in to update your password.')
      return
    }

    setIsChangingPassword(true)
    setPasswordError(null)
    setPasswordNotice(null)
    try {
      const result = await api.changePassword(token, {
        current_password: passwordForm.currentPassword,
        new_password: passwordForm.newPassword,
      })
      setPasswordForm({ currentPassword: '', newPassword: '', confirmPassword: '' })
      setPasswordNotice(result.message)
      await logout()
    } catch (caughtError) {
      setPasswordError(caughtError instanceof Error ? caughtError.message : 'Unable to update password.')
    } finally {
      setIsChangingPassword(false)
    }
  }

  return (
    <div className="mx-auto max-w-5xl">
      <p className="eyebrow">Your account</p>
      <div className="mt-3">
        <h1 className="text-3xl font-semibold tracking-tight text-slate-950">Profile settings</h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">View your account, update profile details, and manage security in one place.</p>
      </div>

      {notice && <p className="alert-info mt-6" role="status">{notice}</p>}
      {error && <p className="alert-error mt-6" role="alert">{error}</p>}

      <section className="mt-8 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-panel" aria-labelledby="account-settings-heading">
        <header className="flex flex-col gap-4 border-b border-slate-200 px-6 py-5 sm:flex-row sm:items-center sm:justify-between lg:px-8">
          <div>
            <p className="eyebrow">Account workspace</p>
            <h2 id="account-settings-heading" className="mt-1 text-xl font-semibold text-slate-950">Account settings</h2>
          </div>
          <span className="inline-flex w-fit rounded-full bg-lab-50 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-lab-800">{formatRole(user.role)}</span>
        </header>

        <div className="grid lg:grid-cols-[0.78fr_1.22fr]">
          <aside className="border-b border-slate-200 bg-slate-50 p-6 lg:border-b-0 lg:border-r lg:p-8" aria-label="Profile overview">
            <div className="flex flex-col items-center text-center">
              <div className="grid h-28 w-28 place-items-center overflow-hidden rounded-2xl bg-lab-50 text-3xl font-semibold text-lab-800 ring-1 ring-slate-200">
                {form.profile_picture ? <img className="h-full w-full object-cover" src={form.profile_picture} alt={`${form.username || user.username} profile`} /> : <span>{initials(form.username || user.username)}</span>}
              </div>
              <h3 className="mt-4 text-xl font-semibold text-slate-950">{form.username || user.username}</h3>
              <p className="mt-1 break-all text-sm text-slate-500">{form.email || user.email}</p>
            </div>

            <div className="mt-5">
              <input ref={fileInputRef} id="profile-picture" className="sr-only" type="file" accept="image/*" onChange={(event) => void handlePictureChange(event)} />
              <div className="flex flex-wrap justify-center gap-2">
                <label className="inline-flex cursor-pointer items-center justify-center rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-100 focus-within:ring-4 focus-within:ring-slate-100" htmlFor="profile-picture">Choose picture</label>
                <button type="button" aria-label="Clear picture" className="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-100 focus:outline-none focus:ring-4 focus:ring-slate-100" onClick={() => void clearPicture()} disabled={isSaving || !form.profile_picture}>Clear</button>
                <button type="button" className="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-100 focus:outline-none focus:ring-4 focus:ring-slate-100" onClick={() => void restorePreviousPicture()} disabled={isSaving || !previousPicture || previousPicture === form.profile_picture}>Use previous</button>
              </div>
              <p className="mt-2 text-center text-xs leading-5 text-slate-500">Upload an image under 350 KB, then save your profile.</p>
              {previousPicture && previousPicture !== form.profile_picture && (
                <div className="mt-3 flex items-center gap-3 rounded-lg border border-slate-200 bg-white p-3">
                  <img className="h-10 w-10 rounded-lg object-cover ring-1 ring-slate-200" src={previousPicture} alt="Previous profile" />
                  <p className="text-xs leading-5 text-slate-500">A previous picture is ready to restore.</p>
                </div>
              )}
            </div>

            <dl className="mt-6 divide-y divide-slate-200 border-y border-slate-200">
              <div className="grid grid-cols-2 gap-4 py-3 text-sm">
                <dt className="text-slate-500">Account ID</dt>
                <dd className="text-right font-mono font-semibold text-slate-900">{user.id}</dd>
              </div>
              <div className="grid grid-cols-2 gap-4 py-3 text-sm">
                <dt className="text-slate-500">Role</dt>
                <dd className="text-right font-semibold text-slate-900">{formatRole(user.role)}</dd>
              </div>
              <div className="grid grid-cols-2 gap-4 py-3 text-sm">
                <dt className="text-slate-500">Session</dt>
                <dd className="text-right font-semibold text-slate-900">1 hour</dd>
              </div>
            </dl>
          </aside>

          <form className="p-6 lg:p-8" onSubmit={submit} noValidate aria-labelledby="profile-details-heading">
            <div>
              <h3 id="profile-details-heading" className="text-lg font-semibold text-slate-950">Profile details</h3>
              <p className="mt-1 text-sm leading-6 text-slate-500">Updates are reflected in your profile and the app header.</p>
            </div>
            <div className="mt-6 space-y-5">
            <label className="field-label" htmlFor="profile-username">Username
              <input id="profile-username" className="field-input" minLength={3} maxLength={30} pattern="[A-Za-z][A-Za-z0-9_]{2,29}" value={form.username} onChange={(event) => update('username', event.target.value)} />
              <span className="mt-1 text-xs font-normal text-slate-500">3-30 characters. Start with a letter. Letters, numbers, and underscores only.</span>
            </label>
            <label className="field-label" htmlFor="profile-email">Email address
              <input id="profile-email" className="field-input" type="email" maxLength={255} value={form.email} onChange={(event) => update('email', event.target.value)} />
              <span className="mt-1 text-xs font-normal text-slate-500">Use a valid email address, up to 255 characters.</span>
            </label>
            </div>
            <div className="mt-6 flex justify-end border-t border-slate-100 pt-5">
              <button type="submit" className="button-primary" disabled={isSaving}>{isSaving ? 'Saving...' : 'Save profile'}</button>
            </div>
          </form>
        </div>

        <div className="grid border-t border-slate-200 lg:grid-cols-[0.78fr_1.22fr]">
          <div className="border-b border-slate-200 bg-slate-50 px-6 py-7 lg:border-b-0 lg:border-r lg:px-8 lg:py-8">
            <div className="grid h-11 w-11 place-items-center rounded-xl bg-lab-100 text-lab-800 ring-1 ring-lab-200">
              <svg aria-hidden="true" className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <rect x="5" y="10" width="14" height="10" rx="2" />
                <path d="M8 10V7a4 4 0 0 1 8 0v3" />
                <path d="M12 14v2" />
              </svg>
            </div>
            <p className="eyebrow mt-5">Account security</p>
            <h2 id="security-heading" className="mt-2 text-xl font-semibold text-slate-950">Security</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">Choose a strong password that you do not use for another account.</p>

            <ul className="mt-6 space-y-3 text-sm text-slate-600" aria-label="Password requirements">
              <li className="flex items-start gap-3">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-teal-600" />
                Use 8-72 characters.
              </li>
              <li className="flex items-start gap-3">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-teal-600" />
                Include at least one letter and one number.
              </li>
              <li className="flex items-start gap-3">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-teal-600" />
                Make it different from your current password.
              </li>
            </ul>
          </div>

          <form className="p-6 lg:p-8" onSubmit={submitPassword} noValidate>
            <div>
              <h3 className="text-lg font-semibold text-slate-950">Change password</h3>
              <p className="mt-1 text-sm leading-6 text-slate-500">Confirm your current password before creating a new one.</p>
            </div>

            <div className="mt-6 space-y-5">
              {passwordNotice && <p className="alert-info" role="status">{passwordNotice}</p>}
              {passwordError && <p className="alert-error" role="alert">{passwordError}</p>}

              <label className="field-label" htmlFor="current-password">Current password
                <input id="current-password" aria-label="Current password" name="currentPassword" type="password" autoComplete="current-password" className="field-input" value={passwordForm.currentPassword} onChange={(event) => updatePassword('currentPassword', event.target.value)} />
              </label>

              <div className="border-t border-slate-100 pt-5">
                <div className="grid gap-5 sm:grid-cols-2">
                  <label className="field-label" htmlFor="new-password">New password
                    <input id="new-password" aria-label="New password" name="newPassword" type="password" autoComplete="new-password" className="field-input" minLength={8} maxLength={72} value={passwordForm.newPassword} onChange={(event) => updatePassword('newPassword', event.target.value)} />
                  </label>
                  <label className="field-label" htmlFor="confirm-new-password">Confirm new password
                    <input id="confirm-new-password" aria-label="Confirm new password" name="confirmPassword" type="password" autoComplete="new-password" className="field-input" value={passwordForm.confirmPassword} onChange={(event) => updatePassword('confirmPassword', event.target.value)} />
                  </label>
                </div>
              </div>
            </div>

            <div className="mt-6 flex flex-col gap-3 border-t border-slate-100 pt-5 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-xs leading-5 text-slate-500">All password fields are required.</p>
              <button type="submit" className="button-primary sm:min-w-40" disabled={isChangingPassword}>{isChangingPassword ? 'Updating...' : 'Update password'}</button>
            </div>
          </form>
        </div>
      </section>
    </div>
  )
}
