import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  productionBrowserSourceMaps: true,
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://127.0.0.1:8000/api/:path*', // Proxy to Backend
      },
      {
        source: '/token',
        destination: 'http://127.0.0.1:8000/token', // Proxy to Backend
      },
    ];
  },
};

export default nextConfig;
