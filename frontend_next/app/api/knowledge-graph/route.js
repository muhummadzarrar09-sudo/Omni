// Next.js API route -> proxies to FastAPI /api/knowledge-graph
export async function GET() {
  try {
    const res = await fetch('http://localhost:8765/api/knowledge-graph')
    const data = await res.json()
    return Response.json(data)
  } catch (e) {
    return Response.json({ nodes: [], edges: [], stats: { nodes: 0, edges: 0, message: 'FastAPI not running' } })
  }
}
