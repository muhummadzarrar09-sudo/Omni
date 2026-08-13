import { backendProxy } from '@/backend'

export function POST(request) {
  return backendProxy('/api/security/lock', {
    sourceRequest: request,
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason: 'manual lock from OMNI web UI' }),
  })
}
