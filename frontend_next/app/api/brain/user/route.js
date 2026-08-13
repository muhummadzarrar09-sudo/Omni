import { backendProxy } from '@/backend'

export function GET() {
  return backendProxy('/api/brain/identity/user')
}

export function POST(request) {
  return backendProxy('/api/brain/identity/user', { sourceRequest: request })
}
