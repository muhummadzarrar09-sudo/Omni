/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/python/:path*',
        destination: 'http://localhost:8765/api/:path*', // Proxy to FastAPI
      },
    ];
  },
};

module.exports = nextConfig;
