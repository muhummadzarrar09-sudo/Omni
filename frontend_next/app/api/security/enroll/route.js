import { backendProxy } from '@/backend'

export function POST(request) {
  return backendProxy('/api/security/enroll', {
    sourceRequest: request,
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ frames: 6, delay: 0.25 }),
  })
}
