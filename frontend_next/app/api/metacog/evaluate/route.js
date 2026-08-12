import { backendProxy } from '@/backend'

export function POST(request) {
  return backendProxy('/api/metacog/evaluate', { sourceRequest: request })
}
