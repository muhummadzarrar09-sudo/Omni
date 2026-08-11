// Next.js API route -> proxies to FastAPI /api/goals (Jarvis goal stack)
export async function GET() {
  try {
    const res = await fetch('http://localhost:8765/api/goals')
    const data = await res.json()
    return Response.json(data)
  } catch (e) {
    return Response.json({ goals: [], mock: true, message: 'FastAPI not running' })
  }
}

export async function POST(request) {
  try {
    const body = await request.json()
    const res = await fetch('http://localhost:8765/api/goals', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
    const data = await res.json()
    return Response.json(data)
  } catch (e) {
    return Response.json({ error: e.message }, { status: 500 })
  }
}
