import { backendProxy } from '@/backend'

export function POST(request) {
  return backendProxy('/api/security/guard/arm', { sourceRequest: request })
}
