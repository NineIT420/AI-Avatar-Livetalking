/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // If your backend is on a different port/domain, configure rewrites
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://52.3.240.147:8010/api/:path*', // FastAPI backend
      },
      {
        source: '/backend/:path*',
        destination: 'https://52.3.240.147:8010/:path*', // Proxy all backend routes to avoid CORS
      },
    ];
  },
};

module.exports = nextConfig;

