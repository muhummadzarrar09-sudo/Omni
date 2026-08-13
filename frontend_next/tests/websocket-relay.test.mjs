import assert from 'node:assert/strict'
import { EventEmitter } from 'node:events'
import test from 'node:test'

import relayModule from '../websocket-relay.js'

const {
  createWebSocketRelay,
  parseAllowedOrigins,
  parseUpstreamHandshake,
  validateBackendUrl,
  validateUpgradeRequest,
} = relayModule

const KEY = 'dGhlIHNhbXBsZSBub25jZQ=='
const ACCEPT = 's3pPLMBiTxaQ9kYGzzhZRbK+xOo='
const ORIGIN = 'http://127.0.0.1:3000'

function request(overrides = {}) {
  const headers = {
    connection: 'keep-alive, Upgrade',
    upgrade: 'websocket',
    origin: ORIGIN,
    'sec-websocket-key': KEY,
    'sec-websocket-version': '13',
    ...(overrides.headers || {}),
  }
  return {
    method: 'GET',
    httpVersionMajor: 1,
    httpVersionMinor: 1,
    url: '/ws?token=abcdefghijklmnopqrstuvwxyz',
    rawHeaders: Object.entries(headers).flat(),
    ...overrides,
    headers,
  }
}

class FakeSocket extends EventEmitter {
  constructor() {
    super()
    this.destroyed = false
    this.output = []
    this.paused = false
    this.pipeTargets = []
  }

  pause() { this.paused = true }
  resume() { this.paused = false }
  write(value) { this.output.push(Buffer.from(value)); return true }
  pipe(target) { this.pipeTargets.push(target); return target }
  end(value) {
    if (value) this.write(value)
    if (!this.destroyed) {
      this.destroyed = true
      this.emit('close')
    }
  }
  destroy() {
    if (!this.destroyed) {
      this.destroyed = true
      this.emit('close')
    }
  }
  text() { return Buffer.concat(this.output).toString('latin1') }
}

const allowedOrigins = parseAllowedOrigins(`${ORIGIN},https://preview.example`)

test('accepts only exact configured WebSocket origins and valid ticket upgrades', () => {
  const valid = validateUpgradeRequest(request(), allowedOrigins)
  assert.equal(valid.incomingUrl.pathname, '/ws')

  assert.equal(validateUpgradeRequest(request({ headers: { origin: undefined } }), allowedOrigins).status, 403)
  assert.equal(
    validateUpgradeRequest(request({ headers: { origin: 'https://attacker.example' } }), allowedOrigins).status,
    403,
  )
  assert.equal(
    validateUpgradeRequest(request({ url: '/ws?token=abcdefghijklmnop&token=qrstuvwxyzabcdef' }), allowedOrigins).status,
    400,
  )
  assert.equal(validateUpgradeRequest(request({ method: 'POST' }), allowedOrigins).status, 400)
  assert.equal(
    validateUpgradeRequest(request({ headers: { 'sec-websocket-key': 'not-base64' } }), allowedOrigins).status,
    400,
  )
})

test('rejects malformed configuration and backend targets', () => {
  assert.throws(() => parseAllowedOrigins(''))
  assert.throws(() => parseAllowedOrigins('*'))
  assert.throws(() => parseAllowedOrigins('https://example.test/path'))
  assert.throws(() => validateBackendUrl('https://127.0.0.1:8000'))
  assert.throws(() => validateBackendUrl('http://user:pass@127.0.0.1:8000'))
  assert.throws(() => validateBackendUrl('http://127.0.0.1:8000/api'))
})

test('parses only a complete and cryptographically matching backend handshake', () => {
  const valid = Buffer.from(
    `HTTP/1.1 101 Switching Protocols\r\nConnection: Upgrade\r\nUpgrade: websocket\r\nSec-WebSocket-Accept: ${ACCEPT}\r\n\r\n`,
  )
  assert.equal(parseUpstreamHandshake(valid, KEY), valid.length)
  assert.equal(parseUpstreamHandshake(valid.subarray(0, valid.length - 2), KEY), null)
  assert.throws(() => parseUpstreamHandshake(Buffer.from('HTTP/1.1 200 OK\r\n\r\n'), KEY))
  assert.throws(() => parseUpstreamHandshake(Buffer.from(
    'HTTP/1.1 101 Switching Protocols\r\nConnection: Upgrade\r\nUpgrade: websocket\r\nSec-WebSocket-Accept: wrong\r\n\r\n',
  ), KEY))
})

test('rejects malformed upgrades before opening a backend connection', () => {
  let connections = 0
  const relay = createWebSocketRelay({
    backendUrl: 'http://127.0.0.1:8000',
    allowedOrigins,
    connect: () => { connections += 1; return new FakeSocket() },
  })
  const client = new FakeSocket()
  relay(request({ headers: { origin: 'https://attacker.example' } }), client, Buffer.alloc(0))
  assert.equal(connections, 0)
  assert.match(client.text(), /^HTTP\/1\.1 403 /)
  assert.equal(client.destroyed, true)
})

test('bounds backend handshake parsing and closes both sides on overflow', () => {
  const upstream = new FakeSocket()
  const client = new FakeSocket()
  const relay = createWebSocketRelay({
    backendUrl: 'http://127.0.0.1:8000',
    allowedOrigins,
    connect: () => upstream,
    maxHandshakeBytes: 512,
  })
  relay(request(), client, Buffer.alloc(0))
  upstream.emit('connect')
  upstream.emit('data', Buffer.alloc(513, 65))
  assert.equal(upstream.destroyed, true)
  assert.equal(client.destroyed, true)
  assert.match(client.text(), /^HTTP\/1\.1 502 /)
})

test('times out a backend that never connects and cleans up both sockets', async () => {
  const upstream = new FakeSocket()
  const client = new FakeSocket()
  const relay = createWebSocketRelay({
    backendUrl: 'http://127.0.0.1:8000',
    allowedOrigins,
    connect: () => upstream,
    connectTimeoutMs: 20,
  })
  relay(request(), client, Buffer.alloc(0))
  await new Promise((resolve) => setTimeout(resolve, 50))
  assert.equal(upstream.destroyed, true)
  assert.equal(client.destroyed, true)
  assert.match(client.text(), /^HTTP\/1\.1 504 /)
})

test('relays only after a valid backend handshake and cleans up on client close', () => {
  const upstream = new FakeSocket()
  const client = new FakeSocket()
  const relay = createWebSocketRelay({
    backendUrl: 'http://127.0.0.1:8000',
    allowedOrigins,
    connect: () => upstream,
  })
  relay(request(), client, Buffer.from('early-frame'))
  upstream.emit('connect')
  assert.match(upstream.text(), /^GET \/ws\?token=abcdefghijklmnopqrstuvwxyz HTTP\/1\.1/)
  assert.doesNotMatch(upstream.text(), /early-frame/)

  upstream.emit('data', Buffer.from(
    `HTTP/1.1 101 Switching Protocols\r\nConnection: Upgrade\r\nUpgrade: websocket\r\nSec-WebSocket-Accept: ${ACCEPT}\r\n\r\n`,
  ))
  assert.match(client.text(), /^HTTP\/1\.1 101 /)
  assert.match(upstream.text(), /early-frame/)
  assert.deepEqual(client.pipeTargets, [upstream])
  assert.deepEqual(upstream.pipeTargets, [client])

  client.destroy()
  assert.equal(upstream.destroyed, true)
})
