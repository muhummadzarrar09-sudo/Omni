import { backendProxy } from '@/backend'

async function proxy(request, context) {
  const { path } = await context.params
  const backendPath = `/api/${path.map(encodeURIComponent).join('/')}${request.nextUrl.search}`
  return backendProxy(backendPath, { sourceRequest: request, cache: 'no-store' })
}

export const dynamic = 'force-dynamic'
export const GET = proxy
export const HEAD = proxy
export const POST = proxy
export const PUT = proxy
export const PATCH = proxy
export const DELETE = proxy
