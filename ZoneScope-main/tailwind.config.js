/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // Clinical white–blue palette. Token names kept ("teal" = primary,
        // "agar" = neutral surfaces) so components reskin without edits.
        teal: {
          DEFAULT: '#000080',
          50: '#ECECF6',
          100: '#C9C9E6',
          600: '#000080',
          700: '#000066',
          800: '#00004D',
          900: '#000033',
        },
        agar: {
          DEFAULT: '#DCE6F1',
          50: '#F4F8FC',
          100: '#EAF1F8',
          200: '#DCE6F1',
          300: '#C3D3E5',
        },
        ink: {
          DEFAULT: '#14202E',
          soft: '#43566B',
          faint: '#7A8CA1',
        },
        // Clinical S / I / R semantics
        sir: {
          s: '#2E9E6B',
          i: '#DDA02B',
          r: '#D2483F',
        },
      },
      fontFamily: {
        sans: ['"PSU Stidti"', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      boxShadow: {
        card: '0 1px 2px rgba(28,35,33,0.06), 0 8px 24px rgba(28,35,33,0.06)',
        sheet: '0 -8px 30px rgba(28,35,33,0.10)',
      },
      borderRadius: {
        xl2: '1.25rem',
      },
    },
  },
  plugins: [],
}
