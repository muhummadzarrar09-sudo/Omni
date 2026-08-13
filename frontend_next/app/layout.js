import './globals.css'

export const metadata = {
  title: 'OMNI — Personal AI Assistant',
  description: 'Experimental local-first interface for the OMNI personal AI assistant.',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
