const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS'])

export class ProxyPolicyError extends Error {
  constructor(status, code, message) {
    super(message)
    this.name = 'ProxyPolicyError'
    this.status = status
    this.code = code
  }
}

export function configuredBrowserOrigins(raw = process.env.OMNI_CORS_ORIGINS) {
  if (!raw) {
    throw new ProxyPolicyError(
      500,
      'proxy_policy_error',
      'OMNI_CORS_ORIGINS is required for browser proxy origin enforcement.',
    )
  }
  const origins = new Set()
  for (const candidate of raw.split(',')) {
    try {
      const parsed = new URL(candidate.trim())
      if (
        !['http:', 'https:'].includes(parsed.protocol)
        || parsed.username
        || parsed.password
        || parsed.pathname !== '/'
        || parsed.search
        || parsed.hash
        || candidate.trim() === '*'
      ) {
        throw new Error('not an exact HTTP origin')
      }
      origins.add(parsed.origin)
    } catch {
      throw new ProxyPolicyError(
        500,
        'proxy_policy_error',
        'OMNI_CORS_ORIGINS contains an invalid browser origin.',
      )
    }
  }
  if (!origins.size) {
    throw new ProxyPolicyError(500, 'proxy_policy_error', 'No trusted browser origin is configured.')
  }
  return origins
}

export function enforceMutationOrigin(request, method = 'GET') {
  const normalizedMethod = method.toUpperCase()
  if (SAFE_METHODS.has(normalizedMethod)) return
  if (!request) {
    throw new ProxyPolicyError(
      500,
      'proxy_policy_error',
      'A mutating proxy call omitted its inbound request context.',
    )
  }

  const fetchSite = request.headers.get('sec-fetch-site')?.toLowerCase()
  const origin = request.headers.get('origin')
  if (!origin) {
    throw new ProxyPolicyError(
      403,
      'missing_origin',
      'Browser-facing mutations require an explicit trusted Origin header.',
    )
  }
  if (fetchSite === 'cross-site' || origin === 'null') {
    throw new ProxyPolicyError(
      403,
      'cross_origin_mutation_rejected',
      'Cross-origin browser mutations are not permitted.',
    )
  }

  let normalizedOrigin
  try {
    normalizedOrigin = new URL(origin).origin
  } catch {
    throw new ProxyPolicyError(
      403,
      'invalid_origin',
      'The browser mutation supplied an invalid Origin header.',
    )
  }
  if (!configuredBrowserOrigins().has(normalizedOrigin)) {
    throw new ProxyPolicyError(
      403,
      'cross_origin_mutation_rejected',
      'Cross-origin browser mutations are not permitted.',
    )
  }
}
