import { backendProxy } from '@/backend'

export function GET() {
  return backendProxy('/api/away/tasks')
}

export function POST(request) {
  return backendProxy('/api/away/tasks', { sourceRequest: request })
}
