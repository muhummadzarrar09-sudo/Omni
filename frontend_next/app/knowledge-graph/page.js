'use client'
import { useState, useEffect, useRef } from 'react'

/**
 * OMNI Knowledge Graph viewer - renders the RAG+CAG memory graph as an
 * interactive force-directed visualization (canvas, no heavy deps).
 * Loads graph JSON from /api/knowledge-graph, falls back to mock.
 */

export default function KnowledgeGraphPage() {
  const [graph, setGraph] = useState({ nodes: [], edges: [] })
  const [stats, setStats] = useState(null)
  const [sel, setSel] = useState(null)
  const canvasRef = useRef(null)

  useEffect(() => {
    fetch('/api/knowledge-graph')
      .then(r => r.json())
      .then(d => {
        setGraph(d)
        setStats(d.stats)
      })
      .catch(() => {
        setStats({ nodes: 0, edges: 0, message: 'FastAPI not running' })
      })
  }, [])

  // simple force layout on canvas
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const nodes = (graph.nodes || []).slice(0, 200)
    const edges = (graph.edges || []).slice(0, 400)
    const W = canvas.width = 900, H = canvas.height = 600
    const nodeMap = {}
    nodes.forEach((n, i) => { nodeMap[n.id] = i })
    // init positions in a circle
    nodes.forEach((n, i) => {
      n.x = W / 2 + Math.cos(i / nodes.length * 2 * Math.PI) * (W * 0.3)
      n.y = H / 2 + Math.sin(i / nodes.length * 2 * Math.PI) * (H * 0.3)
    })
    const color = { topic: '#22d3ee', file: '#a78bfa', tool: '#34d399', command: '#fbbf24', person: '#f472b6', entity: '#f87171' }
    let raf
    const tick = () => {
      // repulsion
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[j].x - nodes[i].x, dy = nodes[j].y - nodes[i].y
          const d2 = dx * dx + dy * dy + 1
          const f = 200 / d2
          nodes[i].x -= dx * f; nodes[i].y -= dy * f
          nodes[j].x += dx * f; nodes[j].y += dy * f
        }
      }
      // springs on edges
      for (const e of edges) {
        const a = nodeMap[e.source], b = nodeMap[e.target]
        if (a === undefined || b === undefined) continue
        const dx = nodes[b].x - nodes[a].x, dy = nodes[b].y - nodes[a].y
        const d = Math.sqrt(dx * dx + dy * dy) + 1
        const f = (d - 60) * 0.02
        nodes[a].x += dx / d * f; nodes[a].y += dy / d * f
        nodes[b].x -= dx / d * f; nodes[b].y -= dy / d * f
      }
      // draw
      ctx.fillStyle = '#020617'; ctx.fillRect(0, 0, W, H)
      for (const e of edges) {
        const a = nodeMap[e.source], b = nodeMap[e.target]
        if (a === undefined || b === undefined) continue
        ctx.strokeStyle = 'rgba(148,163,184,0.25)'; ctx.lineWidth = 0.5 + Math.min(e.weight || 1, 4)
        ctx.beginPath(); ctx.moveTo(nodes[a].x, nodes[a].y); ctx.lineTo(nodes[b].x, nodes[b].y); ctx.stroke()
      }
      for (const n of nodes) {
        ctx.fillStyle = color[n.kind] || '#94a3b8'
        ctx.beginPath(); ctx.arc(n.x, n.y, 4 + Math.min(n.weight || 1, 8), 0, 2 * Math.PI); ctx.fill()
        if (n.weight >= 2) {
          ctx.fillStyle = 'rgba(255,255,255,0.6)'
          ctx.font = '10px monospace'
          ctx.fillText(n.name.slice(0, 14), n.x + 6, n.y - 4)
        }
      }
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [graph])

  return (
    <div className="min-h-screen bg-[#020617] text-white p-6 font-mono">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-sm tracking-widest">🧠 KNOWLEDGE GRAPH</h1>
        <div className="text-[10px] text-white/40">
          {stats ? `${stats.nodes} nodes · ${stats.edges} edges${stats.message ? ' · ' + stats.message : ''}` : 'loading…'}
        </div>
      </div>
      <div className="flex gap-2 text-[10px] mb-3 text-white/60">
        <span><span className="inline-block w-2 h-2 rounded-full bg-cyan-400 mr-1"/>topic</span>
        <span><span className="inline-block w-2 h-2 rounded-full bg-violet-400 mr-1"/>file</span>
        <span><span className="inline-block w-2 h-2 rounded-full bg-emerald-400 mr-1"/>tool</span>
        <span><span className="inline-block w-2 h-2 rounded-full bg-amber-400 mr-1"/>command</span>
      </div>
      <div className="relative">
        <canvas ref={canvasRef} className="w-full border border-white/10 rounded-xl bg-black/40" />
        {sel && (
          <div className="absolute top-3 left-3 bg-[#0D1424] border border-white/10 rounded-lg px-3 py-2 text-xs">
            <div className="text-cyan-300">{sel.name}</div>
            <div className="text-white/50 text-[10px]">kind: {sel.kind} · weight: {sel.weight}</div>
          </div>
        )}
      </div>
    </div>
  )
}
