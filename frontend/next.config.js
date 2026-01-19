/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // If your backend is on a different port/domain, configure rewrites
  async rewrites() {
    return [
      {
        source: '/:path*',
        destination: 'https://52.3.240.147:8010/:path*', // FastAPI backend - proxy all requests
      },
    ];
  },
};

module.exports = nextConfig;

