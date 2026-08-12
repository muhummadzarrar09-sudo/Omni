/** @type {import('next').NextConfig} */
const configuredBackendUrl = process.env.OMNI_BACKEND_URL
if (!configuredBackendUrl) {
  throw new Error('OMNI_BACKEND_URL is required; use the managed OMNI installer or launcher')
}

const nextConfig = {
  turbopack: {
    root: __dirname,
  },
}

module.exports = nextConfig
