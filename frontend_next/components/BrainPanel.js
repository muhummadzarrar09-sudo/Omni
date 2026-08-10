'use client'
import { useState, useEffect } from 'react'

/**
 * OMNI Jarvis Brain panel - drives identity / goals / reflection / patterns
 * through the Next.js -> FastAPI proxy routes. Works locally; falls back to
 * mock state when FastAPI isn't running.
 */

const API = {
  identity: '/api/brain/identity',
  user: '/api/brain/user',
  goals: '/api/goals',
  patterns: '/api/reflect/patterns',
  reflectToday: '/api/reflect/today',
  episodes: '/api/reflect/episodes',
}

async function jget(path) {
  try {
    const r = await fetch(path)
    return await r.json()
  } catch (e) {
    return { mock: true }
  }
}
async function jpost(path, body) {
  try {
    const r = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined,
    })
    return await r.json()
  } catch (e) {
    return { mock: true }
  }
}

export default function BrainPanel() {
  const [tab, setTab] = useState('identity')
  const [identity, setIdentity] = useState(null)
  const [goals, setGoals] = useState([])
  const [episodes, setEpisodes] = useState([])
  const [patterns, setPatterns] = useState([])
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState('')

  const load = async () => {
    setIdentity(await jget(API.identity))
    setGoals((await jget(API.goals)).goals || [])
    setEpisodes((await jget(API.episodes)).episodes || [])
    setPatterns((await jpost(API.patterns, { days: 7 })).patterns || [])
  }
  useEffect(() => { load() }, [])

  const refresh = async () => {
    setBusy(true)
    await load()
    setBusy(false)
  }

  const createGoal = async () => {
    const intent = prompt('Goal intent:')
    if (!intent) return
    const res = await jpost(API.goals, { intent })
    setMsg(res.goal ? `Goal created: ${res.goal.title} (${res.goal.steps.length} steps)` : 'Goal create failed')
    setGoals((await jget(API.goals)).goals || [])
  }

  const reflectToday = async () => {
    const res = await jpost(API.reflectToday)
    setMsg(res.episode ? `Reflected: ${res.episode.summary}` : 'Reflect failed')
    setEpisodes((await jget(API.episodes)).episodes || [])
  }

  const updateName = async () => {
    const name = prompt('Your name:')
    if (!name) return
    const res = await jpost(API.user, { name })
    setIdentity(await jget(API.identity))
    setMsg(`User set to ${res.name || name}`)
  }

  const card = 'bg-[#0D1424] border border-white/10 rounded-xl p-3'
  const tabBtn = (t) => `px-3 py-1.5 rounded-lg text-xs font-mono transition ${tab === t ? 'bg-cyan-500/20 text-cyan-200 border border-cyan-500/30' : 'text-white/60 hover:bg-white/5'}`

  return (
    <div className="w-full max-w-3xl mx-auto p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-sm font-mono tracking-widest text-white font-bold">🧠 JARVIS BRAIN</div>
        <button onClick={refresh} className="text-xs font-mono px-3 py-1.5 rounded-lg bg-white/5 text-white/70 hover:bg-white/10">
          {busy ? '…' : '↻ Refresh'}
        </button>
      </div>

      <div className="flex gap-2 flex-wrap">
        {['identity', 'goals', 'episodes', 'patterns'].map((t) => (
          <button key={t} onClick={() => setTab(t)} className={tabBtn(t)}>{t.toUpperCase()}</button>
        ))}
      </div>

      {msg && <div className="text-xs font-mono text-emerald-300/80 bg-emerald-500/5 border border-emerald-500/20 rounded-lg px-3 py-2">{msg}</div>}

      {tab === 'identity' && (
        <div className="space-y-2">
          <div className={card}>
            <div className="text-[10px] font-mono text-cyan-400/60 uppercase tracking-widest mb-1">Identity</div>
            <div className="font-mono text-sm text-white">Name: <span className="text-cyan-300">{identity?.name || 'OMNI'}</span></div>
            <div className="font-mono text-xs text-white/70 mt-1">Mood: {identity?.mood || 'neutral'} · Values: {(identity?.values || ['privacy']).join(', ')}</div>
            <div className="font-mono text-[11px] text-white/50 mt-1 truncate">Persona: {identity?.persona || 'local butler'}</div>
          </div>
          <div className={card}>
            <div className="text-[10px] font-mono text-cyan-400/60 uppercase tracking-widest mb-1">The user</div>
            <div className="font-mono text-sm text-white">Name: <span className="text-cyan-300">{identity?.user?.name || '(not set)'}</span></div>
            <div className="font-mono text-xs text-white/70 mt-1">Style: {identity?.user?.style || 'casual'} · Tone: {identity?.user?.tone || 'direct'}</div>
            <div className="font-mono text-[11px] text-white/50 mt-1">Likes: {(identity?.user?.likes || []).join(', ') || '—'}</div>
            <button onClick={updateName} className="mt-3 text-xs font-mono px-3 py-1.5 rounded-lg bg-white/5 text-white/70 hover:bg-white/10">Set user name</button>
          </div>
        </div>
      )}

      {tab === 'goals' && (
        <div className="space-y-2">
          <button onClick={createGoal} className="text-xs font-mono px-3 py-1.5 rounded-lg bg-cyan-500/20 text-cyan-200 border border-cyan-500/30 hover:bg-cyan-500/30">＋ New goal</button>
          {goals.length === 0 && <div className="text-xs font-mono text-white/40">No goals yet.</div>}
          {goals.map((g) => (
            <div key={g.id} className={card}>
              <div className="flex items-center justify-between">
                <span className="font-mono text-sm text-white">{g.title}</span>
                <span className="text-[10px] font-mono text-cyan-300">{Math.round(g.progress * 100)}%</span>
              </div>
              <div className="text-[10px] font-mono text-white/40 mt-0.5">[{g.status}]</div>
              {(g.steps || []).map((s, i) => (
                <div key={i} className="font-mono text-[11px] mt-1 text-white/70">
                  {s.status === 'done' ? '✔' : s.status === 'failed' ? '✘' : s.status === 'running' ? '▶' : '·'} {s.desc}
                </div>
              ))}
            </div>
          ))}
        </div>
      )}

      {tab === 'episodes' && (
        <div className="space-y-2">
          <button onClick={reflectToday} className="text-xs font-mono px-3 py-1.5 rounded-lg bg-white/5 text-white/70 hover:bg-white/10">📓 Reflect today</button>
          {episodes.length === 0 && <div className="text-xs font-mono text-white/40">No episodes yet.</div>}
          {episodes.map((e, i) => (
            <div key={i} className={card}>
              <div className="text-[10px] font-mono text-white/40">{e.day}</div>
              <div className="font-mono text-xs text-white/80 mt-1">{e.summary}</div>
            </div>
          ))}
        </div>
      )}

      {tab === 'patterns' && (
        <div className="space-y-2">
          {patterns.length === 0 && <div className="text-xs font-mono text-white/40">No notable patterns.</div>}
          {patterns.map((p, i) => (
            <div key={i} className={card}>
              <div className="font-mono text-sm text-white">{p.severity >= 2 ? '🔴' : p.severity === 1 ? '🟡' : '⚪'} {p.title}</div>
              <div className="font-mono text-[11px] text-white/60 mt-1">{p.body}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
