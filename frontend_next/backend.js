import 'server-only'

import { enforceMutationOrigin, ProxyPolicyError } from './proxy-policy.mjs'

const MAX_PROXY_REQUEST_BYTES = 64 * 1024
const BACKEND_TIMEOUT_MS = 15_000

function backendBaseUrl() {
  const raw = process.env.OMNI_BACKEND_URL
  if (!raw) {
    throw new Error('OMNI_BACKEND_URL is required; start the interface with the managed OMNI launcher')
  }
  const url = new URL(raw)
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash) {
    throw new Error('OMNI_BACKEND_URL must be a credential-free HTTP(S) origin')
  }
  return url
}

export async function backendFetch(path, options = {}) {
  const { sourceRequest, ...fetchOptions } = options
  const method = String(fetchOptions.method || 'GET').toUpperCase()
  enforceMutationOrigin(sourceRequest, method)

  const base = backendBaseUrl()
  const url = new URL(path, `${base.href.replace(/\/$/, '')}/`)
  if (url.origin !== base.origin) {
    throw new Error('Backend proxy path must remain on the configured OMNI backend origin')
  }
  const headers = new Headers(fetchOptions.headers || {})
  const token = process.env.OMNI_API_TOKEN
  if (token) headers.set('X-OMNI-Token', token)
  const timeoutSignal = AbortSignal.timeout(BACKEND_TIMEOUT_MS)
  const signal = fetchOptions.signal
    ? AbortSignal.any([fetchOptions.signal, timeoutSignal])
    : timeoutSignal
  return fetch(url, {
    ...fetchOptions,
    method,
    headers,
    signal,
    cache: fetchOptions.cache || 'no-store',
  })
}

export function forwardBackendResponse(response) {
  const headers = new Headers()
  for (const name of ['content-type', 'cache-control', 'retry-after']) {
    const value = response.headers.get(name)
    if (value) headers.set(name, value)
  }
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers,
  })
}

export function proxyErrorResponse(error) {
  if (error instanceof ProxyPolicyError) {
    return Response.json(
      { ok: false, error: error.code, detail: error.message },
      { status: error.status, headers: { 'Cache-Control': 'no-store' } },
    )
  }
  console.error('OMNI backend proxy failure:', error)
  return Response.json(
    {
      ok: false,
      error: 'backend_unavailable',
      detail: 'The OMNI backend is unavailable. Start or repair it with the managed launcher and inspect preflight diagnostics.',
    },
    { status: 503, headers: { 'Cache-Control': 'no-store' } },
  )
}

export async function backendProxy(path, options = {}) {
  try {
    const { sourceRequest, ...fetchOptions } = options
    const method = String(fetchOptions.method || sourceRequest?.method || 'GET').toUpperCase()
    const headers = new Headers(fetchOptions.headers || {})
    let body = fetchOptions.body
    if (sourceRequest && body === undefined && !['GET', 'HEAD'].includes(method)) {
      const declaredLength = Number(sourceRequest.headers.get('content-length') || 0)
      if (!Number.isFinite(declaredLength) || declaredLength < 0 || declaredLength > MAX_PROXY_REQUEST_BYTES) {
        throw new ProxyPolicyError(
          413,
          'proxy_request_too_large',
          `Proxy request bodies are limited to ${MAX_PROXY_REQUEST_BYTES} bytes.`,
        )
      }
      const contentType = sourceRequest.headers.get('content-type')
      if (contentType) headers.set('Content-Type', contentType)
      const bytes = await sourceRequest.arrayBuffer()
      if (bytes.byteLength > MAX_PROXY_REQUEST_BYTES) {
        throw new ProxyPolicyError(
          413,
          'proxy_request_too_large',
          `Proxy request bodies are limited to ${MAX_PROXY_REQUEST_BYTES} bytes.`,
        )
      }
      if (bytes.byteLength) body = bytes
    }
    const response = await backendFetch(path, {
      ...fetchOptions,
      sourceRequest,
      method,
      headers,
      body,
    })
    return forwardBackendResponse(response)
  } catch (error) {
    return proxyErrorResponse(error)
  }
}
