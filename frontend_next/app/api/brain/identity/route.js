import { backendProxy } from '@/backend'

export function GET() {
  return backendProxy('/api/brain/identity')
}

export function POST(request) {
  return backendProxy('/api/brain/identity', { sourceRequest: request })
}
