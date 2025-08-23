import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  productionBrowserSourceMaps: true,
  output: 'standalone',
  eslint: {
    // Disable ESLint during builds (for staging/production)
    ignoreDuringBuilds: true,
  },
  typescript: {
    // Disable TypeScript checking during builds (for staging)
    ignoreBuildErrors: true,
  },
  swcMinify: false,
  async rewrites() {
    // Proxy API routes to backend service
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    return [
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
      {
        source: '/health/:path*', 
        destination: `${backendUrl}/health/:path*`,
      },
      {
        source: '/openapi.json',
        destination: `${backendUrl}/openapi.json`,
      },
    ];
  },
  outputFileTracingIncludes: {
    '/api': ['./node_modules/**/*.js'],
    '/_next': ['./node_modules/**/*.js']
  },
  images: {
    domains: ['localhost', 'staging.netrasystems.ai']
  },
  webpack: (config, { isServer }) => {
    // Optimize for Docker builds
    if (isServer) {
      config.externals = [...(config.externals || []), 'canvas', 'jsdom'];
    }
    return config;
  }
};

export default nextConfig;
