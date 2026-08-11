// Next.js API route -> proxies to FastAPI /api/brain/identity (Jarvis identity core)
export async function GET() {
  try {
    const res = await fetch('http://localhost:8765/api/brain/identity')
    const data = await res.json()
    return Response.json(data)
  } catch (e) {
    return Response.json({ name: 'OMNI', persona: 'local butler', mood: 'neutral',
      goals_today: [], values: ['privacy'], user: { name: '', style: 'casual' },
      mock: true, message: 'FastAPI not running' })
  }
}

export async function POST(request) {
  try {
    const body = await request.json()
    const res = await fetch('http://localhost:8765/api/brain/identity', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
    const data = await res.json()
    return Response.json(data)
  } catch (e) {
    return Response.json({ error: e.message }, { status: 500 })
  }
}
