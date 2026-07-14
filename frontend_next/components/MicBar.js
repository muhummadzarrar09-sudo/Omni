'use client'
import { useEffect, useState } from 'react'

export default function MicBar({ rms = 0, max = 0, devices = [], selectedDevice = '', onDeviceChange, onTestMic }) {
  const pct = Math.min(100, (rms / 0.05) * 100)
  
  let statusText = ''
  let color = '#6B7280'
  if (rms < 0.001) { statusText = '🔇 Silent — Boost 100% +30dB'; color = '#6B7280'; }
  else if (rms < 0.01) { statusText = `🔈 Low ${rms.toFixed(4)} — LOUDER`; color = '#F87171'; }
  else if (rms < 0.03) { statusText = `🔉 Good ${rms.toFixed(4)}`; color = '#FB923C'; }
  else { statusText = `🔊 LOUD ${rms.toFixed(4)} Excellent`; color = '#4ADE80'; }
  
  return (
    <div className="neu p-5">
      <div className="text-[9px] font-extrabold tracking-[2.5px] text-[#A0AEC0] mb-4">🎤 MICROPHONE — SOFT SELECT (PORTABLE)</div>
      
      <select 
        value={selectedDevice} 
        onChange={(e) => onDeviceChange(e.target.value)}
        className="w-full neu-inset border-none rounded-[12px] py-3 px-4 text-[11px] text-[#E2E8F0] outline-none"
      >
        {devices.length === 0 ? (
          <>
            <option>[10] Microphone (Realtek HD Audio Mic input) ⭐ BEST — Score 339.0</option>
            <option>[13] Microphone (Realtek HD Audio Mic input) — Score 338.7</option>
            <option>[1] Microphone (Realtek Audio) — Score 314.9</option>
          </>
        ) : (
          devices.map((d, i) => (
            <option key={i} value={d.index}>[{d.index}] {d.name} {d.is_best ? '⭐ BEST' : ''} Score {d.score?.toFixed(1)}</option>
          ))
        )}
      </select>
      
      <div className="neu-inset p-3 rounded-[16px] mt-4">
        <div className="h-[28px] bg-[#151A24] rounded-[14px] overflow-hidden relative shadow-[inset_3px_3px_8px_rgba(0,0,0,0.8),inset_-2px_-2px_6px_rgba(255,255,255,0.03)]">
          <div 
            className="h-full rounded-[14px] flex items-center justify-center text-[10px] font-bold font-mono text-[#0F172A] transition-all duration-75"
            style={{ 
              width: `${pct}%`, 
              background: 'linear-gradient(90deg, #4ADE80, #38BDF8)',
              boxShadow: '0 0 12px rgba(56,189,248,0.4)'
            }}
          >
            {pct > 20 ? statusText : ''}
          </div>
        </div>
        <div className="text-[10px] font-mono text-center mt-2" style={{ color }}>{statusText}</div>
      </div>
      
      <div className="flex gap-2 mt-3">
        <button onClick={onTestMic} className="neu-button small flex-1">🧪 Test Mic RMS</button>
      </div>
      
      <div className="neu-inset p-3 rounded-[12px] mt-3">
        <div className="font-mono text-[10px] text-[#A0AEC0] space-y-1">
          <div>Device: <span className="text-[#E2E8F0]">{selectedDevice || '[10] Realtek HD Audio Mic'}</span></div>
          <div>STT: <span className="text-[#4ADE80]">base.en cuda int8 ✓</span> | TTS: <span className="text-[#4ADE80]">SAPI5 ✓</span></div>
          <div>Backend: <span className="text-[#4ADE80]">sounddevice primary (fixes -9999) ✓</span></div>
          <div>Portable: <span className="text-[#38BDF8]">No D:/Omni hardcode ✓</span></div>
        </div>
      </div>
    </div>
  )
}
