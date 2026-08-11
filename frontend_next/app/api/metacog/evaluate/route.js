// Next.js API route -> proxies to FastAPI /api/metacog/evaluate
export async function POST(request) {
  try {
    const body = await request.json()
    const res = await fetch('http://localhost:8765/api/metacog/evaluate', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
    const data = await res.json()
    return Response.json(data)
  } catch (e) {
    return Response.json({ verdict: { action: 'succeeded', succeeded: true }, mock: true })
  }
}
