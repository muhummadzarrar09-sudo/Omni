// Next.js API route -> proxies to FastAPI /api/security/status
export async function GET() {
  try {
    const res = await fetch('http://localhost:8765/api/security/status')
    const data = await res.json()
    return Response.json(data)
  } catch (e) {
    return Response.json({ enrolled: false, backend: 'unavailable', mock: true })
  }
}
