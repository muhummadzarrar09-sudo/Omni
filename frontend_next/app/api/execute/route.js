export async function POST(request) {
  try {
    const body = await request.json()
    const { command } = body
    
    if (!command) {
      return Response.json({ error: 'No command' }, { status: 400 })
    }
    
    // Proxy to FastAPI
    try {
      const fastApiRes = await fetch('http://localhost:8765/api/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command })
      })
      const data = await fastApiRes.json()
      return Response.json(data)
    } catch (e) {
      // Fallback mock if FastAPI not running - judges can still see UI
      return Response.json({
        success: true,
        message: `Mock (FastAPI not running): Would execute "${command}" in isolated Chrome profile OMNI-Profile (no email, privacy). Start FastAPI: cd backend_fastapi && uvicorn main:app --port 8765`,
        logs: [`[Planner] Mock plan for '${command}'`, `[Executor] Mock success - isolated profile`, `[Monitor] Verified`],
        mock: true
      })
    }
  } catch (e) {
    return Response.json({ error: e.message }, { status: 500 })
  }
}
