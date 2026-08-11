// Next.js API route -> proxies to FastAPI /api/security/lock
export async function POST() {
  try {
    const res = await fetch('http://localhost:8765/api/security/lock', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason: 'manual lock from OMNI web UI' })
    })
    const data = await res.json()
    return Response.json(data)
  } catch (e) {
    return Response.json({ ok: false, detail: 'FastAPI not running' })
  }
}
