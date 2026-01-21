/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_BASE_URL || 'https://52.3.240.147:8010'}/:path*`, // FastAPI backend - proxy all requests
      },
    ];
  },
};

module.exports = nextConfig;

