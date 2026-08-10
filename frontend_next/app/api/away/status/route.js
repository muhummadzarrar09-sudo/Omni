// Next.js API route -> proxies to FastAPI /api/away/status
export async function GET() {
  try {
    const res = await fetch('http://localhost:8765/api/away/status')
    const data = await res.json()
    return Response.json(data)
  } catch (e) {
    return Response.json({ active: false, messenger: 'file', mock: true })
  }
}
