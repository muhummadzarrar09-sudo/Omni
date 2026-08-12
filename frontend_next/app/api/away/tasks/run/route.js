import { backendProxy } from '@/backend'

export function POST(request) {
  return backendProxy('/api/away/tasks/run', { sourceRequest: request })
}
