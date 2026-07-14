/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        neu: {
          bg: '#1E222D',
          card: '#232933',
          inset: '#1E242F',
          light: '#2A313F',
          text: '#E2E8F0',
          text2: '#A0AEC0',
          text3: '#6B7280',
          accent: '#38BDF8',
          green: '#4ADE80',
          orange: '#FB923C',
          red: '#F87171',
          purple: '#C4B5FD',
        }
      },
      boxShadow: {
        'neu': '12px 12px 24px rgba(0,0,0,0.55), -8px -8px 20px rgba(255,255,255,0.055)',
        'neu-sm': '8px 8px 16px rgba(0,0,0,0.55), -6px -6px 14px rgba(255,255,255,0.055)',
        'neu-inset': 'inset 8px 8px 16px rgba(0,0,0,0.75), inset -6px -6px 16px rgba(255,255,255,0.055)',
        'neu-inset-sm': 'inset 5px 5px 12px rgba(0,0,0,0.75), inset -4px -4px 12px rgba(255,255,255,0.055)',
      },
      fontFamily: {
        sans: ['Inter', 'Segoe UI', 'sans-serif'],
        mono: ['JetBrains Mono', 'Consolas', 'monospace'],
      }
    },
  },
  plugins: [],
}
