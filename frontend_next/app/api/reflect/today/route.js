// Next.js API route -> proxies to FastAPI /api/reflect/today (episodic recap)
export async function POST() {
  try {
    const res = await fetch('http://localhost:8765/api/reflect/today', { method: 'POST' })
    const data = await res.json()
    return Response.json(data)
  } catch (e) {
    return Response.json({ episode: { day: 'today', summary: 'No activity (FastAPI not running)' }, mock: true })
  }
}
