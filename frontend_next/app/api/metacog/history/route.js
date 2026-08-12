import { backendProxy } from '@/backend'

export function GET() {
  return backendProxy('/api/metacog/history')
}
