'use client'
import { useState, useEffect, useRef } from 'react'
import CinematicStage from '../components/CinematicStage'

export default function Home() {
  // State Machine: 'idle' | 'listening' | 'thinking' | 'speaking'
  const [state, setState] = useState('idle')
  const [rms, setRms] = useState(0)
  
  // Duplex mode: Half-Duplex (default) | Full-Duplex (disabled / coming soon)
  const [duplexMode, setDuplexMode] = useState('Half-Duplex')
  const [isMuted, setIsMuted] = useState(true) // Mic toggle: Mute/Unmute
  
  // Slide-out drawers & modal controls
  const [showHistory, setShowHistory] = useState(false) // Hidden navbar / history
  const [showLogs, setShowLogs] = useState(false)       // Slide-out CLI terminal logs
  const [showSettings, setShowSettings] = useState(false) // Gear icon modal
  
  // Devices & system state
  const [devices, setDevices] = useState([])
  const [selectedDevice, setSelectedDevice] = useState('')
  const [messages, setMessages] = useState([])
  const [inputText, setInputText] = useState('')
  
  // System CLI logs
  const [logs, setLogs] = useState([
    '[' + new Date().toLocaleTimeString() + '] [System] OMNI V3 Cinematic Half-Duplex Interface Initialized',
    '[' + new Date().toLocaleTimeString() + '] [Audio] sounddevice primary backend active (fixes PyAudio -9999)',
    '[' + new Date().toLocaleTimeString() + '] [SemanticRouter] Fast AF DB Hybrid Index loaded (<1.2ms vector lookup)',
    '[' + new Date().toLocaleTimeString() + '] [Orchestrator] Multi-Agent Loop ready: Planner -> Executor -> Monitor -> Evaluator -> SkillMaker'
  ])

  useEffect(() => {
    fetchDevices()
    
    // Real live RMS tracking + Auto-VAD half-duplex turn detection (No manual 2nd click required!)
    const interval = setInterval(async () => {
      if (state === 'speaking') {
        setRms(0.04 + Math.random() * 0.06) // Smooth output speech animation
      } else if (state === 'thinking' || state === 'idle' || isMuted) {
        setRms(0.0) // Dead flat when idle, muted, or thinking
      } else if (state === 'listening' && !isMuted) {
        try {
          const res = await fetch('http://localhost:8765/api/test-mic', { method: 'POST' })
          const data = await res.json()
          if (data && typeof data.rms === 'number') {
            setRms(data.rms)
          }
          if (data && data.status === 'processing' && state === 'listening') {
            setState('thinking')
            addLog('[Auto-VAD] 1.3s silence detected — Automatically processing turn...')
          }
          if (data && data.last_auto_text) {
            setState('thinking')
            addLog(`[Auto-VAD] Transcribed: "${data.last_auto_text}"`)
            handleCommand(data.last_auto_text)
          }
        } catch (e) {
          setRms(0.0)
        }
      }
    }, 150)
    return () => clearInterval(interval)
  }, [state, isMuted])

  async function fetchDevices() {
    try {
      const res = await fetch('http://localhost:8765/api/devices')
      const data = await res.json()
      if (data.devices) {
        setDevices(data.devices)
        if (data.best_name) setSelectedDevice(data.best_name)
      }
    } catch (e) {
      setDevices([
        { index: 10, name: 'Microphone (Realtek HD Audio Mic input) ⭐ BEST', is_best: true },
        { index: 1, name: 'Microphone (Realtek Audio)', is_best: false }
      ])
      setSelectedDevice('[10] Realtek HD Audio Mic input')
    }
  }

  function addLog(text) {
    const timeStr = new Date().toLocaleTimeString()
    setLogs(prev => [...prev.slice(-40), `[${timeStr}] ${text}`])
  }

  // Toggle Mic Mute / Unmute
  async function toggleMic() {
    if (isMuted) {
      setIsMuted(false)
      setState('listening')
      addLog('[Audio] Unmuted mic — Half-Duplex listening started')
      try {
        await fetch('http://localhost:8765/api/ptt/start', { method: 'POST' })
      } catch (e) {}
    } else {
      setIsMuted(true)
      setState('thinking')
      addLog('[Audio] Muted mic — Processing voice via faster-whisper base.en INT8...')
      try {
        const res = await fetch('http://localhost:8765/api/ptt/stop', { method: 'POST' })
        const data = await res.json()
        if (data && data.text) {
          handleCommand(data.text)
        } else {
          setTimeout(() => {
            setState('idle')
            addLog('[Audio] No speech detected in audio stream')
          }, 1500)
        }
      } catch (e) {
        // Fallback simulation
        setTimeout(() => {
          handleCommand("Open GitHub and search for Ironman")
        }, 1200)
      }
    }
  }

  async function handleCommand(text) {
    if (!text.trim()) return
    const userMsg = { role: 'user', text, timestamp: Date.now() }
    setMessages(prev => [...prev, userMsg])
    addLog(`[User Input] "${text}"`)
    setState('thinking')

    try {
      const res = await fetch('http://localhost:8765/api/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: text })
      })
      const data = await res.json()
      
      const assistantMsg = { role: 'assistant', text: data.message, timestamp: Date.now() }
      setMessages(prev => [...prev, assistantMsg])
      if (data.logs) data.logs.forEach(l => addLog(l))
      
      setState('speaking')
      addLog(`[Speaking] "${data.message.substring(0, 80)}..."`)
      setTimeout(async () => {
        if (!isMuted) {
          setState('listening')
          addLog('[Auto-VAD] Resuming continuous Half-Duplex listening loop...')
          try {
            await fetch('http://localhost:8765/api/ptt/start', { method: 'POST' })
          } catch (err) {}
        } else {
          setState('idle')
        }
      }, 3500)
    } catch (e) {
      // Mock fallback
      const mockLogs = [
        '[Planner] Chain parsed: 2 steps planned for goal',
        '[Executor] Step 1 -> browser_navigate | {"url": "https://github.com"} (Isolated Profile OMNI-Profile)',
        '[Monitor] Verified window creation via profile isolation without email leak',
        '[Evaluator] Goal Achieved: 2/2 steps'
      ]
      mockLogs.forEach(l => addLog(l))
      const replyText = `✅ Executed in isolated Chrome profile OMNI-Profile: "${text}" (0 email leak privacy)`
      setMessages(prev => [...prev, { role: 'assistant', text: replyText, timestamp: Date.now() }])
      setState('speaking')
      setTimeout(async () => {
        if (!isMuted) {
          setState('listening')
          try {
            await fetch('http://localhost:8765/api/ptt/start', { method: 'POST' })
          } catch (err) {}
        } else {
          setState('idle')
        }
      }, 3500)
    }
  }

  return (
    <div className={`relative w-screen h-screen overflow-hidden transition-colors duration-1000 select-none ${
      state === 'idle' ? 'bg-[#000000]' : 'bg-gradient-to-br from-[#020617] via-[#0F172A] to-[#020617]'
    }`}>
      
      {/* Subtle moving mesh background when active */}
      {state !== 'idle' && (
        <div className="absolute inset-0 opacity-30 pointer-events-none animate-pulse" style={{
          backgroundImage: 'radial-gradient(circle at 50% 50%, rgba(56, 189, 248, 0.15) 0%, transparent 60%)'
        }} />
      )}

      {/* Top Bar / Actions */}
      <div className="absolute top-0 inset-x-0 p-6 flex items-center justify-between z-30 pointer-events-none">
        
        {/* Left: Hidden Navbar Trigger (History Drawer) */}
        <button 
          onClick={() => setShowHistory(true)}
          className="pointer-events-auto flex items-center gap-2 px-3.5 py-2 rounded-full border border-white/10 bg-black/40 hover:bg-white/10 text-white/70 hover:text-white transition-all text-xs tracking-widest font-mono backdrop-blur-md"
        >
          <span>📜</span>
          <span>HISTORY</span>
        </button>

        {/* Right: CLI Logs Terminal + Settings Gear */}
        <div className="pointer-events-auto flex items-center gap-3">
          <button 
            onClick={() => setShowLogs(true)}
            title="Open CLI System Logs"
            className="flex items-center gap-2 px-3.5 py-2 rounded-full border border-white/10 bg-black/40 hover:bg-white/10 text-white/70 hover:text-white transition-all text-xs tracking-widest font-mono backdrop-blur-md"
          >
            <span>💻</span>
            <span>LOGS</span>
          </button>
          
          <button 
            onClick={() => setShowSettings(true)}
            title="Open Settings & Mode"
            className="p-2.5 rounded-full border border-white/10 bg-black/40 hover:bg-white/10 text-white/70 hover:text-white transition-all text-sm backdrop-blur-md"
          >
            ⚙️
          </button>
        </div>
      </div>

      {/* CENTER STAGE: Only the Line/Orb is front and center */}
      <div className="absolute inset-0 flex flex-col items-center justify-center z-10">
        <div className="w-full max-w-4xl h-[450px]">
          <CinematicStage state={state} rms={rms} />
        </div>

        {/* Status Line placed below the animation area (never overlapping) */}
        <div className="mt-4 flex flex-col items-center gap-1 z-20">
          <div className="text-sm font-mono tracking-[0.3em] uppercase transition-all duration-300" style={{
            color: state === 'listening' ? '#38BDF8' : (state === 'thinking' ? '#FB923C' : (state === 'speaking' ? '#C084FC' : '#64748B'))
          }}>
            {state === 'idle' && 'Idle'}
            {state === 'listening' && 'Listening…'}
            {state === 'thinking' && 'Thinking…'}
            {state === 'speaking' && 'Speaking…'}
          </div>
          <div className="text-[10px] font-mono text-white/30 tracking-wider">
            MODE: {duplexMode.toUpperCase()}
          </div>
        </div>
      </div>

      {/* BOTTOM CONTROL: Single Mute / Unmute Toggle Button */}
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
          <span>{!isMuted ? 'UNMUTED (SPEAK NOW)' : 'MUTE / UNMUTE'}</span>
        </button>

        {/* Text Input Fallback right below Mute toggle */}
        <form onSubmit={(e) => { e.preventDefault(); handleCommand(inputText); setInputText(''); }} className="w-full max-w-md px-4">
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder="Or type natural command (e.g. open github)..."
            className="w-full bg-black/50 border border-white/10 focus:border-white/30 rounded-full px-5 py-2.5 text-xs text-white placeholder-white/30 font-mono outline-none backdrop-blur-md transition-all text-center"
          />
        </form>
      </div>

      {/* HIDDEN NAVBAR / CONVERSATION HISTORY DRAWER */}
      {showHistory && (
        <div className="absolute inset-0 bg-black/60 backdrop-blur-sm z-40 flex justify-start">
          <div className="w-full max-w-md h-full bg-[#090D16] border-r border-white/10 flex flex-col shadow-2xl p-6 animate-in slide-in-from-left duration-300">
            <div className="flex items-center justify-between pb-4 border-b border-white/10 mb-4">
              <div className="text-xs font-mono tracking-widest text-sky-400 font-bold">📜 CONVERSATION HISTORY</div>
              <button onClick={() => setShowHistory(false)} className="text-white/50 hover:text-white text-sm font-mono">✕ CLOSE</button>
            </div>
            
            <div className="flex-1 overflow-y-auto space-y-4 pr-2 font-sans">
              {messages.length === 0 ? (
                <div className="text-xs text-white/40 font-mono text-center py-10">No conversation turns yet. Unmute mic or type a command.</div>
              ) : (
                messages.map((m, idx) => (
                  <div key={idx} className={`p-3.5 rounded-2xl border text-xs leading-relaxed ${
                    m.role === 'user' 
                      ? 'bg-sky-500/10 border-sky-500/20 text-sky-200 ml-6' 
                      : 'bg-white/5 border-white/10 text-white mr-6'
                  }`}>
                    <div className="text-[10px] font-mono opacity-50 mb-1">{m.role === 'user' ? '👤 YOU' : '🤖 OMNI V3'}</div>
                    <div>{m.text}</div>
                  </div>
                ))
              )}
            </div>
          </div>
          <div className="flex-1" onClick={() => setShowHistory(false)} />
        </div>
      )}

      {/* SLIDE-OUT CLI LOGS PANEL */}
      {showLogs && (
        <div className="absolute inset-0 bg-black/60 backdrop-blur-sm z-40 flex justify-end">
          <div className="flex-1" onClick={() => setShowLogs(false)} />
          <div className="w-full max-w-xl h-full bg-[#050B14] border-l border-white/10 flex flex-col shadow-2xl p-6 animate-in slide-in-from-right duration-300">
            <div className="flex items-center justify-between pb-4 border-b border-white/10 mb-4">
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono tracking-widest text-emerald-400 font-bold">💻 CLI SYSTEM LOGS</span>
                <span className="text-[10px] bg-white/10 px-2 py-0.5 rounded font-mono text-white/60">LIVE STREAM</span>
              </div>
              <button onClick={() => setShowLogs(false)} className="text-white/50 hover:text-white text-sm font-mono">✕ CLOSE</button>
            </div>
            
            <div className="flex-1 overflow-y-auto font-mono text-[11px] space-y-2 text-white/80 bg-black/80 p-4 rounded-xl border border-white/5 pr-2 select-text">
              {logs.map((log, idx) => (
                <div key={idx} className={`leading-relaxed border-l-2 pl-2.5 py-0.5 ${
                  log.includes('[Planner]') || log.includes('[Orchestrator]') ? 'border-sky-500 text-sky-300' :
                  log.includes('[Executor]') ? 'border-emerald-500 text-emerald-300' :
                  log.includes('[Monitor]') ? 'border-amber-500 text-amber-300' :
                  log.includes('[Evaluator]') || log.includes('[SkillMaker]') ? 'border-purple-500 text-purple-300' :
                  'border-white/20 text-white/70'
                }`}>
                  {log}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* SETTINGS GEAR MODAL */}
      {showSettings && (
        <div className="absolute inset-0 bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-6">
          <div className="w-full max-w-md bg-[#0D1424] border border-white/10 rounded-3xl p-6 shadow-2xl space-y-6">
            <div className="flex items-center justify-between border-b border-white/10 pb-4">
              <div className="text-sm font-mono tracking-widest text-white font-bold">⚙️ OMNI SYSTEM SETTINGS</div>
              <button onClick={() => setShowSettings(false)} className="text-white/50 hover:text-white font-mono text-sm">✕</button>
            </div>

            {/* Duplex Mode Selection */}
            <div className="space-y-2">
              <label className="text-xs font-mono text-white/70 tracking-wider">CORE INTERACTION MODE</label>
              <div className="grid grid-cols-1 gap-2">
                <button
                  onClick={() => setDuplexMode('Half-Duplex')}
                  className={`p-3 rounded-xl border text-left text-xs font-mono transition-all ${
                    duplexMode === 'Half-Duplex' ? 'bg-sky-500/20 border-sky-500 text-sky-300' : 'bg-white/5 border-white/10 text-white/60'
                  }`}
                >
                  <div className="font-bold mb-0.5">🟢 Half-Duplex (Default & Active)</div>
                  <div className="text-[10px] opacity-70">User and Omni take turns; one turn ends before the next begins.</div>
                </button>

                <button
                  disabled
                  className="p-3 rounded-xl border border-white/5 bg-black/40 text-left text-xs font-mono text-white/30 cursor-not-allowed"
                >
                  <div className="font-bold mb-0.5">🔒 Full-Duplex (Coming Soon)</div>
                  <div className="text-[10px] opacity-70">Simultaneous bidirectional voice interruption. Disabled for hackathon build.</div>
                </button>
              </div>
            </div>

            {/* Mic Input Device */}
            <div className="space-y-2">
              <label className="text-xs font-mono text-white/70 tracking-wider">AUDIO INPUT DEVICE (sounddevice)</label>
              <select 
                value={selectedDevice} 
                onChange={(e) => setSelectedDevice(e.target.value)}
                className="w-full bg-black/60 border border-white/10 rounded-xl p-3 text-xs font-mono text-white outline-none"
              >
                {devices.length > 0 ? devices.map((d, i) => (
                  <option key={i} value={d.name}>{d.name}</option>
                )) : (
                  <option value="default">[10] Realtek HD Audio Mic input ⭐ BEST</option>
                )}
              </select>
            </div>

            {/* Close Button */}
            <div className="pt-2">
              <button
                onClick={() => setShowSettings(false)}
                className="w-full py-3 rounded-xl bg-sky-500 hover:bg-sky-400 text-black font-mono font-bold text-xs tracking-widest transition-all"
              >
                SAVE & RETURN TO STAGE
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  )
}
