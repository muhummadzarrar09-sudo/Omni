/* OMNI Mobile PWA — client logic
 * Drives: discovery (HTTP scan + QR), pairing, WebSocket chat,
 *         push-to-talk, thought stream, PWA install.
 *
 * No external dependencies. No build step. Pure ES2018.
 */
(() => {
  'use strict';

  // ---------- State ----------
  const state = {
    brains: new Map(),       // host:port -> { info, lastSeen }
    ws: null,
    brain: null,             // currently connected NetworkInfo
    paired: false,
    isRecording: false,
    mediaRecorder: null,
    audioChunks: [],
    pttStream: null,
    reconnectTimer: null,
    reconnectAttempts: 0,
    scanTimer: null,
    deferredPrompt: null,
    messages: [],            // session history
    pendingPttBlob: null,
    // Phase 5C: Location state
    geoWatchId: null,
    currentFix: null,        // { lat, lon, accuracy, ts }
    currentPlace: null,      // currently-inside place
    places: [],
    rules: [],
    sendingLoc: false,
    // Phase 5D: Notification state
    notifications: [],
    notifUnread: 0,
    deviceId: "pwa-" + Math.random().toString(36).slice(2, 10),
    pushSubscribed: false,
  };

  const STORAGE_KEY = 'omni-mobile-state-v1';

  // ---------- Persistence ----------
  function saveLocal() {
    try {
      const minimal = {
        brain: state.brain ? state.brain.to_dict_safe() : null,
        messages: state.messages.slice(-50),  // cap
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(minimal));
    } catch (e) { /* ignore quota */ }
  }

  function loadLocal() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      return JSON.parse(raw);
    } catch (e) { return null; }
  }

  // ---------- Screen routing ----------
  const $ = (id) => document.getElementById(id);
  const screens = ['boot', 'discover', 'pair', 'chat', 'geofence', 'notifications', 'notifPrefs', 'brainState'];
  function show(name) {
    for (const s of screens) {
      const el = $(s);
      if (el) el.hidden = (s !== name);
    }
  }

  // ---------- Toast ----------
  let toastTimer = null;
  function toast(msg, ms = 2200) {
    const el = $('toast');
    el.textContent = msg;
    el.hidden = false;
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { el.hidden = true; }, ms);
  }

  // ---------- Brain model helpers ----------
  function brainKey(b) { return `${b.host}:${b.port}`; }
  function brainEqual(a, b) { return a && b && a.host === b.host && a.port === b.port; }

  // Patch NetworkInfo with to_dict_safe for storage
  if (typeof NetworkInfo === 'undefined') {
    // We don't have a class; just attach to plain objects when received
  }
  function attachInfoMethods(info) {
    if (info && !info.to_dict_safe) {
      info.to_dict_safe = function () {
        return { name: info.name, host: info.host, port: info.port,
                 version: info.version, model: info.model,
                 capabilities: info.capabilities || [] };
      };
    }
    return info;
  }

  // ---------- Discovery (HTTP scan) ----------
  // Phones can't do UDP broadcast easily in browsers, so we use a different
  // strategy: ask the user to either scan a QR (zero ambiguity) or
  // enter host manually. We also try a set of common local subnets
  // via the backend's CORS-friendly HTTP /api/network/info endpoint.
  async function probeHttp(host, port, timeoutMs = 1200) {
    const url = `http://${host}:${port}/api/network/info`;
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), timeoutMs);
    try {
      const r = await fetch(url, { signal: ctrl.signal, mode: 'cors' });
      if (!r.ok) return null;
      const data = await r.json();
      const net = data.network || data;
      return attachInfoMethods({
        name: net.name || 'OMNI',
        host: net.host || host,
        port: net.port || port,
        version: net.version || 'unknown',
        model: net.model || 'unknown',
        capabilities: net.capabilities || net.caps || [],
      });
    } catch (e) { return null; }
    finally { clearTimeout(t); }
  }

  async function scanSubnet() {
    // Try common private ranges for the laptop. This is best-effort;
    // UDP broadcast mDNS is done by the laptop side, but browsers can't
    // receive UDP broadcasts. So we use HTTP probing on likely IPs.
    const candidates = [];
    const myIps = await guessMySubnet();
    for (const subnet of myIps) {
      // Try .1 (router) and .x where x is common laptop endings
      for (const last of [1, 2, 5, 10, 20, 42, 100, 105, 200]) {
        candidates.push(`${subnet}.${last}`);
      }
    }
    // Dedupe
    const uniq = [...new Set(candidates)];
    // Probe in parallel (limited)
    const batch = 16;
    for (let i = 0; i < uniq.length; i += batch) {
      const slice = uniq.slice(i, i + batch);
      const results = await Promise.all(slice.map(ip => probeHttp(ip, 8765, 800)));
      for (const r of results) {
        if (r) addBrain(r);
      }
    }
    renderBrains();
  }

  async function guessMySubnet() {
    // Not directly possible in browser, but we can use WebRTC trick
    // to get local IPs, then derive subnets.
    return new Promise((resolve) => {
      const ips = new Set();
      const timeout = setTimeout(() => resolve(['192.168.1', '192.168.0', '10.0.0']), 800);
      try {
        const pc = new RTCPeerConnection({ iceServers: [] });
        pc.createDataChannel('');
        pc.onicecandidate = (e) => {
          if (!e || !e.candidate || !e.candidate.candidate) return;
          const m = e.candidate.candidate.match(/(\d+\.\d+\.\d+)\.\d+/);
          if (m) ips.add(m[1]);
        };
        pc.createOffer().then(o => pc.setLocalDescription(o)).catch(() => {});
      } catch (e) { /* ignore */ }
      setTimeout(() => {
        clearTimeout(timeout);
        if (ips.size === 0) resolve(['192.168.1', '192.168.0', '10.0.0']);
        else resolve([...ips]);
      }, 900);
    });
  }

  function addBrain(info) {
    const key = brainKey(info);
    const existing = state.brains.get(key);
    state.brains.set(key, { info: attachInfoMethods(info), lastSeen: Date.now() });
  }

  function renderBrains() {
    const list = $('brainList');
    const items = [...state.brains.values()]
      .sort((a, b) => b.lastSeen - a.lastSeen);
    if (items.length === 0) {
      list.innerHTML = `
        <div class="empty-state">
          <div class="big">📡</div>
          <div>no brains found yet</div>
          <p class="hint">make sure OMNI is running on your laptop and you're on the same WiFi. you can also scan a QR code or enter the host manually.</p>
        </div>`;
      return;
    }
    list.innerHTML = items.map(({ info }) => `
      <div class="brain-card" data-host="${escapeHtml(info.host)}" data-port="${info.port}">
        <div class="pulse-dot"></div>
        <div class="meta">
          <div class="name">${escapeHtml(info.name)}</div>
          <div class="info">${escapeHtml(info.host)}:${info.port} · v${escapeHtml(info.version)} · ${escapeHtml(info.model)}</div>
          <div class="caps">${(info.capabilities || []).slice(0, 5).map(c => `<span class="cap">${escapeHtml(c)}</span>`).join('')}</div>
        </div>
        <div class="arrow">›</div>
      </div>
    `).join('');
    list.querySelectorAll('.brain-card').forEach(card => {
      card.addEventListener('click', () => {
        const host = card.dataset.host;
        const port = parseInt(card.dataset.port, 10);
        const info = state.brains.get(`${host}:${port}`)?.info;
        if (info) onBrainSelected(info);
      });
    });
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  }

  // ---------- Brain selected → pair ----------
  function onBrainSelected(info) {
    state.brain = info;
    $('pairBrainName').textContent = info.name;
    $('pairCode').value = '';
    $('pairError').hidden = true;
    show('pair');
    setTimeout(() => $('pairCode').focus(), 200);
  }

  $('pairBackBtn')?.addEventListener('click', () => show('discover'));

  $('pairForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const code = $('pairCode').value.trim();
    if (!/^\d{6}$/.test(code)) {
      $('pairError').textContent = 'code must be 6 digits';
      $('pairError').hidden = false;
      return;
    }
    $('pairError').hidden = true;
    await tryConnect(state.brain, code);
  });

  // ---------- WebSocket connect ----------
  async function tryConnect(info, pairCode) {
    if (!info) return;
    // First verify the pairing code via HTTP if the endpoint exists
    if (pairCode) {
      try {
        const url = `http://${info.host}:${info.port}/api/network/pair/verify`;
        const r = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ code: pairCode }),
        });
        if (r.ok) {
          const data = await r.json();
          if (!data.valid && data.valid !== undefined) {
            $('pairError').textContent = data.reason || 'invalid or expired code';
            $('pairError').hidden = false;
            return;
          }
        }
        // If endpoint doesn't exist, we just trust the code (manual mode)
      } catch (e) { /* offline / endpoint missing — proceed */ }
    }
    state.paired = !!pairCode;
    openWebSocket(info);
  }

  function openWebSocket(info) {
    if (state.ws) {
      try { state.ws.close(); } catch (e) {}
      state.ws = null;
    }
    const wsUrl = `ws://${info.host}:${info.port}/ws/mobile`;
    $('chatBrainName').textContent = info.name;
    $('chatBrainSub').textContent = `connecting to ${info.host}…`;
    show('chat');
    addSystemMessage(`connected to ${info.name}`);
    // Phase 5C: enable location features
    showLocationCard();
    refreshGeofenceData();
    startGeoWatch();
    // Phase 5D: enable notification features
    refreshNotifications();
    trySubscribePush();
    let sock;
    try { sock = new WebSocket(wsUrl); }
    catch (e) { toast('connection failed'); backToDiscover(); return; }
    state.ws = sock;
    sock.onopen = () => {
      state.reconnectAttempts = 0;
      $('chatBrainSub').textContent = 'connected';
      // Identify as mobile
      sock.send(JSON.stringify({
        type: 'mobile_identify',
        device: 'pwa',
        ua: navigator.userAgent,
        paired: state.paired,
      }));
      saveLocal();
    };
    sock.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        handleServerMessage(msg);
      } catch (e) { /* ignore non-JSON */ }
    };
    sock.onerror = () => {
      $('chatBrainSub').textContent = 'connection error';
    };
    sock.onclose = () => {
      $('chatBrainSub').textContent = 'disconnected';
      scheduleReconnect(info);
    };
  }

  function scheduleReconnect(info) {
    if (state.reconnectTimer) return;
    state.reconnectAttempts += 1;
    const delay = Math.min(15000, 1000 * Math.pow(1.6, state.reconnectAttempts - 1));
    state.reconnectTimer = setTimeout(() => {
      state.reconnectTimer = null;
      if (state.brain) openWebSocket(info);
    }, delay);
    toast(`reconnecting in ${Math.round(delay / 1000)}s…`);
  }

  function handleServerMessage(msg) {
    switch (msg.type) {
      case 'text':
      case 'message':
        addMessage('brain', msg.text || msg.content || msg.message || '');
        break;
      case 'thinking':
        appendThinking(msg.token || msg.chunk || '');
        break;
      case 'thinking_done':
        finalizeThinking(msg.text);
        break;
      case 'tool_call':
      case 'tool':
        addToolBubble(msg.tool || msg.name, msg.status || 'running');
        break;
      case 'tool_result':
        markToolResult(msg.tool, msg.ok, msg.output);
        break;
      case 'system':
      case 'status':
        addSystemMessage(msg.text || msg.message || '');
        break;
      case 'wake':
      case 'wake_event':
        flashWake();
        break;
      case 'location_update':
        // Server pushed a current location update (broadcast from any client)
        if (msg.location) {
          state.currentFix = {
            lat: msg.location.lat,
            lon: msg.location.lon,
            accuracy: msg.location.accuracy_m,
            ts: msg.location.ts || Date.now() / 1000,
          };
        }
        state.currentPlace = msg.current_place || null;
        renderLocationCard();
        break;
      case 'geofence_event':
        // A geofence rule fired
        if (msg.event) {
          const ev = msg.event;
          addSystemMessage(`📍 ${ev.event} @ ${ev.place_name} → ${ev.command}`);
        }
        break;
      case 'location_ack':
        if (msg.fired_count > 0) {
          addSystemMessage(`📍 ${msg.fired_count} rule${msg.fired_count > 1 ? 's' : ''} fired`);
        }
        break;
      case 'notification':
        // Real-time notification from the brain (Phase 5D)
        if (msg.notification) {
          const n = msg.notification;
          state.notifications.unshift(n);
          if (!n.read) {
            state.notifUnread++;
            updateNotifBadge();
            showNotifToast(n);
          }
        }
        break;
      case 'pong':
      case 'ack':
        break;
      default:
        // Unknown — show as system if text
        if (msg.text) addSystemMessage(msg.text);
    }
  }

  function wsSend(obj) {
    if (state.ws && state.ws.readyState === WebSocket.OPEN) {
      state.ws.send(JSON.stringify(obj));
      return true;
    }
    return false;
  }

  // ---------- Chat UI ----------
  function addMessage(role, text) {
    state.messages.push({ role, text, ts: Date.now() });
    saveLocal();
    const log = $('messageLog');
    const bubble = document.createElement('div');
    bubble.className = `bubble ${role}`;
    bubble.textContent = text;
    log.appendChild(bubble);
    scrollToBottom();
  }

  function addSystemMessage(text) {
    const log = $('messageLog');
    const bubble = document.createElement('div');
    bubble.className = 'bubble system';
    bubble.textContent = text;
    log.appendChild(bubble);
    scrollToBottom();
  }

  let thinkingEl = null;
  function appendThinking(token) {
    const log = $('messageLog');
    if (!thinkingEl) {
      thinkingEl = document.createElement('div');
      thinkingEl.className = 'bubble brain thinking';
      thinkingEl.innerHTML = '<span class="typing"><span></span><span></span><span></span></span> <span class="think-text"></span>';
      log.appendChild(thinkingEl);
    }
    const txt = thinkingEl.querySelector('.think-text');
    txt.textContent += token;
    scrollToBottom();
  }
  function finalizeThinking(text) {
    if (!thinkingEl) return;
    if (text) {
      thinkingEl.classList.remove('thinking');
      thinkingEl.textContent = text;
      state.messages.push({ role: 'brain', text, ts: Date.now() });
    } else {
      thinkingEl.remove();
    }
    thinkingEl = null;
    saveLocal();
    scrollToBottom();
  }

  function addToolBubble(tool, status) {
    const log = $('messageLog');
    const bubble = document.createElement('div');
    bubble.className = 'bubble system';
    bubble.dataset.tool = tool;
    bubble.innerHTML = `<span class="tool">${escapeHtml(tool)}</span> <span class="status">${escapeHtml(status)}</span>`;
    log.appendChild(bubble);
    scrollToBottom();
  }
  function markToolResult(tool, ok, output) {
    const log = $('messageLog');
    const existing = [...log.querySelectorAll(`[data-tool="${CSS.escape(tool)}"]`)].pop();
    if (existing) {
      existing.querySelector('.status').textContent = ok ? '✓ done' : '✗ failed';
    }
    if (output) {
      const b = document.createElement('div');
      b.className = 'bubble system';
      b.textContent = String(output).slice(0, 400);
      log.appendChild(b);
      scrollToBottom();
    }
  }

  function flashWake() {
    const logo = document.querySelector('.topbar .logo.pulsing');
    if (!logo) return;
    logo.style.boxShadow = '0 0 40px var(--accent)';
    setTimeout(() => { logo.style.boxShadow = ''; }, 600);
    addSystemMessage('🎙 wake word detected');
  }

  function scrollToBottom() {
    const log = $('messageLog');
    requestAnimationFrame(() => { log.scrollTop = log.scrollHeight; });
  }

  // ---------- Send text ----------
  $('sendBtn')?.addEventListener('click', sendText);
  $('textInput')?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendText();
    }
  });

  function sendText() {
    const ta = $('textInput');
    const text = ta.value.trim();
    if (!text) return;
    addMessage('user', text);
    const ok = wsSend({ type: 'text', text, source: 'pwa' });
    if (!ok) {
      toast('not connected');
    }
    ta.value = '';
    autoSizeTextarea();
  }

  function autoSizeTextarea() {
    const ta = $('textInput');
    ta.style.height = 'auto';
    ta.style.height = Math.min(ta.scrollHeight, 120) + 'px';
  }
  $('textInput')?.addEventListener('input', autoSizeTextarea);

  // ---------- Push-to-talk ----------
  // Records audio on the phone mic, sends to /api/voice/transcribe
  // or posts a "voice" event with the audio blob over WebSocket.
  $('pttBtn')?.addEventListener('pointerdown', startPtt);
  $('pttBtn')?.addEventListener('pointerup', stopPtt);
  $('pttBtn')?.addEventListener('pointerleave', () => { if (state.isRecording) stopPtt(); });
  $('pttBtn')?.addEventListener('pointercancel', () => { if (state.isRecording) stopPtt(); });

  async function startPtt(e) {
    e.preventDefault();
    if (state.isRecording) return;
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      toast('mic not supported on this browser');
      return;
    }
    try {
      state.pttStream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, channelCount: 1 }
      });
      const mime = pickMime();
      state.mediaRecorder = new MediaRecorder(state.pttStream, mime ? { mimeType: mime } : {});
      state.audioChunks = [];
      state.mediaRecorder.ondataavailable = (ev) => {
        if (ev.data.size > 0) state.audioChunks.push(ev.data);
      };
      state.mediaRecorder.onstop = onPttStop;
      state.mediaRecorder.start();
      state.isRecording = true;
      $('pttBtn').classList.add('recording');
      toast('listening…', 800);
    } catch (err) {
      toast('mic permission denied');
      cleanupPtt();
    }
  }

  function stopPtt(e) {
    if (e) e.preventDefault();
    if (!state.isRecording) return;
    try { state.mediaRecorder.stop(); } catch (err) { /* ignore */ }
  }

  function pickMime() {
    const candidates = [
      'audio/webm;codecs=opus',
      'audio/webm',
      'audio/ogg;codecs=opus',
      'audio/mp4',
    ];
    for (const c of candidates) {
      if (MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported(c)) return c;
    }
    return '';
  }

  async function onPttStop() {
    state.isRecording = false;
    $('pttBtn').classList.remove('recording');
    const blob = new Blob(state.audioChunks, { type: state.audioChunks[0]?.type || 'audio/webm' });
    cleanupPtt();
    if (blob.size < 1000) { toast('too short, try again'); return; }
    addSystemMessage('🎙 transcribing…');
    try {
      // Try /api/voice/transcribe first
      const fd = new FormData();
      const ext = (blob.type.includes('mp4') ? 'm4a' : (blob.type.includes('ogg') ? 'ogg' : 'webm'));
      fd.append('audio', blob, `ptt.${ext}`);
      const url = `http://${state.brain.host}:${state.brain.port}/api/voice/transcribe`;
      const r = await fetch(url, { method: 'POST', body: fd });
      let transcript = '';
      if (r.ok) {
        const data = await r.json();
        transcript = data.text || data.transcript || data.text || '';
      }
      if (!transcript) {
        // Fallback: send raw audio as base64 over WebSocket
        const buf = await blob.arrayBuffer();
        const b64 = arrayBufferToBase64(buf);
        const sent = wsSend({ type: 'audio', format: ext, data: b64, source: 'pwa' });
        if (sent) {
          addSystemMessage('🎙 sent audio to brain');
          return;
        }
        toast('no transcript & no socket');
        return;
      }
      addMessage('user', transcript);
      wsSend({ type: 'text', text: transcript, source: 'pwa-voice' });
    } catch (e) {
      toast('transcribe failed: ' + e.message);
    }
  }

  function cleanupPtt() {
    if (state.pttStream) {
      try { state.pttStream.getTracks().forEach(t => t.stop()); } catch (e) {}
      state.pttStream = null;
    }
    state.mediaRecorder = null;
    state.audioChunks = [];
  }

  function arrayBufferToBase64(buf) {
    const bytes = new Uint8Array(buf);
    let bin = '';
    const chunk = 0x8000;
    for (let i = 0; i < bytes.length; i += chunk) {
      bin += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
    }
    return btoa(bin);
  }

  // ---------- QR scanner ----------
  let scanStream = null;
  let scanRAF = null;
  let jsQR = null;

  $('scanBtn')?.addEventListener('click', startScanner);
  $('scanCloseBtn')?.addEventListener('click', stopScanner);

  async function startScanner() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      toast('camera not supported');
      return;
    }
    $('scanArea').hidden = false;
    try {
      // Load jsQR dynamically
      if (!jsQR) {
        await loadScript('https://cdn.jsdelivr.net/npm/jsqr@1.4.0/dist/jsQR.js');
        jsQR = window.jsQR;
      }
      scanStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' }, audio: false,
      });
      const video = $('scanVideo');
      video.srcObject = scanStream;
      await video.play();
      tickScan();
    } catch (e) {
      toast('camera permission denied');
      stopScanner();
    }
  }

  function tickScan() {
    if (!scanStream) return;
    const video = $('scanVideo');
    const canvas = $('scanCanvas');
    if (video.readyState === video.HAVE_ENOUGH_DATA) {
      const w = video.videoWidth, h = video.videoHeight;
      canvas.width = w; canvas.height = h;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(video, 0, 0, w, h);
      try {
        const img = ctx.getImageData(0, 0, w, h);
        const code = jsQR(img.data, w, h, { inversionAttempts: 'dontInvert' });
        if (code && code.data) {
          handleQrPayload(code.data);
          return;
        }
      } catch (e) { /* ignore frame errors */ }
    }
    scanRAF = requestAnimationFrame(tickScan);
  }

  function handleQrPayload(payload) {
    stopScanner();
    let info = null;
    try {
      const data = JSON.parse(payload);
      if (data.type === 'omni-discover' && data.host) {
        info = attachInfoMethods({
          name: data.name || 'OMNI',
          host: data.host,
          port: parseInt(data.port, 10) || 8765,
          version: data.version || 'unknown',
          model: data.model || 'unknown',
          capabilities: data.caps || [],
        });
      }
    } catch (e) {
      // Try URI form
      if (payload.startsWith('omni://')) {
        const url = new URL(payload.replace('omni://', 'http://'));
        const host = url.hostname;
        const port = parseInt(url.port, 10) || 8765;
        const code = url.searchParams.get('code');
        if (host) {
          info = attachInfoMethods({
            name: 'OMNI', host, port,
            version: 'unknown', model: 'unknown', capabilities: [],
          });
          if (code) {
            // Direct connect with code
            state.brain = info;
            tryConnect(info, code);
            return;
          }
        }
      }
    }
    if (info) {
      addBrain(info);
      renderBrains();
      toast('found brain: ' + info.name);
    } else {
      toast('QR not recognized');
    }
  }

  function stopScanner() {
    if (scanRAF) cancelAnimationFrame(scanRAF);
    scanRAF = null;
    if (scanStream) {
      try { scanStream.getTracks().forEach(t => t.stop()); } catch (e) {}
      scanStream = null;
    }
    $('scanVideo').srcObject = null;
    $('scanArea').hidden = true;
  }

  function loadScript(src) {
    return new Promise((resolve, reject) => {
      const s = document.createElement('script');
      s.src = src; s.onload = () => resolve();
      s.onerror = () => reject(new Error('script load failed: ' + src));
      document.head.appendChild(s);
    });
  }

  // ---------- Manual connect ----------
  $('manualForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const host = $('manualHost').value.trim();
    const port = parseInt($('manualPort').value, 10) || 8765;
    if (!host) return;
    const info = await probeHttp(host, port, 1500);
    if (info) {
      addBrain(info);
      renderBrains();
      toast('connected to ' + info.name);
      onBrainSelected(info);
    } else {
      // Try anyway (maybe brain has no /api/network/info yet)
      const guess = attachInfoMethods({
        name: 'OMNI', host, port,
        version: 'unknown', model: 'unknown', capabilities: [],
      });
      onBrainSelected(guess);
    }
  });

  // ---------- Menu ----------
  $('chatMenuBtn')?.addEventListener('click', () => { $('menu').hidden = false; });
  $('menu')?.addEventListener('click', (e) => {
    if (e.target === $('menu')) $('menu').hidden = true;
  });
  $('menuDiscover')?.addEventListener('click', () => { $('menu').hidden = true; backToDiscover(); });
  $('menuHistory')?.addEventListener('click', () => {
    $('menu').hidden = true;
    if (state.messages.length === 0) { toast('no history yet'); return; }
    const blob = new Blob([JSON.stringify(state.messages, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `omni-session-${Date.now()}.json`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  $('menuStats')?.addEventListener('click', async () => {
    $('menu').hidden = true;
    if (!state.brain) { toast('not connected'); return; }
    try {
      const r = await fetch(`http://${state.brain.host}:${state.brain.port}/api/stats`);
      if (r.ok) {
        const data = await r.json();
        const lines = Object.entries(data).slice(0, 10).map(([k, v]) => `${k}: ${v}`).join('\n');
        toast(lines, 4000);
      } else { toast('stats unavailable'); }
    } catch (e) { toast('stats request failed'); }
  });
  $('menuInstall')?.addEventListener('click', async () => {
    $('menu').hidden = true;
    if (state.deferredPrompt) {
      state.deferredPrompt.prompt();
      const choice = await state.deferredPrompt.userChoice;
      toast(choice.outcome === 'accepted' ? 'installing…' : 'install cancelled');
      state.deferredPrompt = null;
    } else {
      toast('use browser menu: "Add to Home Screen"');
    }
  });
  $('menuDisconnect')?.addEventListener('click', () => {
    $('menu').hidden = true;
    if (state.ws) { try { state.ws.close(); } catch (e) {} state.ws = null; }
    state.brain = null;
    state.paired = false;
    state.messages = [];
    stopGeoWatch();
    state.currentFix = null;
    state.currentPlace = null;
    const card = $('locationCard');
    if (card) card.hidden = true;
    saveLocal();
    backToDiscover();
  });

  function backToDiscover() {
    if (state.scanTimer) clearInterval(state.scanTimer);
    state.scanTimer = setInterval(scanSubnet, 8000);
    show('discover');
    renderBrains();
  }

  // ---------- Phase 5C: Geofence / Location ----------

  // Show location card (only on chat screen, only if geofence enabled on backend)
  function showLocationCard() {
    const card = $('locationCard');
    if (!card) return;
    card.hidden = false;
    renderLocationCard();
  }

  function renderLocationCard() {
    const place = state.currentPlace;
    const fix = state.currentFix;
    const placeEl = $('locPlace');
    const coordsEl = $('locCoords');
    const iconEl = $('locIcon');
    const sendBtn = $('locSendBtn');

    if (place) {
      placeEl.textContent = `${place.icon || '📍'} ${place.name}`;
      coordsEl.textContent = `inside ${place.radius_m}m · ${place.address || ''}`;
      iconEl.textContent = place.icon || '📍';
    } else if (fix) {
      placeEl.textContent = '— not at a place —';
      coordsEl.textContent = `${fix.lat.toFixed(5)}, ${fix.lon.toFixed(5)} ±${Math.round(fix.accuracy || 0)}m`;
      iconEl.textContent = '🌐';
    } else {
      placeEl.textContent = 'location off';
      coordsEl.textContent = 'tap ↑ to send your location';
      iconEl.textContent = '📍';
    }
    if (sendBtn) {
      sendBtn.disabled = state.sendingLoc;
      sendBtn.classList.toggle('sending', state.sendingLoc);
    }
  }

  // Get current GPS fix (one-shot)
  async function getOneShotFix() {
    if (!navigator.geolocation) {
      toast('geolocation not supported');
      return null;
    }
    return new Promise((resolve) => {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          resolve({
            lat: pos.coords.latitude,
            lon: pos.coords.longitude,
            accuracy: pos.coords.accuracy,
            ts: pos.timestamp || Date.now(),
          });
        },
        (err) => {
          toast('location denied: ' + err.message);
          resolve(null);
        },
        { enableHighAccuracy: true, timeout: 8000, maximumAge: 30000 }
      );
    });
  }

  // Start watching position (continuous)
  function startGeoWatch() {
    if (state.geoWatchId !== null) return;
    if (!navigator.geolocation) return;
    try {
      state.geoWatchId = navigator.geolocation.watchPosition(
        (pos) => {
          state.currentFix = {
            lat: pos.coords.latitude,
            lon: pos.coords.longitude,
            accuracy: pos.coords.accuracy,
            ts: pos.timestamp || Date.now(),
          };
          renderLocationCard();
        },
        (err) => {
          // Silent — user may have denied
          console.debug('geo watch error:', err.message);
        },
        { enableHighAccuracy: false, timeout: 30000, maximumAge: 60000 }
      );
    } catch (e) {
      console.debug('geo watch failed:', e);
    }
  }

  function stopGeoWatch() {
    if (state.geoWatchId !== null && navigator.geolocation) {
      try { navigator.geolocation.clearWatch(state.geoWatchId); } catch (e) {}
      state.geoWatchId = null;
    }
  }

  // Send current location to the brain
  async function sendLocation() {
    if (!state.brain) { toast('not connected'); return; }
    if (state.sendingLoc) return;
    state.sendingLoc = true;
    renderLocationCard();
    try {
      let fix = state.currentFix;
      if (!fix) fix = await getOneShotFix();
      if (!fix) {
        state.sendingLoc = false;
        renderLocationCard();
        return;
      }
      // Try WebSocket first (lower latency), fall back to HTTP
      let firedCount = 0;
      if (state.ws && state.ws.readyState === WebSocket.OPEN) {
        const ok = wsSend({
          type: 'location',
          lat: fix.lat,
          lon: fix.lon,
          accuracy_m: fix.accuracy,
          source: 'phone-pwa',
        });
        if (ok) {
          addSystemMessage(`📍 sent location (${fix.lat.toFixed(4)}, ${fix.lon.toFixed(4)})`);
        }
      } else {
        // HTTP fallback
        const url = `http://${state.brain.host}:${state.brain.port}/api/geofence/location`;
        const r = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            lat: fix.lat, lon: fix.lon,
            accuracy_m: fix.accuracy, source: 'phone-pwa',
          }),
        });
        if (r.ok) {
          const data = await r.json();
          firedCount = (data.fired || []).length;
          if (firedCount > 0) {
            addSystemMessage(`📍 triggered ${firedCount} rule${firedCount > 1 ? 's' : ''}`);
            for (const ev of data.fired) {
              addSystemMessage(`  → ${ev.event} @ ${ev.place_name}: ${ev.command}`);
            }
          } else {
            addSystemMessage(`📍 location sent (no rules fired)`);
          }
        } else {
          toast('failed to send location');
        }
      }
      // Refresh place list (in case rules fired)
      await refreshGeofenceData();
    } catch (e) {
      toast('send failed: ' + e.message);
    } finally {
      state.sendingLoc = false;
      renderLocationCard();
    }
  }

  // Fetch places, rules, events from backend
  async function refreshGeofenceData() {
    if (!state.brain) return;
    const base = `http://${state.brain.host}:${state.brain.port}`;
    try {
      const [p, r, e, s] = await Promise.all([
        fetch(`${base}/api/geofence/places`).then(x => x.json()).catch(() => ({})),
        fetch(`${base}/api/geofence/rules`).then(x => x.json()).catch(() => ({})),
        fetch(`${base}/api/geofence/events?limit=10`).then(x => x.json()).catch(() => ({})),
        fetch(`${base}/api/geofence/location`).then(x => x.json()).catch(() => ({})),
      ]);
      state.places = p.places || [];
      state.rules = r.rules || [];
      if (s.current_place) state.currentPlace = s.current_place;
      if (s.location) state.currentFix = s.location;
      renderLocationCard();
      renderGeofenceScreen();
    } catch (e) {
      // ignore
    }
  }

  // Render the geofence management screen
  function renderGeofenceScreen() {
    const placeList = $('placeList');
    const ruleList = $('ruleList');
    const eventList = $('eventList');
    const subtitle = $('geoSubtitle');
    if (!placeList || !ruleList || !eventList) return;

    if (subtitle) {
      subtitle.textContent = `${state.places.length} places · ${state.rules.length} rules`;
    }

    // Places
    if (state.places.length === 0) {
      placeList.innerHTML = `<div class="empty-mini">no places yet — tap + to add</div>`;
    } else {
      placeList.innerHTML = state.places.map(p => `
        <div class="place-card">
          <div class="place-icon">${escapeHtml(p.icon || '📍')}</div>
          <div class="place-info">
            <div class="place-name">${escapeHtml(p.name)}</div>
            <div class="place-meta">${p.lat.toFixed(4)}, ${p.lon.toFixed(4)} · r=${p.radius_m}m</div>
          </div>
          <button class="place-del" data-id="${escapeHtml(p.id)}" aria-label="Delete">×</button>
        </div>
      `).join('');
      placeList.querySelectorAll('.place-del').forEach(btn => {
        btn.addEventListener('click', () => deletePlace(btn.dataset.id));
      });
    }

    // Rules
    if (state.rules.length === 0) {
      ruleList.innerHTML = `<div class="empty-mini">no rules yet — tap + to add</div>`;
    } else {
      ruleList.innerHTML = state.rules.map(r => `
        <div class="rule-card ${r.enabled ? '' : 'disabled'}">
          <div class="rule-event ${escapeHtml(r.event)}">${escapeHtml(r.event)}</div>
          <div class="rule-info">
            <div class="rule-cmd">${escapeHtml(r.label || r.command)}</div>
            <div class="rule-place">${escapeHtml(r.place_icon || '📍')} ${escapeHtml(r.place_name || '?')}</div>
          </div>
          <button class="rule-del" data-id="${escapeHtml(r.id)}" aria-label="Delete">×</button>
        </div>
      `).join('');
      ruleList.querySelectorAll('.rule-del').forEach(btn => {
        btn.addEventListener('click', () => deleteRule(btn.dataset.id));
      });
    }

    // Events (fetched separately)
    fetchEvents();
  }

  async function fetchEvents() {
    if (!state.brain) return;
    try {
      const r = await fetch(`http://${state.brain.host}:${state.brain.port}/api/geofence/events?limit=10`);
      const data = await r.json();
      const events = data.events || [];
      const eventList = $('eventList');
      if (!eventList) return;
      if (events.length === 0) {
        eventList.innerHTML = `<div class="empty-mini">no events yet</div>`;
      } else {
        eventList.innerHTML = events.slice().reverse().map(e => {
          const when = new Date(e.ts * 1000);
          const h = when.getHours().toString().padStart(2, '0');
          const m = when.getMinutes().toString().padStart(2, '0');
          return `
            <div class="event-card">
              <div class="event-time">${h}:${m}</div>
              <div class="event-detail">
                <span class="place">${escapeHtml(e.place_name)}</span>
                <span style="color:var(--fg-mute)"> · ${escapeHtml(e.event)}</span>
                <div style="color:var(--fg-dim); font-size:11px; margin-top:2px;">${escapeHtml(e.command)}</div>
              </div>
            </div>
          `;
        }).join('');
      }
    } catch (e) { /* ignore */ }
  }

  // CRUD: places
  async function addPlace(name, lat, lon, radius_m, icon) {
    if (!state.brain) return;
    try {
      const r = await fetch(`http://${state.brain.host}:${state.brain.port}/api/geofence/places`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, lat, lon, radius_m, icon }),
      });
      const data = await r.json();
      if (data.status === 'ok') {
        toast('place added');
        await refreshGeofenceData();
      } else {
        toast('failed: ' + (data.error || 'unknown'));
      }
    } catch (e) { toast('add failed'); }
  }
  async function deletePlace(id) {
    if (!state.brain) return;
    try {
      const r = await fetch(`http://${state.brain.host}:${state.brain.port}/api/geofence/places/${id}`, { method: 'DELETE' });
      const data = await r.json();
      if (data.removed) {
        toast('place removed');
        await refreshGeofenceData();
      }
    } catch (e) { toast('delete failed'); }
  }

  // CRUD: rules
  async function addRule(place_id, event, command, label) {
    if (!state.brain) return;
    try {
      const r = await fetch(`http://${state.brain.host}:${state.brain.port}/api/geofence/rules`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ place_id, event, command, label }),
      });
      const data = await r.json();
      if (data.status === 'ok') {
        toast('rule added');
        await refreshGeofenceData();
      } else {
        toast('failed: ' + (data.error || 'unknown'));
      }
    } catch (e) { toast('add failed'); }
  }
  async function deleteRule(id) {
    if (!state.brain) return;
    try {
      const r = await fetch(`http://${state.brain.host}:${state.brain.port}/api/geofence/rules/${id}`, { method: 'DELETE' });
      const data = await r.json();
      if (data.removed) {
        toast('rule removed');
        await refreshGeofenceData();
      }
    } catch (e) { toast('delete failed'); }
  }

  // Seed sample places
  async function seedSamples() {
    if (!state.brain) return;
    try {
      const r = await fetch(`http://${state.brain.host}:${state.brain.port}/api/geofence/seed`, { method: 'POST' });
      const data = await r.json();
      toast(`added ${data.count} sample places`);
      await refreshGeofenceData();
    } catch (e) { toast('seed failed'); }
  }

  // ---------- Modal: add place ----------
  let _modalEl = null;
  function showAddPlaceModal() {
    if (_modalEl) _modalEl.remove();
    _modalEl = document.createElement('div');
    _modalEl.className = 'modal-bg';
    _modalEl.innerHTML = `
      <div class="modal">
        <h2>Add place</h2>
        <div class="form-row">
          <label>Name</label>
          <input type="text" id="m_place_name" placeholder="Home" />
        </div>
        <div class="form-row">
          <label>Icon</label>
          <select id="m_place_icon">
            <option value="📍">📍 Pin</option>
            <option value="🏠">🏠 Home</option>
            <option value="🏢">🏢 Work</option>
            <option value="💪">💪 Gym</option>
            <option value="☕">☕ Coffee</option>
            <option value="🛒">🛒 Store</option>
            <option value="🌳">🌳 Park</option>
            <option value="🚗">🚗 Commute</option>
          </select>
        </div>
        <div class="form-row">
          <label>Latitude</label>
          <input type="number" id="m_place_lat" step="any" placeholder="33.6844" />
        </div>
        <div class="form-row">
          <label>Longitude</label>
          <input type="number" id="m_place_lon" step="any" placeholder="73.0479" />
        </div>
        <div class="form-row">
          <label>Radius (meters)</label>
          <input type="number" id="m_place_radius" value="100" min="20" max="5000" />
        </div>
        <div class="actions">
          <button class="btn-secondary" id="m_use_current">use my location</button>
          <button class="btn-primary" id="m_save_place">save</button>
        </div>
        <div class="actions" style="margin-top:8px;">
          <button class="btn-secondary" id="m_cancel" style="flex:1;">cancel</button>
        </div>
      </div>
    `;
    document.body.appendChild(_modalEl);
    // Pre-fill with current location if available
    if (state.currentFix) {
      $('m_place_lat').value = state.currentFix.lat.toFixed(6);
      $('m_place_lon').value = state.currentFix.lon.toFixed(6);
    }
    $('m_place_name').focus();
    $('m_cancel').addEventListener('click', closeModal);
    $('m_save_place').addEventListener('click', async () => {
      const name = $('m_place_name').value.trim();
      const lat = parseFloat($('m_place_lat').value);
      const lon = parseFloat($('m_place_lon').value);
      const radius = parseInt($('m_place_radius').value, 10) || 100;
      const icon = $('m_place_icon').value;
      if (!name || isNaN(lat) || isNaN(lon)) {
        toast('fill in name, lat, lon');
        return;
      }
      closeModal();
      await addPlace(name, lat, lon, radius, icon);
    });
    $('m_use_current').addEventListener('click', async () => {
      const fix = state.currentFix || await getOneShotFix();
      if (fix) {
        $('m_place_lat').value = fix.lat.toFixed(6);
        $('m_place_lon').value = fix.lon.toFixed(6);
        toast('using current location');
      }
    });
  }

  function showAddRuleModal() {
    if (state.places.length === 0) {
      toast('add a place first');
      return;
    }
    if (_modalEl) _modalEl.remove();
    const placeOptions = state.places.map(p =>
      `<option value="${escapeHtml(p.id)}">${escapeHtml(p.icon || '📍')} ${escapeHtml(p.name)}</option>`
    ).join('');
    _modalEl = document.createElement('div');
    _modalEl.className = 'modal-bg';
    _modalEl.innerHTML = `
      <div class="modal">
        <h2>Add rule</h2>
        <div class="form-row">
          <label>Place</label>
          <select id="m_rule_place">${placeOptions}</select>
        </div>
        <div class="form-row">
          <label>Event</label>
          <select id="m_rule_event">
            <option value="arrive">arrive (enter place)</option>
            <option value="depart">depart (leave place)</option>
            <option value="dwell">dwell (stayed 5+ min)</option>
          </select>
        </div>
        <div class="form-row">
          <label>Command to run</label>
          <input type="text" id="m_rule_cmd" placeholder="play my workout playlist" />
        </div>
        <div class="form-row">
          <label>Label (optional)</label>
          <input type="text" id="m_rule_label" placeholder="Start workout music" />
        </div>
        <div class="actions">
          <button class="btn-secondary" id="m_cancel">cancel</button>
          <button class="btn-primary" id="m_save_rule">save</button>
        </div>
      </div>
    `;
    document.body.appendChild(_modalEl);
    $('m_cancel').addEventListener('click', closeModal);
    $('m_save_rule').addEventListener('click', async () => {
      const place_id = $('m_rule_place').value;
      const event = $('m_rule_event').value;
      const command = $('m_rule_cmd').value.trim();
      const label = $('m_rule_label').value.trim();
      if (!command) { toast('enter a command'); return; }
      closeModal();
      await addRule(place_id, event, command, label);
    });
  }

  function closeModal() {
    if (_modalEl) { _modalEl.remove(); _modalEl = null; }
  }

  // ---------- Wire location UI ----------
  $('locSendBtn')?.addEventListener('click', sendLocation);
  $('locManageBtn')?.addEventListener('click', async () => {
    await refreshGeofenceData();
    show('geofence');
  });
  $('locSeedBtn')?.addEventListener('click', seedSamples);
  $('locClearBtn')?.addEventListener('click', async () => {
    if (!state.brain) return;
    if (!confirm('Clear all geofence events?')) return;
    try {
      await fetch(`http://${state.brain.host}:${state.brain.port}/api/geofence/clear-events`, { method: 'POST' });
      toast('events cleared');
    } catch (e) { toast('clear failed'); }
  });
  $('menuLocation')?.addEventListener('click', async () => {
    $('menu').hidden = true;
    await refreshGeofenceData();
    show('geofence');
  });
  $('geoBackBtn')?.addEventListener('click', () => show('chat'));
  $('geoAddBtn')?.addEventListener('click', () => {
    if (state.places.length === 0) {
      showAddPlaceModal();
    } else {
      // Cycle: if there are places but no rules, prompt rule; else show both options
      const choice = confirm(`Tap OK to add a PLACE.\nTap Cancel to add a RULE.`);
      if (choice) showAddPlaceModal();
      else showAddRuleModal();
    }
  });

  // ---------- Phase 5D: Notifications ----------

  // Fetch notifications from backend
  async function refreshNotifications() {
    if (!state.brain) return;
    try {
      const r = await fetch(`http://${state.brain.host}:${state.brain.port}/api/notifications?limit=100`);
      const data = await r.json();
      state.notifications = data.notifications || [];
      state.notifUnread = data.unread_count || 0;
      updateNotifBadge();
      renderNotificationsScreen();
      // Also fetch prefs to show snooze banner
      try {
        const pr = await fetch(`http://${state.brain.host}:${state.brain.port}/api/notifications/prefs`);
        const pd = await pr.json();
        if (pd.status === 'ok') showSnoozeBanner(pd.snooze);
      } catch (_) { /* ignore */ }
    } catch (e) {
      // ignore
    }
  }

  function updateNotifBadge() {
    const badge = $('notifBadge');
    if (!badge) return;
    if (state.notifUnread > 0) {
      badge.textContent = state.notifUnread > 99 ? '99+' : String(state.notifUnread);
      badge.hidden = false;
      const bell = $('chatNotifBtn');
      if (bell && !bell.classList.contains('has-new')) {
        bell.classList.add('has-new');
        setTimeout(() => bell.classList.remove('has-new'), 1800);
      }
    } else {
      badge.hidden = true;
    }
  }

  function renderNotificationsScreen() {
    const list = $('notifList');
    const subtitle = $('notifSubtitle');
    if (!list) return;
    if (subtitle) {
      const total = state.notifications.length;
      const unread = state.notifUnread;
      subtitle.textContent = `${total} total · ${unread} unread`;
    }
    if (state.notifications.length === 0) {
      list.innerHTML = `<div class="empty-mini">no notifications yet</div>`;
      return;
    }
    list.innerHTML = state.notifications.map(n => {
      const when = n.ts ? new Date(n.ts * 1000) : new Date();
      const timeStr = when.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      const dateStr = when.toLocaleDateString([], { month: 'short', day: 'numeric' });
      const prioCls = n.priority >= 3 ? 'urgent' : n.priority >= 2 ? 'high' : '';
      const prioLabel = n.priority >= 3 ? '⚠ URGENT' : n.priority >= 2 ? '! high' : '';
      const icon = n.icon || '🔔';
      return `
        <div class="notif-card ${n.read ? '' : 'unread'}" data-id="${escapeHtml(n.id)}">
          <div class="notif-icon">${escapeHtml(icon)}</div>
          <div class="notif-body-col">
            <div class="notif-title">
              ${escapeHtml(n.title || '(no title)')}
              <span class="notif-cat ${escapeHtml(n.category)}">${escapeHtml(n.category)}</span>
              ${prioLabel ? `<span class="notif-prio ${prioCls}">${prioLabel}</span>` : ''}
            </div>
            ${n.body ? `<div class="notif-text">${escapeHtml(n.body)}</div>` : ''}
            <div class="notif-meta">${dateStr} ${timeStr}</div>
          </div>
        </div>
      `;
    }).join('');
    // Tap to mark read
    list.querySelectorAll('.notif-card.unread').forEach(card => {
      card.addEventListener('click', async () => {
        const id = card.dataset.id;
        try {
          await fetch(`http://${state.brain.host}:${state.brain.port}/api/notifications/${id}/read`, { method: 'POST' });
          card.classList.remove('unread');
          state.notifUnread = Math.max(0, state.notifUnread - 1);
          updateNotifBadge();
        } catch (e) { /* ignore */ }
      });
    });
  }

  // Try to subscribe to web push (VAPID)
  async function trySubscribePush() {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
      return; // not supported
    }
    try {
      const reg = await navigator.serviceWorker.ready;
      // Get VAPID key
      const r = await fetch(`http://${state.brain.host}:${state.brain.port}/api/notifications/vapid`);
      const data = await r.json();
      const pubKey = data.vapid && data.vapid.public_key;
      if (!pubKey || pubKey.length < 40) return;  // not a real key (dev mode)
      // Subscribe
      const sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(pubKey),
      });
      // Register with backend
      const regRes = await fetch(`http://${state.brain.host}:${state.brain.port}/api/notifications/subscribe`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          device_id: state.deviceId,
          endpoint: sub.endpoint,
          p256dh: arrayBufferToBase64(sub.getKey('p256dh')),
          auth: arrayBufferToBase64(sub.getKey('auth')),
          user_agent: navigator.userAgent,
          paired: true,
          capabilities: ['voice', 'location', 'notifications'],
        }),
      });
      const regData = await regRes.json();
      if (regData.status === 'ok') {
        state.pushSubscribed = true;
        console.info('Push subscription registered:', state.deviceId);
      }
    } catch (e) {
      console.debug('Push subscribe failed (this is OK in dev):', e.message);
    }
  }

  function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const raw = atob(base64);
    const out = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
    return out;
  }

  // Show a toast for a real-time notification
  function showNotifToast(n) {
    const t = document.createElement('div');
    t.className = 'notif-toast';
    t.innerHTML = `
      <div class="notif-toast-icon">${escapeHtml(n.icon || '🔔')}</div>
      <div class="notif-toast-body">
        <div class="notif-toast-title">${escapeHtml(n.title || 'OMNI')}</div>
        ${n.body ? `<div class="notif-toast-text">${escapeHtml(n.body)}</div>` : ''}
      </div>
    `;
    document.body.appendChild(t);
    requestAnimationFrame(() => t.classList.add('show'));
    setTimeout(() => {
      t.classList.remove('show');
      setTimeout(() => t.remove(), 300);
    }, 5000);
    t.addEventListener('click', () => {
      $('notifToast')?.remove();
      // Open notifications screen
      refreshNotifications();
      show('notifications');
    });
  }

  // ---------- Wire notification UI ----------
  $('chatNotifBtn')?.addEventListener('click', async () => {
    await refreshNotifications();
    show('notifications');
  });
  $('notifBackBtn')?.addEventListener('click', () => show('chat'));
  $('notifMarkAllBtn')?.addEventListener('click', async () => {
    if (!state.brain) return;
    try {
      await fetch(`http://${state.brain.host}:${state.brain.port}/api/notifications/read-all`, { method: 'POST' });
      state.notifUnread = 0;
      updateNotifBadge();
      await refreshNotifications();
      toast('all marked as read');
    } catch (e) { toast('failed'); }
  });
  $('menuNotifications')?.addEventListener('click', async () => {
    $('menu').hidden = true;
    await refreshNotifications();
    show('notifications');
  });

  // ---------- Phase 5E: Notification preferences + snooze ----------

  const ALL_CATEGORIES = [
    "info", "success", "warn", "error",
    "action_required", "geofence", "proactive",
    "schedule", "wake", "tool",
  ];

  async function refreshPrefs() {
    if (!state.brain) return;
    try {
      const r = await fetch(`http://${state.brain.host}:${state.brain.port}/api/notifications/prefs`);
      const data = await r.json();
      renderPrefsScreen(data);
    } catch (e) { /* ignore */ }
  }

  function renderPrefsScreen(data) {
    if (!data || data.status !== 'ok') return;
    const p = data.prefs;
    const snooze = data.snooze;
    $('prefEnabled').checked = !!p.enabled;
    $('prefShowPreview').checked = !!p.show_preview;
    $('prefPlaySound').checked = !!p.play_sound;
    $('prefDndEnabled').checked = !!p.dnd_enabled;
    $('prefDndStart').value = p.dnd_start_hour ?? 22;
    $('prefDndEnd').value = p.dnd_end_hour ?? 7;
    // Render category toggles
    const muted = new Set(p.muted_categories || []);
    const catWrap = $('catToggles');
    catWrap.innerHTML = ALL_CATEGORIES.map(cat => {
      const on = !muted.has(cat);
      return `<div class="cat-toggle ${on ? 'on' : ''}" data-cat="${escapeHtml(cat)}">${escapeHtml(cat)}</div>`;
    }).join('');
    catWrap.querySelectorAll('.cat-toggle').forEach(el => {
      el.addEventListener('click', () => el.classList.toggle('on'));
    });
  }

  async function savePrefs() {
    if (!state.brain) return;
    const muted = [];
    $('catToggles').querySelectorAll('.cat-toggle').forEach(el => {
      if (!el.classList.contains('on')) muted.push(el.dataset.cat);
    });
    const payload = {
      enabled: $('prefEnabled').checked,
      show_preview: $('prefShowPreview').checked,
      play_sound: $('prefPlaySound').checked,
      dnd_enabled: $('prefDndEnabled').checked,
      dnd_start_hour: parseInt($('prefDndStart').value, 10) || 22,
      dnd_end_hour: parseInt($('prefDndEnd').value, 10) || 7,
      muted_categories: muted,
    };
    try {
      const r = await fetch(`http://${state.brain.host}:${state.brain.port}/api/notifications/prefs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await r.json();
      if (data.status === 'ok') {
        toast('preferences saved');
      } else {
        toast('save failed');
      }
    } catch (e) { toast('save failed'); }
  }

  async function snoozeFor(minutes) {
    if (!state.brain) return;
    try {
      const r = await fetch(`http://${state.brain.host}:${state.brain.port}/api/notifications/snooze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ minutes }),
      });
      const data = await r.json();
      if (data.status === 'ok') {
        toast(`🔕 snoozed for ${minutes} min`);
        await refreshNotifications();
      }
    } catch (e) { toast('snooze failed'); }
  }

  async function unsnooze() {
    if (!state.brain) return;
    try {
      await fetch(`http://${state.brain.host}:${state.brain.port}/api/notifications/snooze`, { method: 'DELETE' });
      toast('snooze lifted');
      await refreshNotifications();
    } catch (e) { /* ignore */ }
  }

  function showSnoozeBanner(snooze) {
    const banner = $('snoozeBanner');
    if (!banner) return;
    if (snooze && snooze.until > Date.now() / 1000) {
      banner.hidden = false;
      const until = new Date(snooze.until * 1000);
      $('snoozeSub').textContent = `until ${until.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    } else {
      banner.hidden = true;
    }
  }

  // ---------- Wire prefs UI ----------
  $('notifPrefsBtn')?.addEventListener('click', async () => {
    await refreshPrefs();
    show('notifPrefs');
  });
  $('prefsBackBtn')?.addEventListener('click', () => show('notifications'));
  $('prefsSaveBtn')?.addEventListener('click', savePrefs);
  $('prefsResetBtn')?.addEventListener('click', async () => {
    if (!state.brain) return;
    if (!confirm('Reset all notification preferences to defaults?')) return;
    try {
      await fetch(`http://${state.brain.host}:${state.brain.port}/api/notifications/prefs/reset`, { method: 'POST' });
      toast('preferences reset');
      await refreshPrefs();
    } catch (e) { toast('reset failed'); }
  });
  // Snooze preset buttons
  document.querySelectorAll('.preset-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const min = parseInt(btn.dataset.min, 10);
      if (min) snoozeFor(min);
    });
  });
  $('snoozeLiftBtn')?.addEventListener('click', unsnooze);

  // ---------- Phase 6A: Brain State (Visual-First) ----------

  async function refreshBrainState() {
    if (!state.brain) return;
    try {
      const [ctxR, statusR, dashR, suggR] = await Promise.all([
        fetch(`http://${state.brain.host}:${state.brain.port}/api/screen/context`),
        fetch(`http://${state.brain.host}:${state.brain.port}/api/screen/status`),
        fetch(`http://${state.brain.host}:${state.brain.port}/api/screen/dashboard`),
        fetch(`http://${state.brain.host}:${state.brain.port}/api/proactive/suggestions`),
      ]);
      const ctx = await ctxR.json();
      const status = await statusR.json();
      const dash = await dashR.json();
      const sugg = await suggR.json();
      renderBrainScreen(ctx, status, dash, sugg);
    } catch (e) { /* ignore */ }
  }

  function renderBrainScreen(ctx, status, dash, sugg) {
    const subtitle = $('brainSubtitle');
    const icon = $('brainIcon');
    const actEl = $('brainActivity');
    const appEl = $('brainApp');
    const durEl = $('brainDuration');
    if (subtitle) {
      subtitle.textContent = status.screen?.running ? 'watching 👁' : 'paused';
    }
    const screen = ctx.context?.screen || {};
    if (screen.available) {
      const act = screen.activity || 'unknown';
      const actEmoji = {
        coding: '💻', browsing: '🌐', reading: '📖', communicating: '💬',
        gaming: '🎮', idle: '😴', unknown: '❓',
      }[act] || '👁';
      if (icon) icon.textContent = actEmoji;
      if (actEl) {
        actEl.textContent = act.charAt(0).toUpperCase() + act.slice(1);
      }
      if (appEl) {
        const wt = (screen.window_title || '').slice(0, 40);
        appEl.textContent = screen.app ? `${screen.app}${wt ? ' · ' + wt : ''}` : 'unknown app';
      }
      if (durEl) {
        const min = Math.floor(screen.duration_min || 0);
        const sec = Math.floor(((screen.duration_min || 0) - min) * 60);
        durEl.textContent = `for ${min}m ${sec}s · ${(screen.change_pct || 0).toFixed(0)}% changed`;
      }
    } else {
      if (icon) icon.textContent = '👁';
      if (actEl) actEl.textContent = '—';
      if (appEl) appEl.textContent = 'tap ▶ to start watching';
      if (durEl) durEl.textContent = '';
    }
    const durWrap = $('brainDurations');
    const durations = ctx.context?.today?.app_durations_min || {};
    if (durWrap) {
      const entries = Object.entries(durations).sort((a, b) => b[1] - a[1]).slice(0, 8);
      if (entries.length === 0) {
        durWrap.innerHTML = `<div class="empty-mini">no activity yet</div>`;
      } else {
        durWrap.innerHTML = entries.map(([app, mins]) =>
          `<div class="brain-duration-row"><span class="app">${escapeHtml(app)}</span><span class="minutes">${mins.toFixed(0)}m</span></div>`
        ).join('');
      }
    }
    const scenesWrap = $('brainScenes');
    const scenes = dash.dashboard?.recent_scenes || [];
    if (scenesWrap) {
      if (scenes.length === 0) {
        scenesWrap.innerHTML = `<div class="empty-mini">no scenes yet</div>`;
      } else {
        scenesWrap.innerHTML = scenes.slice(-10).reverse().map(s => {
          const when = new Date(s.ts * 1000);
          const timeStr = when.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
          return `<div class="brain-scene-row">
              <span class="ts">${timeStr}</span>
              <span class="act">${escapeHtml(s.activity)}</span>
              <span style="color: var(--fg-dim); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${escapeHtml(s.app_name || '')}</span>
            </div>`;
        }).join('');
      }
    }
    const suggWrap = $('brainSuggestions');
    const suggList = (sugg.suggestions || []).filter(s =>
      s.category === 'location' || s.category === 'proactive' || s.category === 'health'
    ).slice(0, 5);
    if (suggWrap) {
      if (suggList.length === 0) {
        suggWrap.innerHTML = `<div class="empty-mini">no suggestions right now</div>`;
      } else {
        suggWrap.innerHTML = suggList.map(s =>
          `<div class="brain-suggestion" data-id="${escapeHtml(s.id)}">
            <div class="title">${escapeHtml(s.title)}</div>
            <div class="body">${escapeHtml(s.body || '')}</div>
            ${s.actions && s.actions.length ? `<div class="actions">${s.actions.map(a =>
              `<button data-cmd="${escapeHtml(a.command)}">${escapeHtml(a.label)}</a>`
            ).join('')}</div>` : ''}
          </div>`
        ).join('');
        suggWrap.querySelectorAll('button[data-cmd]').forEach(btn => {
          btn.addEventListener('click', () => {
            const cmd = btn.dataset.cmd;
            if (cmd.startsWith('_')) {
              toast('acknowledged');
            } else {
              wsSend({ type: 'text', text: cmd, source: 'brain-state-action' });
            }
          });
        });
      }
    }
  }

  $('menuBrain')?.addEventListener('click', async () => {
    $('menu').hidden = true;
    await refreshBrainState();
    show('brainState');
  });
  $('brainBackBtn')?.addEventListener('click', () => show('chat'));
  $('brainStartBtn')?.addEventListener('click', async () => {
    if (!state.brain) return;
    try {
      await fetch(`http://${state.brain.host}:${state.brain.port}/api/screen/start`, { method: 'POST' });
      toast('brain watching 👁');
      await refreshBrainState();
    } catch (e) { toast('failed'); }
  });
  $('brainStopBtn')?.addEventListener('click', async () => {
    if (!state.brain) return;
    try {
      await fetch(`http://${state.brain.host}:${state.brain.port}/api/screen/stop`, { method: 'POST' });
      toast('brain paused');
      await refreshBrainState();
    } catch (e) { toast('failed'); }
  });

  // ---------- Service worker ----------
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('./sw.js').catch(() => { /* offline best-effort */ });
    });
  }

  // ---------- Install prompt ----------
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    state.deferredPrompt = e;
  });

  // ---------- Boot ----------
  function boot() {
    // Try restore last connection
    const saved = loadLocal();
    if (saved && saved.brain) {
      const info = attachInfoMethods(saved.brain);
      state.messages = saved.messages || [];
      // Reconnect attempt
      state.brain = info;
      openWebSocket(info);
      // Replay history
      for (const m of state.messages) addMessage(m.role, m.text);
      return;
    }
    // Else: go to discover
    show('discover');
    renderBrains();
    scanSubnet();  // first scan
    state.scanTimer = setInterval(scanSubnet, 8000);
  }

  // Hide boot after a moment
  setTimeout(() => {
    if (!$('boot').hidden) boot();
  }, 600);

  // Expose for debugging
  window.OMNI = { state, scanSubnet, backToDiscover, openWebSocket };
})();
