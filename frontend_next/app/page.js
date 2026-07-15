'use client'
import { useState, useEffect, useRef, useCallback } from 'react'
import CinematicStage from '../components/CinematicStage'

/**
 * OMNI Command Center - AGI Interface
 *
 * Design principles:
 * - The LLM's actual thinking is VISIBLE (live streamed tokens)
 * - Tool calls show up as discrete cards with intent, args, result
 * - The orb reflects the actual brain state (loading, thinking, listening, executing, speaking)
 * - Memory is visible (last 5 recalls)
 * - Conversation flows naturally without hardcoded states
 */

const STATE_STYLES = {
  booting:     { color: '#94A3B8', label: 'Booting',  orb: 'dim'    },
  idle:        { color: '#64748B', label: 'Idle',     orb: 'idle'   },
  listening:   { color: '#38BDF8', label: 'Listening', orb: 'pulse'  },
  thinking:    { color: '#FB923C', label: 'Reasoning', orb: 'spin'   },
  executing:   { color: '#A78BFA', label: 'Executing', orb: 'burst'  },
  speaking:    { color: '#34D399', label: 'Speaking',  orb: 'ripple' },
  error:       { color: '#EF4444', label: 'Error',     orb: 'red'    },
}

function ThinkingStream({ tokens, isStreaming }) {
  // tokens is a string built up token-by-token
  if (!tokens && !isStreaming) {
    return (
      <div className="text-[10px] font-mono text-white/20 tracking-widest uppercase">
        Awaiting input...
      </div>
    )
  }
  return (
    <div className="font-mono text-[12px] leading-relaxed text-orange-300/90 break-words min-h-[2.5rem]">
      <span className="text-orange-500/40 mr-2">▎</span>
      {tokens}
      {isStreaming && (
        <span className="inline-block w-1.5 h-3.5 bg-orange-400 ml-0.5 align-middle animate-pulse" />
      )}
    </div>
  )
}

function ToolCallCard({ tc, result, isActive }) {
  const status = isActive ? 'running' : (result?.success ? 'done' : 'error')
  const colors = {
    running: 'border-purple-500/50 bg-purple-500/5',
    done:    'border-emerald-500/30 bg-emerald-500/5',
    error:   'border-red-500/40 bg-red-500/5',
  }
  return (
    <div className={`border rounded-xl px-3 py-2 ${colors[status]} backdrop-blur-sm`}>
      <div className="flex items-center gap-2">
        <span className={`w-1.5 h-1.5 rounded-full ${
          status === 'running' ? 'bg-purple-400 animate-pulse' :
          status === 'done'    ? 'bg-emerald-400' : 'bg-red-400'
        }`} />
        <span className="text-[10px] font-mono text-white/60 tracking-widest uppercase">
          {status === 'running' ? '⚡ Executing' : status === 'done' ? '✓ Done' : '✕ Error'}
        </span>
        <span className="text-xs font-mono text-white/90 font-bold ml-auto">
          {tc.tool}
        </span>
      </div>
      {Object.keys(tc.args || {}).length > 0 && (
        <div className="text-[10px] font-mono text-white/50 mt-1 truncate">
          {Object.entries(tc.args).map(([k, v]) => (
            <span key={k} className="mr-2">
              <span className="text-white/30">{k}=</span>
              <span className="text-sky-400/70">"{String(v).slice(0, 40)}"</span>
            </span>
          ))}
        </div>
      )}
      {result?.message && status !== 'running' && (
        <div className="text-[10px] font-mono text-white/40 mt-1 truncate italic">
          → {result.message.slice(0, 100)}
        </div>
      )}
    </div>
  )
}

function MemoryChip({ recall }) {
  return (
    <div className="px-2.5 py-1 rounded-full bg-amber-500/10 border border-amber-500/20 text-[10px] font-mono text-amber-300/80 max-w-[200px] truncate" title={recall}>
      🧠 {recall}
    </div>
  )
}

export default function Home() {
  // The brain states map 1:1 to the LLM's actual lifecycle
  const [state, setState] = useState('booting')
  const [rms, setRms] = useState(0)

  // Live streamed LLM tokens (the "thoughts" the LLM is currently generating)
  const [thoughts, setThoughts] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)

  // Tool calls the LLM has decided to make + their results
  const [toolCalls, setToolCalls] = useState([])  // [{tc, result, isActive}]
  const [rawLlmOutput, setRawLlmOutput] = useState('')  // For debug

  // Brain metadata from server
  const [brainTier, setBrainTier] = useState('loading...')
  const [brainLatency, setBrainLatency] = useState(0)

  // Conversation
  const [messages, setMessages] = useState([])
  const [inputText, setInputText] = useState('')

  // Memory recall (from server)
  const [memories, setMemories] = useState([])

  // System log
  const [logs, setLogs] = useState([])
  const [showHistory, setShowHistory] = useState(false)
  const [showLogs, setShowLogs] = useState(false)
  const [showSettings, setShowSettings] = useState(false)

  const [devices, setDevices] = useState([])
  const [isMuted, setIsMuted] = useState(true)

  // PROACTIVE-UI: incoming suggestions from the AGI brain
  const [proactiveSuggestions, setProactiveSuggestions] = useState([])
  const [proactiveBanner, setProactiveBanner] = useState(null)

  const logRef = useRef(null)
  const thoughtsRef = useRef(null)

  function addLog(text) {
    const timeStr = new Date().toLocaleTimeString()
    setLogs(prev => [...prev.slice(-80), `[${timeStr}] ${text}`])
  }

  // Boot - check brain
  useEffect(() => {
    fetch('http://localhost:8765/api/health')
      .then(r => r.json())
      .then(d => {
        setBrainTier(d.brain_ready ? '🧠 LLM Brain Ready' : '⚠️ Brain Mock Mode')
        setState('idle')
        addLog(d.brain_ready
          ? '[Brain] LLM-loaded brain ready - Qwen2.5-1.5B reasoning online'
          : '[Brain] No LLM detected - using regex fallback')
        if (d.proactive_active) {
          addLog('[Proactive] 💡 AGI proactive engine online - watching for helpful moments')
        }
      })
      .catch(e => {
        setState('error')
        addLog(`[Boot] Failed to reach backend: ${e.message}`)
      })
    fetchDevices()
  }, [])

  // Auto-scroll logs
  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [logs])
  useEffect(() => {
    if (thoughtsRef.current) thoughtsRef.current.scrollTop = thoughtsRef.current.scrollHeight
  }, [thoughts])

  // PROACTIVE-UI: poll for new suggestions every 30s
  useEffect(() => {
    let mounted = true
    const pollProactive = async () => {
      try {
        const res = await fetch('http://localhost:8765/api/proactive/suggestions')
        const data = await res.json()
        if (!mounted) return
        const suggestions = data.suggestions || []
        setProactiveSuggestions(suggestions)
        // Show top-priority one as a banner
        if (suggestions.length > 0 && !proactiveBanner) {
          setProactiveBanner(suggestions[0])
          addLog(`[Proactive] 💡 ${suggestions[0].title} — ${suggestions[0].body.slice(0, 80)}`)
        }
      } catch (e) {
        // silent
      }
    }
    pollProactive()
    const interval = setInterval(pollProactive, 30000)
    return () => { mounted = false; clearInterval(interval) }
  }, [proactiveBanner])

  async function fetchDevices() {
    try {
      const res = await fetch('http://localhost:8765/api/devices')
      const data = await res.json()
      if (data.devices) setDevices(data.devices)
    } catch (e) { /* silent */ }
  }

  // PROACTIVE-UI: dismiss a suggestion
  async function dismissProactive(suggestionId) {
    try {
      await fetch('http://localhost:8765/api/proactive/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ suggestion_id: suggestionId, action: 'dismiss' }),
      })
      addLog(`[Proactive] Dismissed: ${suggestionId}`)
      setProactiveSuggestions(prev => prev.filter(s => s.id !== suggestionId))
      if (proactiveBanner?.id === suggestionId) {
        setProactiveBanner(null)
      }
    } catch (e) {
      addLog(`[Proactive] Dismiss failed: ${e.message}`)
    }
  }

  // PROACTIVE-UI: act on a suggestion (execute its first action command)
  async function actOnProactive(suggestion) {
    if (!suggestion.actions || suggestion.actions.length === 0) {
      return dismissProactive(suggestion.id)
    }
    const firstAction = suggestion.actions[0]
    if (firstAction.command === '_ack' || firstAction.command === '_snooze') {
      return dismissProactive(suggestion.id)
    }
    // Mark as acted on
    try {
      await fetch('http://localhost:8765/api/proactive/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ suggestion_id: suggestion.id, action: 'act' }),
      })
    } catch (e) {}
    addLog(`[Proactive] Acting: ${firstAction.label} → ${firstAction.command}`)
    setProactiveBanner(null)
    setProactiveSuggestions(prev => prev.filter(s => s.id !== suggestion.id))
    await handleCommand(firstAction.command)
  }

  /**
   * The CORE function: send a command to the brain, stream its thoughts,
   * and update the UI as the LLM reasons + tools execute.
   */
  async function handleCommand(text) {
    if (!text || !text.trim()) return
    const userMsg = { role: 'user', text, timestamp: Date.now() }
    setMessages(prev => [...prev, userMsg])
    addLog(`[User] ${text}`)

    // Reset brain state
    setThoughts('')
    setIsStreaming(true)
    setToolCalls([])
    setRawLlmOutput('')
    setBrainLatency(0)
    setState('thinking')

    try {
      const res = await fetch('http://localhost:8765/api/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: text }),
      })
      const data = await res.json()

      // Animate the LLM response in - simulate streaming by typing it out
      if (data.brain) {
        setBrainTier(`🧠 ${data.brain.tier === 'llm' ? 'LLM Reasoning' : data.brain.tier}`)
        setBrainLatency(data.brain.latency_ms || 0)
        setRawLlmOutput(data.brain.raw || '')
        if (data.brain.thoughts) {
          // If the LLM shared its thoughts, show those
          await typeOut(data.brain.thoughts, setThoughts, 12)
        }
      }

      setIsStreaming(false)

      // Show each tool call as a card as it executes
      const stepCount = data.steps || 0
      if (stepCount > 0 && data.logs) {
        // Parse tool calls from logs (we don't have a structured array, so reconstruct)
        setState('executing')
        const logToolCalls = data.logs.filter(l => l.startsWith('[Executor] brain.')).map(l => {
          const m = l.match(/brain\.(\w+) -> success=(\w+)/)
          if (m) return { tool: m[1], success: m[2] === 'True' }
          return null
        }).filter(Boolean)
        for (let i = 0; i < logToolCalls.length; i++) {
          setToolCalls(prev => [...prev, { tc: logToolCalls[i], result: null, isActive: true }])
          await sleep(300)
          setToolCalls(prev => prev.map((c, idx) =>
            idx === i ? { ...c, isActive: false, result: { success: logToolCalls[i].success, message: data.message } } : c
          ))
        }
      }

      // Final response
      setState('speaking')
      setMessages(prev => [...prev, {
        role: 'assistant',
        text: data.message,
        timestamp: Date.now(),
        brain: data.brain,
        tier: data.brain?.tier || 'regex',
      }])
      addLog(`[OMNI] ${data.message.slice(0, 120)}`)
      if (data.logs) data.logs.forEach(l => addLog(l))

      // After speaking, return to listening
      setTimeout(() => {
        setState(isMuted ? 'idle' : 'listening')
        setToolCalls([])
      }, 3000)
    } catch (e) {
      setIsStreaming(false)
      setState('error')
      addLog(`[Error] ${e.message}`)
      setTimeout(() => setState('idle'), 3000)
    }
  }

  async function toggleMic() {
    if (isMuted) {
      setIsMuted(false)
      setState('listening')
      addLog('[Mic] Unmuted - waiting for input')
      // Start push-to-talk recording on backend
      try {
        await fetch('http://localhost:8765/api/ptt/start', { method: 'POST' })
        addLog('[Mic] PTT recording started - speak now')
      } catch (e) {
        addLog(`[Mic] PTT start failed: ${e.message}`)
      }
    } else {
      setIsMuted(true)
      setState('idle')
      addLog('[Mic] Muted - stopping recording')
      // Stop recording, transcribe, and execute
      try {
        const res = await fetch('http://localhost:8765/api/ptt/stop', { method: 'POST' })
        const data = await res.json()
        if (data.text && data.text.trim()) {
          addLog(`[STT] Heard: "${data.text}"`)
          await handleCommand(data.text)
        } else {
          addLog(`[STT] No speech detected (RMS ${(data.rms || 0).toFixed(4)})`)
        }
      } catch (e) {
        addLog(`[Mic] PTT stop failed: ${e.message}`)
      }
    }
  }

  const stateStyle = STATE_STYLES[state] || STATE_STYLES.idle

  return (
    <div className={`relative w-screen h-screen overflow-hidden transition-colors duration-1000 select-none ${
      state === 'idle' || state === 'booting' ? 'bg-[#000000]' :
      'bg-gradient-to-br from-[#020617] via-[#0F172A] to-[#020617]'
    }`}>

      {/* Subtle radial glow when active */}
      {state !== 'idle' && state !== 'booting' && (
        <div className="absolute inset-0 opacity-30 pointer-events-none" style={{
          backgroundImage: `radial-gradient(circle at 50% 50%, ${stateStyle.color}22 0%, transparent 60%)`,
          transition: 'background-image 0.5s',
        }} />
      )}

      {/* Top bar */}
      <div className="absolute top-0 inset-x-0 p-5 flex items-center justify-between z-30 pointer-events-none">
        <button
          onClick={() => setShowHistory(true)}
          className="pointer-events-auto flex items-center gap-2 px-3.5 py-2 rounded-full border border-white/10 bg-black/40 hover:bg-white/10 text-white/70 hover:text-white transition-all text-xs tracking-widest font-mono backdrop-blur-md"
        >
          <span>📜</span><span>HISTORY</span>
        </button>
        <div className="flex items-center gap-3 pointer-events-auto">
          <div className="px-3 py-1.5 rounded-full bg-black/40 border border-white/10 backdrop-blur-md text-[10px] font-mono tracking-widest text-white/60">
            {brainTier}
            {brainLatency > 0 && <span className="ml-1.5 text-orange-300">{Math.round(brainLatency)}ms</span>}
          </div>
          <button
            onClick={() => setShowLogs(true)}
            className="flex items-center gap-2 px-3.5 py-2 rounded-full border border-white/10 bg-black/40 hover:bg-white/10 text-white/70 hover:text-white transition-all text-xs tracking-widest font-mono backdrop-blur-md"
          >
            <span>💻</span><span>LOGS</span>
          </button>
          <button
            onClick={() => setShowSettings(true)}
            className="p-2.5 rounded-full border border-white/10 bg-black/40 hover:bg-white/10 text-white/70 hover:text-white transition-all text-sm backdrop-blur-md"
          >
            ⚙️
          </button>
        </div>
      </div>

      {/* CENTER: Orb + thought stream + tool calls */}
      <div className="absolute inset-0 flex flex-col items-center justify-center z-10">
        <div className="w-full max-w-3xl h-[350px]">
          <CinematicStage state={state} rms={rms} />
        </div>

        {/* Live thought stream - the LLM's actual tokens */}
        <div ref={thoughtsRef} className="w-full max-w-2xl px-6 mt-2 max-h-[80px] overflow-y-auto">
          <ThinkingStream tokens={thoughts} isStreaming={isStreaming} />
        </div>

        {/* Tool call cards - real-time as the LLM dispatches tools */}
        {toolCalls.length > 0 && (
          <div className="w-full max-w-2xl px-6 mt-3 space-y-1.5">
            {toolCalls.map((c, i) => (
              <ToolCallCard key={i} tc={c.tc} result={c.result} isActive={c.isActive} />
            ))}
          </div>
        )}

        {/* PROACTIVE-UI: floating suggestion banner - the AGI interrupts with helpful nudges */}
        {proactiveBanner && (
          <div className="w-full max-w-2xl px-6 mt-4">
            <div className="border border-amber-500/40 bg-gradient-to-br from-amber-500/10 to-orange-500/5 rounded-2xl p-4 backdrop-blur-md shadow-2xl shadow-amber-500/20">
              <div className="flex items-start gap-3">
                <div className="text-2xl">💡</div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <div className="text-xs font-mono tracking-widest text-amber-400 font-bold uppercase">
                      OMNI Proactive
                    </div>
                    <div className="text-[10px] font-mono text-white/40">
                      {proactiveBanner.category} · priority {proactiveBanner.priority}
                    </div>
                  </div>
                  <div className="mt-1 text-sm text-white font-medium">
                    {proactiveBanner.title}
                  </div>
                  <div className="mt-0.5 text-xs text-white/70 leading-relaxed">
                    {proactiveBanner.body}
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {proactiveBanner.actions && proactiveBanner.actions.map((a, i) => (
                      <button
                        key={i}
                        onClick={() => actOnProactive(proactiveBanner)}
                        className="px-3 py-1.5 text-[11px] font-mono rounded-full bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 border border-amber-500/30 transition-all"
                      >
                        {a.label}
                      </button>
                    ))}
                    <button
                      onClick={() => dismissProactive(proactiveBanner.id)}
                      className="px-3 py-1.5 text-[11px] font-mono rounded-full bg-white/5 hover:bg-white/10 text-white/60 border border-white/10 transition-all"
                    >
                      Dismiss
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Status line */}
        <div className="mt-4 flex flex-col items-center gap-1 z-20">
          <div
            className="text-sm font-mono tracking-[0.3em] uppercase transition-all duration-300"
            style={{ color: stateStyle.color }}
          >
            {stateStyle.label}{state === 'thinking' ? '…' : state === 'listening' ? '…' : state === 'speaking' ? '…' : ''}
          </div>
          <div className="text-[10px] font-mono text-white/30 tracking-wider">
            OMNI V3 • LLM BRAIN ACTIVE
          </div>
        </div>
      </div>

      {/* Bottom controls */}
      <div className="absolute bottom-10 inset-x-0 flex flex-col items-center justify-center gap-4 z-30">
        <button
          onClick={toggleMic}
          className={`flex items-center gap-3 px-8 py-4 rounded-full font-mono text-xs tracking-[0.25em] transition-all duration-300 shadow-2xl backdrop-blur-lg border ${
            !isMuted
              ? 'bg-sky-500/20 text-sky-400 border-sky-500/50 shadow-sky-500/30 scale-105 animate-pulse'
              : 'bg-white/5 text-white/80 border-white/10 hover:border-white/20 hover:bg-white/10'
          }`}
        >
          <span className="text-base">{!isMuted ? '🎙️' : '🔇'}</span>
          <span>{!isMuted ? 'LISTENING (Speak)' : 'PRESS TO SPEAK'}</span>
        </button>

        <form onSubmit={(e) => { e.preventDefault(); handleCommand(inputText); setInputText(''); }} className="w-full max-w-md px-4">
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder="Ask the brain anything..."
            className="w-full bg-black/50 border border-white/10 focus:border-orange-500/50 rounded-full px-5 py-2.5 text-xs text-white placeholder-white/30 font-mono outline-none backdrop-blur-md transition-all text-center"
          />
        </form>
      </div>

      {/* HISTORY drawer */}
      {showHistory && (
        <div className="absolute inset-0 bg-black/60 backdrop-blur-sm z-40 flex justify-start">
          <div className="w-full max-w-md h-full bg-[#090D16] border-r border-white/10 flex flex-col shadow-2xl p-6">
            <div className="flex items-center justify-between pb-4 border-b border-white/10 mb-4">
              <div className="text-xs font-mono tracking-widest text-sky-400 font-bold">📜 HISTORY</div>
              <button onClick={() => setShowHistory(false)} className="text-white/50 hover:text-white text-sm font-mono">✕</button>
            </div>
            <div className="flex-1 overflow-y-auto space-y-3 pr-2">
              {messages.length === 0 ? (
                <div className="text-xs text-white/40 font-mono text-center py-10">No turns yet.</div>
              ) : (
                messages.map((m, idx) => (
                  <div key={idx} className={`p-3 rounded-2xl border text-xs leading-relaxed ${
                    m.role === 'user'
                      ? 'bg-sky-500/10 border-sky-500/20 text-sky-200 ml-6'
                      : 'bg-white/5 border-white/10 text-white mr-6'
                  }`}>
                    <div className="text-[10px] font-mono opacity-50 mb-1 flex items-center gap-2">
                      {m.role === 'user' ? '👤 YOU' : `🤖 OMNI ${m.tier === 'llm' ? '· LLM' : m.tier === 'regex' ? '· REGEX' : ''}`}
                      {m.brain?.latency_ms > 0 && <span className="text-orange-300">· {Math.round(m.brain.latency_ms)}ms</span>}
                    </div>
                    <div>{m.text}</div>
                  </div>
                ))
              )}
            </div>
          </div>
          <div className="flex-1" onClick={() => setShowHistory(false)} />
        </div>
      )}

      {/* LOGS drawer */}
      {showLogs && (
        <div className="absolute inset-0 bg-black/60 backdrop-blur-sm z-40 flex justify-end">
          <div className="flex-1" onClick={() => setShowLogs(false)} />
          <div className="w-full max-w-xl h-full bg-[#050B14] border-l border-white/10 flex flex-col shadow-2xl p-6">
            <div className="flex items-center justify-between pb-4 border-b border-white/10 mb-4">
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono tracking-widest text-emerald-400 font-bold">💻 LIVE LOGS</span>
                {rawLlmOutput && (
                  <details className="ml-2">
                    <summary className="text-[10px] font-mono text-orange-400 cursor-pointer">view raw LLM</summary>
                    <pre className="text-[10px] font-mono text-orange-300/70 mt-2 p-2 bg-black/50 rounded whitespace-pre-wrap">{rawLlmOutput}</pre>
                  </details>
                )}
              </div>
              <button onClick={() => setShowLogs(false)} className="text-white/50 hover:text-white text-sm font-mono">✕</button>
            </div>
            <div ref={logRef} className="flex-1 overflow-y-auto font-mono text-[11px] space-y-1 text-white/80 bg-black/80 p-4 rounded-xl border border-white/5 pr-2 select-text">
              {logs.map((log, idx) => (
                <div key={idx} className={`leading-relaxed border-l-2 pl-2.5 py-0.5 ${
                  log.includes('[Brain]') || log.includes('[Planner]') ? 'border-orange-500 text-orange-300' :
                  log.includes('[Executor]') ? 'border-emerald-500 text-emerald-300' :
                  log.includes('[Monitor]') ? 'border-amber-500 text-amber-300' :
                  log.includes('[Evaluator]') ? 'border-purple-500 text-purple-300' :
                  log.includes('[Error]') ? 'border-red-500 text-red-300' :
                  'border-white/20 text-white/70'
                }`}>{log}</div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* SETTINGS modal */}
      {showSettings && (
        <div className="absolute inset-0 bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-6">
          <div className="w-full max-w-md bg-[#0D1424] border border-white/10 rounded-3xl p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-white/10 pb-4">
              <div className="text-sm font-mono tracking-widest text-white font-bold">⚙️ SYSTEM</div>
              <button onClick={() => setShowSettings(false)} className="text-white/50 hover:text-white font-mono text-sm">✕</button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="text-[10px] font-mono text-white/50 tracking-widest uppercase">Brain Status</label>
                <div className="mt-1 px-3 py-2 rounded-lg bg-orange-500/10 border border-orange-500/20 text-xs font-mono text-orange-200">
                  {brainTier} {brainLatency > 0 && `· ${Math.round(brainLatency)}ms`}
                </div>
              </div>
              <div>
                <label className="text-[10px] font-mono text-white/50 tracking-widest uppercase">Model</label>
                <div className="mt-1 px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-xs font-mono text-white/70">
                  Qwen2.5-1.5B-Instruct Q4_K_M (1.1GB GGUF)
                </div>
              </div>
              <div>
                <label className="text-[10px] font-mono text-white/50 tracking-widest uppercase">Storage</label>
                <div className="mt-1 px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-xs font-mono text-white/70">
                  data/ · memory.db · chroma · skills/
                </div>
              </div>
            </div>
            <button onClick={() => setShowSettings(false)} className="w-full py-3 rounded-xl bg-orange-500 hover:bg-orange-400 text-black font-mono font-bold text-xs tracking-widest">
              CLOSE
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)) }
async function typeOut(text, setText, ms = 12) {
  // Type out the text character by character for a "thinking" animation
  let acc = ''
  for (const ch of text) {
    acc += ch
    setText(acc)
    await sleep(ms)
  }
}
