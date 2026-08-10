// Next.js API route -> proxies to FastAPI /api/reflect/patterns (pattern awareness)
export async function POST(request) {
  try {
    const body = await request.json()
    const res = await fetch('http://localhost:8765/api/reflect/patterns', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
    const data = await res.json()
    return Response.json(data)
  } catch (e) {
    return Response.json({ patterns: [], mock: true, message: 'FastAPI not running' })
  }
}
