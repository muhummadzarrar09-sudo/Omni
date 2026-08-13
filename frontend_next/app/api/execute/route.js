import { backendProxy } from '@/backend'

export function POST(request) {
  return backendProxy('/api/execute', { sourceRequest: request })
}
