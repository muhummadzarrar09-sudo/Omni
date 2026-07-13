<script>
  import { createEventDispatcher } from "svelte";
  export let micMuted = false;
  export let outputMode = "auto";
  
  const dispatch = createEventDispatcher();

  let sttEngine = "auto";
  let ttsVoice = "af_sarah";
  let wakeWordEnabled = true;
  let vadThreshold = 0.003;
  let noCloud = false;

  function handleMicToggle() {
    dispatch("micToggle");
  }

  function handleOutputModeChange(event) {
    dispatch("outputModeChange", event.target.value);
  }
</script>

<div class="settings-panel">
  <h3>⚙️ Settings - Whisper Flow Style + Drag-Drop</h3>
  
  <div class="setting-group">
    <h4>🎤 Voice I/O</h4>
    <label>
      <input type="checkbox" bind:checked={micMuted} on:change={handleMicToggle} />
      Mic Muted
    </label>
    <label>
      Wake Word "Hey OMNI" Always-On
      <input type="checkbox" bind:checked={wakeWordEnabled} />
    </label>
    <label>
      VAD Threshold (Sensitivity)
      <input type="range" min="0.001" max="0.01" step="0.001" bind:value={vadThreshold} />
      {vadThreshold}
    </label>
    <label>
      PTT Key: V (toggle)
      <button>Change</button>
    </label>
    <label>
      Mic Device: Realtek (preferred, not Sound Mapper)
      <select><option>Realtek Audio</option><option>Sound Mapper (virtual)</option></select>
    </label>
  </div>

  <div class="setting-group">
    <h4>🧠 STT - 4-Tier for Accessibility</h4>
    <label>
      Engine:
      <select bind:value={sttEngine}>
        <option value="auto">Auto (RealtimeSTT → Vosk → Google → Whisper)</option>
        <option value="realtimestt">RealtimeSTT (most robust)</option>
        <option value="vosk">Vosk (offline 50MB)</option>
        <option value="google">Google (cloud reliable)</option>
        <option value="faster_whisper">Faster-Whisper</option>
      </select>
    </label>
    <label>
      <input type="checkbox" bind:checked={noCloud} />
      100% Offline (disable Google cloud, OMNI_NO_CLOUD=1)
    </label>
  </div>

  <div class="setting-group">
    <h4>🔊 TTS - 3-Tier Never Fails</h4>
    <label>
      Voice:
      <select bind:value={ttsVoice}>
        <option value="af_sarah">af_sarah - Bright & warm (demo)</option>
        <option value="bf_gemma">bf_gemma - British elegant</option>
        <option value="am_michael">am_michael - Deep steady</option>
      </select>
    </label>
  </div>

  <div class="setting-group">
    <h4>💬 Output Mode (Your Request)</h4>
    <label>
      Mode:
      <select value={outputMode} on:change={handleOutputModeChange}>
        <option value="auto">Auto: Short near cursor, long in widget</option>
        <option value="tagline">Tagline in widget area (longer)</option>
        <option value="cursor">Dialog near cursor (short <50 chars)</option>
        <option value="both">Both: Thinking near cursor, final in widget</option>
      </select>
    </label>
    <p style="font-size:10px; color:rgba(255,255,255,0.5);">Toggle as you requested: Tagline in widget vs dialog near cursor for thinking + short output</p>
  </div>

  <div class="setting-group">
    <h4>🎨 Whisper Flow Style Features</h4>
    <ul style="font-size:11px;">
      <li>Drag & drop audio/video files into bottom widget to transcribe</li>
      <li>Batch processing multiple files</li>
      <li>Auto-downloads missing models with progress bar</li>
      <li>Real-time console output while transcription</li>
      <li>Custom modes per app: Slack, email, code, terminal style</li>
    </ul>
  </div>

  <div class="setting-group">
    <h4>🧠 LLM - Multi-Tier + Turbo</h4>
    <label>Provider: Ollama (local) / OpenAI / Anthropic</label>
    <label>Model: llama3.1:8b / deepseek-r1:8b / llava:7b</label>
    <label>HF_TOKEN: <input type="password" placeholder="hf_xxx for gated Llama 3.1" /></label>
  </div>

  <div class="setting-group">
    <h4>📁 Data Unanimous Inside Project</h4>
    <p style="font-size:10px;">All data in ./data/ (migrated from ~/.omni_v2, deleted from workspace root as requested)</p>
    <ul style="font-size:10px;">
      <li>data/memory.db - SQLite</li>
      <li>data/chroma/ - Vector DB</li>
      <li>data/models/ - GGUF models via HF_TOKEN</li>
      <li>data/screenshots/ - Screenshots</li>
      <li>data/logs/ - Logs + commands.log audit trail</li>
    </ul>
  </div>
</div>

<style>
  .settings-panel {
    font-size: 12px;
  }

  .setting-group {
    background: rgba(0,0,0,0.3);
    padding: 10px;
    margin: 10px 0;
    border-radius: 5px;
    border: 1px solid rgba(0,200,255,0.2);
  }

  .setting-group h4 {
    margin: 0 0 10px 0;
    color: cyan;
    font-size: 14px;
  }

  label {
    display: block;
    margin: 8px 0;
    color: white;
  }

  input, select, button {
    background: rgba(0,0,0,0.5);
    border: 1px solid rgba(0,200,255,0.3);
    color: white;
    padding: 5px;
    border-radius: 3px;
    margin-left: 10px;
  }
</style>
