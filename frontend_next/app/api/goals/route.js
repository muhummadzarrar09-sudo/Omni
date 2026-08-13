import { backendProxy } from '@/backend'

export function GET() {
  return backendProxy('/api/goals')
}

export function POST(request) {
  return backendProxy('/api/goals', { sourceRequest: request })
}
