/** @type {import('next').NextConfig} */
const backendUrl = (process.env.OMNI_BACKEND_URL || 'http://127.0.0.1:8765').replace(/\/$/, '')

const nextConfig = {
  turbopack: {
    root: __dirname,
  },
  async rewrites() {
    return [
      {
        source: '/api/python/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
      {
        source: '/ws',
        destination: `${backendUrl}/ws`,
      },
    ]
  },
}

module.exports = nextConfig
