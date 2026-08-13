import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        lab: {
          50: '#edf7fa',
          100: '#d6edf3',
          200: '#addae7',
          700: '#0f4a6a',
          800: '#0b3954',
        },
      },
      boxShadow: {
        panel: '0 18px 45px -26px rgba(15, 61, 92, 0.42)',
      },
    },
  },
  plugins: [],
} satisfies Config
