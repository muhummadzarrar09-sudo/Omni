// Next.js API route -> proxies to FastAPI /api/security/guard/disarm
export async function POST() {
  try {
    const res = await fetch('http://localhost:8765/api/security/guard/disarm', { method: 'POST' })
    const data = await res.json()
    return Response.json(data)
  } catch (e) {
    return Response.json({ ok: false, detail: 'FastAPI not running' })
  }
}
