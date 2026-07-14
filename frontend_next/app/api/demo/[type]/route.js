export async function GET(request, { params }) {
  const type = params.type
  
  try {
    const fastApiRes = await fetch(`http://localhost:8765/api/demo/${type}`)
    const data = await fastApiRes.json()
    return Response.json(data)
  } catch (e) {
    // Fallback mock demos for when FastAPI not running
    const demos = {
      accessibility: {
        workflow: "Accessibility - Low Vision Student Mode (Mock)",
        logs: [
          "[Planner] Intent: accessibility_help",
          "[Executor] high_contrast ON -> SUCCESS",
          "[Monitor] Verified",
          "[Evaluator] Goal achieved"
        ],
        final: "Accessibility suite enabled (mock). I see VS Code with omni.py open.",
        impact: "Impact: 1.3B disabled"
      },
      chain: {
        workflow: "Chain + Self-Healing (Mock)",
        logs: [
          "[Planner] Chain: open chrome, maximize, go to youtube",
          "[Executor] Chrome -> FAIL",
          "[Evaluator] Re-plan Chrome->Edge",
          "[Executor] Edge -> SUCCESS",
          "[Evaluator] GOAL ACHIEVED"
        ],
        final: "Self-healed! Edge fallback, maximized, youtube. Mock.",
        impact: "Technical: Only OMNI self-heals"
      },
      business: {
        workflow: "Shop Guardian (Mock)",
        logs: [
          "[Scout] Weather: Heavy rain Sindh",
          "[Risk] 85% sugar +20%",
          "[Sourcing] Akbar Traders @155/kg",
          "[Action] PO PDF + Urdu WhatsApp"
        ],
        final: "Saved Rs 500, avoided stockout (mock)",
        impact: "65M shops"
      }
    }
    
    const demo = demos[type]
    if (!demo) {
      return Response.json({ error: `Unknown demo ${type}` }, { status: 404 })
    }
    
    return Response.json({
      workflow: demo.workflow,
      logs: demo.logs,
      final: demo.final,
      impact: demo.impact,
      mock: true
    })
  }
}
