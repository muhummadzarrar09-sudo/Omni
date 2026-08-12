'use strict'

const crypto = require('crypto')
const net = require('net')

const WEBSOCKET_GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
const DEFAULT_MAX_HANDSHAKE_BYTES = 16 * 1024
const DEFAULT_TIMEOUT_MS = 5_000

function parseAllowedOrigins(raw) {
  if (!raw) throw new Error('OMNI_CORS_ORIGINS is required for WebSocket origin enforcement')
  const origins = new Set()
  for (const candidate of raw.split(',')) {
    const value = candidate.trim()
    let parsed
    try {
      parsed = new URL(value)
    } catch {
      throw new Error('OMNI_CORS_ORIGINS contains an invalid WebSocket origin')
    }
    if (
      !['http:', 'https:'].includes(parsed.protocol)
      || parsed.username
      || parsed.password
      || parsed.pathname !== '/'
      || parsed.search
      || parsed.hash
      || value === '*'
    ) {
      throw new Error('OMNI_CORS_ORIGINS must contain exact HTTP(S) origins')
    }
    origins.add(parsed.origin)
  }
  if (!origins.size) throw new Error('No trusted WebSocket origin is configured')
  return origins
}

function headerHasToken(value, expected) {
  return String(value || '')
    .split(',')
    .some((item) => item.trim().toLowerCase() === expected)
}

function validateWebSocketKey(value) {
  if (typeof value !== 'string' || value.length > 64) return false
  try {
    return Buffer.from(value, 'base64').length === 16 && Buffer.from(value, 'base64').toString('base64') === value
  } catch {
    return false
  }
}

function validateUpgradeRequest(request, allowedOrigins, maxHandshakeBytes = DEFAULT_MAX_HANDSHAKE_BYTES) {
  const serializedBytes = (request.rawHeaders || []).reduce(
    (total, value) => total + Buffer.byteLength(String(value)) + 4,
    Buffer.byteLength(String(request.url || '')),
  )
  if (serializedBytes > maxHandshakeBytes) return { status: 431, reason: 'Request headers too large' }
  if (request.method !== 'GET' || request.httpVersionMajor !== 1 || request.httpVersionMinor < 1) {
    return { status: 400, reason: 'Malformed WebSocket upgrade' }
  }
  if (
    !headerHasToken(request.headers.connection, 'upgrade')
    || String(request.headers.upgrade || '').toLowerCase() !== 'websocket'
    || String(request.headers['sec-websocket-version'] || '') !== '13'
    || !validateWebSocketKey(request.headers['sec-websocket-key'])
  ) {
    return { status: 400, reason: 'Malformed WebSocket upgrade' }
  }

  let incomingUrl
  try {
    incomingUrl = new URL(request.url, 'http://omni.invalid')
  } catch {
    return { status: 400, reason: 'Malformed WebSocket target' }
  }
  const tokens = incomingUrl.searchParams.getAll('token')
  const unexpectedQuery = [...incomingUrl.searchParams.keys()].some((key) => key !== 'token')
  if (
    incomingUrl.pathname !== '/ws'
    || unexpectedQuery
    || tokens.length !== 1
    || tokens[0].length < 16
    || tokens[0].length > 512
  ) {
    return { status: 400, reason: 'Invalid WebSocket target or ticket' }
  }

  const origin = request.headers.origin
  let normalizedOrigin
  try {
    normalizedOrigin = origin ? new URL(origin).origin : ''
  } catch {
    return { status: 403, reason: 'Invalid WebSocket Origin' }
  }
  if (!normalizedOrigin || !allowedOrigins.has(normalizedOrigin)) {
    return { status: 403, reason: 'WebSocket Origin is not trusted' }
  }
  return { incomingUrl, key: request.headers['sec-websocket-key'] }
}

function validateBackendUrl(raw) {
  const backendUrl = new URL(raw)
  if (
    backendUrl.protocol !== 'http:'
    || backendUrl.username
    || backendUrl.password
    || !['', '/'].includes(backendUrl.pathname)
    || backendUrl.search
    || backendUrl.hash
  ) {
    throw new Error('The managed WebSocket relay requires a credential-free HTTP backend origin')
  }
  const port = Number(backendUrl.port || 80)
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    throw new Error('The managed WebSocket relay backend port is invalid')
  }
  return backendUrl
}

function rejectSocket(socket, status, reason) {
  if (socket.destroyed) return
  const safeReason = String(reason).replace(/[\r\n]/g, ' ').slice(0, 120)
  const body = `${safeReason}\n`
  socket.end(
    `HTTP/1.1 ${status} ${safeReason}\r\n`
    + 'Connection: close\r\n'
    + 'Content-Type: text/plain; charset=utf-8\r\n'
    + `Content-Length: ${Buffer.byteLength(body)}\r\n\r\n`
    + body,
  )
}

function parseUpstreamHandshake(buffer, key) {
  const boundary = buffer.indexOf('\r\n\r\n')
  if (boundary < 0) return null
  const lines = buffer.subarray(0, boundary).toString('latin1').split('\r\n')
  if (!/^HTTP\/1\.[01] 101(?: |$)/.test(lines.shift() || '')) {
    throw new Error('Backend rejected the WebSocket upgrade')
  }
  const headers = new Map()
  for (const line of lines) {
    const separator = line.indexOf(':')
    if (separator <= 0 || /^[ \t]/.test(line)) throw new Error('Malformed backend handshake')
    const name = line.slice(0, separator).trim().toLowerCase()
    const value = line.slice(separator + 1).trim()
    headers.set(name, headers.has(name) ? `${headers.get(name)},${value}` : value)
  }
  const expectedAccept = crypto.createHash('sha1').update(`${key}${WEBSOCKET_GUID}`).digest('base64')
  if (
    !headerHasToken(headers.get('connection'), 'upgrade')
    || String(headers.get('upgrade') || '').toLowerCase() !== 'websocket'
    || headers.get('sec-websocket-accept') !== expectedAccept
  ) {
    throw new Error('Backend returned an invalid WebSocket handshake')
  }
  return boundary + 4
}

function createWebSocketRelay(options) {
  const backendUrl = validateBackendUrl(options.backendUrl)
  const allowedOrigins = options.allowedOrigins instanceof Set
    ? options.allowedOrigins
    : parseAllowedOrigins(options.allowedOrigins)
  const connect = options.connect || net.connect
  const connectTimeoutMs = options.connectTimeoutMs || DEFAULT_TIMEOUT_MS
  const handshakeTimeoutMs = options.handshakeTimeoutMs || DEFAULT_TIMEOUT_MS
  const maxHandshakeBytes = options.maxHandshakeBytes || DEFAULT_MAX_HANDSHAKE_BYTES

  return function relayWebSocket(request, clientSocket, head = Buffer.alloc(0)) {
    const validation = validateUpgradeRequest(request, allowedOrigins, maxHandshakeBytes)
    if (validation.status) {
      rejectSocket(clientSocket, validation.status, validation.reason)
      return
    }
    if (head.length > maxHandshakeBytes) {
      rejectSocket(clientSocket, 413, 'Initial WebSocket frame is too large')
      return
    }

    clientSocket.pause()
    let upstream
    let established = false
    let terminal = false
    let connectTimer
    let handshakeTimer

    const clearTimers = () => {
      clearTimeout(connectTimer)
      clearTimeout(handshakeTimer)
    }
    const failBeforeUpgrade = (status, reason) => {
      if (terminal) return
      terminal = true
      clearTimers()
      if (upstream && !upstream.destroyed) upstream.destroy()
      rejectSocket(clientSocket, status, reason)
    }
    const closePeer = (peer) => {
      if (!peer.destroyed) peer.destroy()
    }

    try {
      upstream = connect({
        host: backendUrl.hostname.replace(/^\[|\]$/g, ''),
        port: Number(backendUrl.port || 80),
      })
    } catch {
      failBeforeUpgrade(502, 'OMNI backend connection failed')
      return
    }

    clientSocket.once('error', () => closePeer(upstream))
    clientSocket.once('close', () => {
      clearTimers()
      closePeer(upstream)
    })
    upstream.once('error', () => {
      if (established) closePeer(clientSocket)
      else failBeforeUpgrade(502, 'OMNI backend connection failed')
    })
    upstream.once('close', () => {
      clearTimers()
      if (established) closePeer(clientSocket)
    })

    connectTimer = setTimeout(
      () => failBeforeUpgrade(504, 'OMNI backend connection timed out'),
      connectTimeoutMs,
    )
    connectTimer.unref?.()

    upstream.once('connect', () => {
      clearTimeout(connectTimer)
      const forwardedHeaders = [
        ['Host', backendUrl.host],
        ['Connection', 'Upgrade'],
        ['Upgrade', 'websocket'],
        ['Origin', request.headers.origin],
        ['Sec-WebSocket-Key', request.headers['sec-websocket-key']],
        ['Sec-WebSocket-Version', '13'],
      ]
      for (const name of ['sec-websocket-protocol', 'sec-websocket-extensions', 'user-agent']) {
        const value = request.headers[name]
        if (typeof value === 'string' && !/[\r\n]/.test(value)) forwardedHeaders.push([name, value])
      }
      const lines = forwardedHeaders.map(([name, value]) => `${name}: ${value}`).join('\r\n')
      upstream.write(`GET /ws${validation.incomingUrl.search} HTTP/1.1\r\n${lines}\r\n\r\n`)

      handshakeTimer = setTimeout(
        () => failBeforeUpgrade(504, 'OMNI backend handshake timed out'),
        handshakeTimeoutMs,
      )
      handshakeTimer.unref?.()
      let response = Buffer.alloc(0)
      const onHandshakeData = (chunk) => {
        if (terminal) return
        response = Buffer.concat([response, chunk])
        const headerBoundary = response.indexOf('\r\n\r\n')
        if (
          (headerBoundary < 0 && response.length > maxHandshakeBytes)
          || headerBoundary + 4 > maxHandshakeBytes
        ) {
          failBeforeUpgrade(502, 'OMNI backend handshake is too large')
          return
        }
        let boundary
        try {
          boundary = parseUpstreamHandshake(response, validation.key)
        } catch {
          failBeforeUpgrade(502, 'OMNI backend returned an invalid WebSocket handshake')
          return
        }
        if (boundary === null) return

        established = true
        terminal = true
        clearTimers()
        upstream.off('data', onHandshakeData)
        clientSocket.write(response)
        if (head.length) upstream.write(head)
        clientSocket.resume()
        clientSocket.pipe(upstream)
        upstream.pipe(clientSocket)
      }
      upstream.on('data', onHandshakeData)
    })
  }
}

module.exports = {
  createWebSocketRelay,
  parseAllowedOrigins,
  parseUpstreamHandshake,
  validateBackendUrl,
  validateUpgradeRequest,
}
