// Next.js API route -> proxies to FastAPI /api/brain/identity/user (user model)
export async function GET() {
  try {
    const res = await fetch('http://localhost:8765/api/brain/identity/user')
    const data = await res.json()
    return Response.json(data)
  } catch (e) {
    return Response.json({ name: '', style: 'casual', likes: [], dislikes: [], mock: true })
  }
}

export async function POST(request) {
  try {
    const body = await request.json()
    const res = await fetch('http://localhost:8765/api/brain/identity/user', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
    const data = await res.json()
    return Response.json(data)
  } catch (e) {
    return Response.json({ error: e.message }, { status: 500 })
  }
}
