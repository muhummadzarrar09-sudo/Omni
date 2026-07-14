export async function GET() {
  try {
    const res = await fetch('http://localhost:8765/api/devices')
    const data = await res.json()
    return Response.json(data)
  } catch (e) {
    // Mock devices
    return Response.json({
      devices: [
        { index: 10, name: 'Microphone (Realtek HD Audio Mic input) ⭐ BEST', score: 339.0, is_best: true },
        { index: 13, name: 'Microphone (Realtek HD Audio Mic input)', score: 338.7, is_best: false },
        { index: 1, name: 'Microphone (Realtek Audio)', score: 314.9, is_best: false },
      ],
      best: 10,
      best_name: '[10] Realtek HD Audio Mic input',
      mock: true,
      message: 'FastAPI not running, using mock. Start backend for real devices.'
    })
  }
}
