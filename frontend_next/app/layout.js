import './globals.css'

export const metadata = {
  title: 'OMNI V3 — Neomorphism Soft UI | Offline Agent',
  description: 'Your Voice is Enough — Dark neomorphism correct double box-shadow, Three.js 2400 particles, FastAPI backend, profile isolated privacy, sounddevice fixes -9999, GTX 1050 Ti optimized',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet" />
      </head>
      <body>{children}</body>
    </html>
  )
}
