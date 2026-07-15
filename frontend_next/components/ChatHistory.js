'use client'

export default function ChatHistory({ messages, onClear }) {
  return (
    <div className="neu p-5 flex flex-col h-full">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2 flex-wrap">
          <div className="text-[9px] font-extrabold tracking-[2px] text-[#A0AEC0]">💬 CHAT & ORCHESTRATION</div>
          <span className="bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded-full text-[9px] font-semibold border border-emerald-500/30">🔒 OMNI-Profile Isolated</span>
          <span className="bg-cyan-500/20 text-cyan-400 px-2 py-0.5 rounded-full text-[9px] font-semibold border border-cyan-500/30">✨ Proactive Polling Active</span>
          <span className="bg-purple-500/20 text-purple-300 px-2 py-0.5 rounded-full text-[9px] font-semibold border border-purple-500/30">🧠 GTX 1050 Ti GGUF</span>
        </div>
        <button onClick={onClear} className="neu-button small text-[10px] py-1 px-2.5 shrink-0">🗑️ Clear</button>
      </div>
      
      <div className="flex-1 overflow-y-auto space-y-3 pr-1" style={{ maxHeight: '65vh' }}>
        {messages.length === 0 && (
          <div className="neu-inset p-4 rounded-[12px] text-[11px] leading-[1.6] text-[#A0AEC0]">
            No messages yet. Try demo buttons or type a command.

            Your mic RMS 0.014 = LOUD, mic works. -9999 fixed via sounddevice primary.

            Try: "open github" → opens in isolated Chrome profile without email.
          </div>
        )}
        
        {messages.map((msg, i) => (
          <div key={i} className={`${msg.role === 'user' ? 'neu-sm' : 'neu-inset'} p-3 rounded-[12px]`}>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[10px] font-bold tracking-[1px]" style={{ color: msg.role === 'user' ? '#38BDF8' : '#4ADE80' }}>
                {msg.role === 'user' ? '👤 YOU' : '🤖 OMNI'}
              </span>
              <span className="text-[9px] text-[#6B7280]">{new Date(msg.timestamp).toLocaleTimeString()}</span>
            </div>
            <div className="text-[12px] leading-[1.5] whitespace-pre-wrap text-[#E2E8F0]">{msg.text}</div>
            {msg.logs && (
              <div className="mt-2 space-y-1">
                {msg.logs.slice(0,4).map((log, j) => (
                  <div key={j} className="text-[9px] font-mono text-[#A0AEC0] opacity-80">{log.substring(0,100)}</div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
