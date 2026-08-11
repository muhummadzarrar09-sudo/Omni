'use client'
import { useState, useEffect } from 'react'

/**
 * OMNI Camera Security panel - enroll owner, arm/disarm guard, lock.
 * Proxies to FastAPI /api/security/*. Fully local.
 */

const API = {
  status: '/api/security/status',
  enroll: '/api/security/enroll',
  arm: '/api/security/guard/arm',
  disarm: '/api/security/guard/disarm',
  lock: '/api/security/lock',
}

async function jget(path) {
  try { return await (await fetch(path)).json() } catch (e) { return { mock: true } }
}
async function jpost(path) {
  try {
    const r = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })
    return await r.json()
  } catch (e) { return { mock: true } }
}

export default function SecurityPanel() {
  const [status, setStatus] = useState(null)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState('')

  const load = async () => { setStatus(await jget(API.status)) }
  useEffect(() => {
    let cancelled = false
    jget(API.status).then((nextStatus) => {
      if (!cancelled) setStatus(nextStatus)
    })
    return () => { cancelled = true }
  }, [])

  const doEnroll = async () => { setBusy(true); const r = await jpost(API.enroll); setMsg(r.detail || 'enroll'); setBusy(false); load() }
  const doArm = async () => { setBusy(true); const r = await jpost(API.arm); setMsg(r.detail || 'arm'); setBusy(false); load() }
  const doDisarm = async () => { setBusy(true); await jpost(API.disarm); setMsg('disarmed'); setBusy(false); load() }
  const doLock = async () => { setBusy(true); const r = await jpost(API.lock); setMsg(r.detail || 'locking'); setBusy(false) }

  const card = 'bg-[#0D1424] border border-white/10 rounded-xl p-3'
  const btn = (c) => `text-xs font-mono px-3 py-1.5 rounded-lg ${c}`

  return (
    <div className="w-full max-w-3xl mx-auto p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-sm font-mono tracking-widest text-white font-bold">🔒 CAMERA SECURITY</div>
        <button onClick={load} className="text-xs font-mono px-3 py-1.5 rounded-lg bg-white/5 text-white/70 hover:bg-white/10">{busy ? '…' : '↻'}</button>
      </div>

      {msg && <div className="text-xs font-mono text-emerald-300/80 bg-emerald-500/5 border border-emerald-500/20 rounded-lg px-3 py-2">{msg}</div>}

      <div className={card}>
        <div className="text-[10px] font-mono text-cyan-400/60 uppercase tracking-widest mb-2">Status</div>
        <div className="font-mono text-sm text-white">Owner enrolled: <span className={status?.enrolled ? 'text-emerald-300' : 'text-red-300'}>{status?.enrolled ? '✅ yes' : '❌ no'}</span></div>
        <div className="font-mono text-xs text-white/70 mt-1">Backend: {status?.backend || 'unavailable'}</div>
        <div className="font-mono text-xs text-white/70 mt-1">Guard armed: <span className={status?.guard?.armed ? 'text-emerald-300' : 'text-white/50'}>{status?.guard?.armed ? '✅' : '⚪'}</span></div>
        <div className="font-mono text-[11px] text-white/50 mt-1">samples: {status?.samples ?? '—'} · streak-req: {status?.guard?.streak_required ?? '—'}</div>
      </div>

      <div className="flex gap-2 flex-wrap">
        <button onClick={doEnroll} className={btn('bg-cyan-500/20 text-cyan-200 border border-cyan-500/30 hover:bg-cyan-500/30')}>📸 Enroll owner</button>
        <button onClick={doArm} className={btn('bg-emerald-500/20 text-emerald-200 border border-emerald-500/30 hover:bg-emerald-500/30')}>🛡 Arm guard</button>
        <button onClick={doDisarm} className={btn('bg-white/5 text-white/70 hover:bg-white/10')}>Disarm</button>
        <button onClick={doLock} className={btn('bg-red-500/20 text-red-200 border border-red-500/30 hover:bg-red-500/30')}>🔒 Lock now</button>
      </div>

      <div className={card}>
        <div className="text-[10px] font-mono text-cyan-400/60 uppercase tracking-widest mb-2">Lockdown history</div>
        {(status?.lockdown_history || []).length === 0 && <div className="text-xs font-mono text-white/40">No lockdown events.</div>}
        {(status?.lockdown_history || []).map((e, i) => (
          <div key={i} className="font-mono text-[11px] text-white/60 mt-1">[{e.status}] {e.reason}</div>
        ))}
      </div>
    </div>
  )
}
