import { startVitest } from 'vitest/node'
import react from '@vitejs/plugin-react'

const context = await startVitest(
  'test',
  [],
  {
    run: true,
    threads: false,
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: true,
  },
  {
    configFile: false,
    plugins: [react()],
  },
)

await context?.close()
