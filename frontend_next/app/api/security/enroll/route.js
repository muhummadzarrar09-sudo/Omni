// Next.js API route -> proxies to FastAPI /api/security/enroll
export async function POST() {
  try {
    const res = await fetch('http://localhost:8765/api/security/enroll', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ frames: 6, delay: 0.25 })
    })
    const data = await res.json()
    return Response.json(data)
  } catch (e) {
    return Response.json({ ok: false, detail: 'FastAPI not running' })
  }
}
