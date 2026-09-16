/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        canvas: '#0B0F17',
        surface: {
          1: '#111827',
          2: '#1A2234',
          hover: '#232D42',
        },
        border: {
          DEFAULT: '#2D3748',
          subtle: '#1F2937',
        },
        ops: {
          neutral: '#64748B',
          weather: '#38BDF8',
          pressure: '#818CF8',
          humidity: '#34D399',
          healthy: '#10B981',
          warning: '#F59E0B',
          critical: '#EF4444',
          genuine: '#6366F1',
          uncertain: '#EC4899',
          offline: '#475569',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      fontSize: {
        'stat': ['28px', { lineHeight: '1.1', letterSpacing: '-0.02em', fontWeight: '600' }],
        'h1': ['18px', { lineHeight: '1.2', letterSpacing: '-0.01em', fontWeight: '600' }],
        'h2': ['15px', { lineHeight: '1.3', fontWeight: '600' }],
        'body': ['13px', { lineHeight: '1.4' }],
        'data': ['12px', { lineHeight: '1.3', fontWeight: '500' }],
        'telemetry': ['11px', { lineHeight: '1.2', fontFamily: 'JetBrains Mono, monospace' }],
      },
      spacing: {
        '4.5': '1.125rem',
      },
    },
  },
  plugins: [],
}
