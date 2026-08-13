import assert from 'node:assert/strict'
import test from 'node:test'

import {
  configuredBrowserOrigins,
  enforceMutationOrigin,
  ProxyPolicyError,
} from '../proxy-policy.mjs'

process.env.OMNI_CORS_ORIGINS = 'http://127.0.0.1:3000,http://localhost:3000,https://preview.example'

function request(origin, extraHeaders = {}) {
  const headers = { ...extraHeaders }
  if (origin !== undefined) headers.Origin = origin
  return new Request('http://127.0.0.1:3000/api/execute', {
    method: 'POST',
    headers,
  })
}

function rejectsWith(code, candidate, status = 403) {
  assert.throws(
    candidate,
    (error) => error instanceof ProxyPolicyError && error.status === status && error.code === code,
  )
}

test('accepts explicitly configured same-origin and reverse-proxy mutations', () => {
  enforceMutationOrigin(
    request('http://127.0.0.1:3000', { 'Sec-Fetch-Site': 'same-origin' }),
    'POST',
  )
  enforceMutationOrigin(
    request('https://preview.example', {
      'Sec-Fetch-Site': 'same-origin',
      'X-Forwarded-Host': 'attacker-controlled.example',
      'X-Forwarded-Proto': 'https',
    }),
    'PATCH',
  )
})

test('does not trust request URL or forwarded headers as an origin allowlist', () => {
  rejectsWith('cross_origin_mutation_rejected', () => {
    enforceMutationOrigin(
      request('https://attacker.example', {
        'Sec-Fetch-Site': 'same-origin',
        'X-Forwarded-Host': 'attacker.example',
        'X-Forwarded-Proto': 'https',
      }),
      'POST',
    )
  })
})

test('rejects cross-origin, opaque, invalid, and originless mutations', () => {
  rejectsWith('cross_origin_mutation_rejected', () => {
    enforceMutationOrigin(
      request('https://attacker.example', { 'Sec-Fetch-Site': 'cross-site' }),
      'POST',
    )
  })
  rejectsWith('cross_origin_mutation_rejected', () => enforceMutationOrigin(request('null'), 'DELETE'))
  rejectsWith('invalid_origin', () => enforceMutationOrigin(request('not an origin'), 'PUT'))
  rejectsWith('missing_origin', () => enforceMutationOrigin(request(undefined), 'POST'))
})

test('rejects cross-site Fetch Metadata even with an allowlisted Origin', () => {
  rejectsWith('cross_origin_mutation_rejected', () => {
    enforceMutationOrigin(
      request('http://127.0.0.1:3000', { 'Sec-Fetch-Site': 'cross-site' }),
      'POST',
    )
  })
})

test('allows safe methods without request context', () => {
  enforceMutationOrigin(undefined, 'GET')
  enforceMutationOrigin(undefined, 'HEAD')
  enforceMutationOrigin(undefined, 'OPTIONS')
})

test('fails closed when request context or configured origins are absent', () => {
  rejectsWith('proxy_policy_error', () => enforceMutationOrigin(undefined, 'POST'), 500)
  assert.throws(
    () => configuredBrowserOrigins(''),
    (error) => (
      error instanceof ProxyPolicyError
      && error.status === 500
      && error.code === 'proxy_policy_error'
    ),
  )
  assert.throws(() => configuredBrowserOrigins('*'))
  assert.throws(() => configuredBrowserOrigins('https://example.test/path'))
})
