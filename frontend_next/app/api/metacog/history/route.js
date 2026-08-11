// Next.js API route -> proxies to FastAPI /api/metacog/history
export async function GET() {
  try {
    const res = await fetch('http://localhost:8765/api/metacog/history')
    const data = await res.json()
    return Response.json(data)
  } catch (e) {
    return Response.json({ records: [], mock: true })
  }
}
