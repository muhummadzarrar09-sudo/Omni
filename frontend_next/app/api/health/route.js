import { backendFetch, forwardBackendResponse, proxyErrorResponse } from '@/backend'

export async function GET() {
  try {
    const response = await backendFetch('/api/health')
    if (!response.ok) return forwardBackendResponse(response)
    const data = await response.json()
    return Response.json(
      { ...data, nextjs: true, frontend: 'OMNI managed Next.js interface' },
      { status: response.status },
    )
  } catch (error) {
    return proxyErrorResponse(error)
  }
}
