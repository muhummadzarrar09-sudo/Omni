const http = require('http')
const next = require('next')

const { createWebSocketRelay, parseAllowedOrigins } = require('./websocket-relay')

const hostname = process.env.OMNI_FRONTEND_HOST
const port = Number(process.env.OMNI_FRONTEND_PORT)
const configuredBackendUrl = process.env.OMNI_BACKEND_URL
const configuredOrigins = process.env.OMNI_CORS_ORIGINS

if (!hostname || !Number.isInteger(port) || !configuredBackendUrl || !configuredOrigins) {
  throw new Error(
    'OMNI_FRONTEND_HOST, OMNI_FRONTEND_PORT, OMNI_BACKEND_URL, and OMNI_CORS_ORIGINS are required',
  )
}

const relayWebSocket = createWebSocketRelay({
  backendUrl: configuredBackendUrl,
  allowedOrigins: parseAllowedOrigins(configuredOrigins),
})
const app = next({ dev: process.argv.includes('--dev'), dir: __dirname, hostname, port })
const handle = app.getRequestHandler()

app.prepare()
  .then(() => {
    const server = http.createServer((request, response) => handle(request, response))
    server.headersTimeout = 15_000
    server.requestTimeout = 30_000
    server.on('upgrade', relayWebSocket)
    server.listen(port, hostname, () => {
      console.log(`OMNI interface ready on http://${hostname}:${port}`)
    })
  })
  .catch((error) => {
    console.error(error)
    process.exit(1)
  })
