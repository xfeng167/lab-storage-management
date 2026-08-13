import { ChangeEvent, FormEvent, useEffect, useRef, useState } from 'react'
import { useAuth } from '../auth/AuthContext'

interface ProfileForm {
  username: string
  email: string
  profile_picture: string | null
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

function readImageFile(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result))
    reader.onerror = () => reject(new Error('Unable to read profile picture.'))
    reader.readAsDataURL(file)
  })
}

export function AccountPage() {
  const { user, updateProfile } = useAuth()
  const [form, setForm] = useState<ProfileForm>({ username: '', email: '', profile_picture: null })
  const [previousPicture, setPreviousPicture] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
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

  return (
    <div className="mx-auto max-w-5xl">
      <p className="eyebrow">Your account</p>
      <div className="mt-3 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-slate-950">Profile settings</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">Manage the identity shown across Lab Storage Management.</p>
        </div>
        <span className="inline-flex w-fit rounded-full bg-lab-50 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-lab-800">{formatRole(user.role)}</span>
      </div>

      {notice && <p className="alert-info mt-6" role="status">{notice}</p>}
      {error && <p className="alert-error mt-6" role="alert">{error}</p>}

      <div className="mt-8 grid gap-6 lg:grid-cols-[0.85fr_1.15fr]">
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-panel" aria-label="Profile preview">
          <div className="flex flex-col items-center text-center">
            <div className="grid h-32 w-32 place-items-center overflow-hidden rounded-2xl bg-lab-50 text-3xl font-semibold text-lab-800 ring-1 ring-slate-200">
              {form.profile_picture ? <img className="h-full w-full object-cover" src={form.profile_picture} alt={`${form.username || user.username} profile`} /> : <span>{initials(form.username || user.username)}</span>}
            </div>
            <h2 className="mt-5 text-2xl font-semibold text-slate-950">{form.username || user.username}</h2>
            <p className="mt-1 text-sm text-slate-500">{form.email || user.email}</p>
          </div>
          <dl className="mt-6 divide-y divide-slate-100 rounded-xl border border-slate-100">
            <div className="grid grid-cols-2 gap-4 px-4 py-3 text-sm">
              <dt className="text-slate-500">Account ID</dt>
              <dd className="text-right font-mono font-semibold text-slate-900">{user.id}</dd>
            </div>
            <div className="grid grid-cols-2 gap-4 px-4 py-3 text-sm">
              <dt className="text-slate-500">Role</dt>
              <dd className="text-right font-semibold text-slate-900">{formatRole(user.role)}</dd>
            </div>
            <div className="grid grid-cols-2 gap-4 px-4 py-3 text-sm">
              <dt className="text-slate-500">Session</dt>
              <dd className="text-right font-semibold text-slate-900">1 hour</dd>
            </div>
          </dl>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white shadow-panel" aria-label="Edit profile">
          <div className="border-b border-slate-100 px-6 py-5">
            <h2 className="font-semibold text-slate-950">Edit profile</h2>
            <p className="mt-1 text-sm text-slate-500">Changes are saved to your current account and reflected in the app header.</p>
          </div>
          <form className="space-y-5 p-6" onSubmit={submit} noValidate>
            <label className="field-label" htmlFor="profile-username">Username
              <input id="profile-username" className="field-input" minLength={3} maxLength={30} pattern="[A-Za-z][A-Za-z0-9_]{2,29}" value={form.username} onChange={(event) => update('username', event.target.value)} />
              <span className="mt-1 text-xs font-normal text-slate-500">3-30 characters. Start with a letter. Letters, numbers, and underscores only.</span>
            </label>
            <label className="field-label" htmlFor="profile-email">Email address
              <input id="profile-email" className="field-input" type="email" maxLength={255} value={form.email} onChange={(event) => update('email', event.target.value)} />
              <span className="mt-1 text-xs font-normal text-slate-500">Use a valid email address, up to 255 characters.</span>
            </label>
            <div className="grid gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4 sm:grid-cols-[1fr_auto] sm:items-end">
              <label className="field-label" htmlFor="profile-picture">Profile picture
                <input ref={fileInputRef} id="profile-picture" className="field-input bg-white" type="file" accept="image/*" onChange={(event) => void handlePictureChange(event)} />
                <span className="mt-1 text-xs font-normal text-slate-500">Upload a small image under 350 KB.</span>
              </label>
              <div className="flex flex-wrap gap-2 sm:justify-end">
                <button type="button" className="button-secondary" onClick={() => void clearPicture()} disabled={isSaving || !form.profile_picture}>Clear picture</button>
                <button type="button" className="button-secondary" onClick={() => void restorePreviousPicture()} disabled={isSaving || !previousPicture || previousPicture === form.profile_picture}>Use previous</button>
              </div>
              {previousPicture && previousPicture !== form.profile_picture && (
                <div className="flex items-center gap-3 rounded-lg border border-slate-200 bg-white p-3 sm:col-span-2">
                  <img className="h-12 w-12 rounded-lg object-cover ring-1 ring-slate-200" src={previousPicture} alt="Previous profile" />
                  <p className="text-xs leading-5 text-slate-500">One previous picture is available to restore.</p>
                </div>
              )}
            </div>
            <div className="flex justify-end border-t border-slate-100 pt-5">
              <button type="submit" className="button-primary" disabled={isSaving}>{isSaving ? 'Saving...' : 'Save profile'}</button>
            </div>
          </form>
        </section>
      </div>
    </div>
  )
}
