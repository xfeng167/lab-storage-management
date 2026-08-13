import { Outlet } from 'react-router-dom'
import { Brand } from '../components/Brand'

export function AuthLayout() {
  return (
    <main className="relative grid min-h-screen overflow-hidden bg-slate-50 px-5 py-8 lg:grid-cols-[1.1fr_0.9fr] lg:p-10">
      <div className="absolute -left-20 top-10 h-80 w-80 rounded-full bg-teal-100 blur-3xl" aria-hidden="true" />
      <section className="relative hidden flex-col justify-between rounded-3xl bg-lab-800 p-12 text-white shadow-panel lg:flex">
        <Brand />
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-teal-200">Lab operations, simplified</p>
          <h1 className="mt-5 max-w-xl text-5xl font-semibold leading-tight">Know what your lab has, and where it belongs.</h1>
          <p className="mt-6 max-w-lg text-base leading-7 text-lab-100">Secure account access for the teams that keep research materials organized and ready.</p>
        </div>
        <p className="text-sm text-lab-200">Lab Storage Management</p>
      </section>
      <section className="relative mx-auto flex w-full max-w-md items-center py-10 lg:px-10">
        <div className="w-full">
          <div className="mb-10 lg:hidden"><Brand /></div>
          <Outlet />
        </div>
      </section>
    </main>
  )
}
