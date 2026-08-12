import { backendProxy } from '@/backend'

export async function GET(request, { params }) {
  const { type } = await params
  return backendProxy(`/api/demo/${encodeURIComponent(type)}`)
}
