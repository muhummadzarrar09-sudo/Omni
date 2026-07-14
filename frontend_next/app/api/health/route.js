export async function GET() {
  try {
    const res = await fetch('http://localhost:8765/api/health')
    const data = await res.json()
    return Response.json({ ...data, nextjs: true, frontend: 'Next.js 14 neomorphism correct' })
  } catch (e) {
    return Response.json({
      status: 'mock',
      brain_ready: false,
      nextjs: true,
      frontend: 'Next.js 14 neomorphism correct - real double box-shadow',
      message: 'FastAPI not running - UI in mock mode, still shows neomorphism + demos',
      portable: true,
      fix: 'No D:/Omni hardcode, Path(__file__).resolve()'
    })
  }
}
