import { backendProxy } from '@/backend'

export function POST(request) {
  return backendProxy('/api/reflect/today', { sourceRequest: request })
}
