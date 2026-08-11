// Next.js API route -> proxies to FastAPI /api/reflect/episodes
export async function GET() {
  try {
    const res = await fetch('http://localhost:8765/api/reflect/episodes')
    const data = await res.json()
    return Response.json(data)
  } catch (e) {
    return Response.json({ episodes: [], mock: true })
  }
}
