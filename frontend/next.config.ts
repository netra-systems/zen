import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  productionBrowserSourceMaps: process.env.NODE_ENV !== 'production',
  output: 'standalone',
  eslint: {
    // Disable ESLint during builds (for staging/production)
    ignoreDuringBuilds: true,
  },
  typescript: {
    // Disable TypeScript checking during builds (for staging)
    ignoreBuildErrors: true,
  },
  swcMinify: process.env.NODE_ENV === 'production',
  // Optimize based on environment
  experimental: {
    optimizeCss: process.env.NODE_ENV === 'production',
    optimizePackageImports: ['lucide-react', '@radix-ui/*', 'framer-motion', 'react-markdown'],
  },
  async headers() {
    const isDevelopment = process.env.NODE_ENV === 'development';
    
    if (isDevelopment) {
      // In development, use a more permissive CSP without nonces
      return [
        {
          source: '/:path*',
          headers: [
            {
              key: 'Content-Security-Policy',
              value: [
                "default-src 'self' http://localhost:* http://127.0.0.1:* ws://localhost:* ws://127.0.0.1:*",
                "script-src 'self' 'unsafe-eval' 'unsafe-inline' http://localhost:* http://127.0.0.1:*",
                "style-src 'self' 'unsafe-inline' http://localhost:* http://127.0.0.1:*",
                "img-src 'self' data: blob: http://localhost:* http://127.0.0.1:*",
                "connect-src 'self' http://localhost:* http://127.0.0.1:* ws://localhost:* ws://127.0.0.1:* wss://localhost:* wss://127.0.0.1:*",
                "font-src 'self' data: http://localhost:* http://127.0.0.1:*",
                "media-src 'self' http://localhost:* http://127.0.0.1:*",
                "frame-src 'self' http://localhost:* http://127.0.0.1:*"
              ].join('; ')
            }
          ]
        }
      ];
    }
    
    // For production, return empty array - CSP will be handled by middleware with proper nonce support
    return [];
  },
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
  webpack: (config, { isServer, isProduction }) => {
    // Exclude test files and mocks from production builds
    if (isProduction) {
      config.module.rules.push({
        test: /\.(test|spec)\.(ts|tsx|js|jsx)$/,
        loader: 'ignore-loader'
      });
      
      // Exclude mock directories
      config.module.rules.push({
        test: /\/__mocks__\//,
        loader: 'ignore-loader'
      });
      
      // Exclude test utilities
      config.module.rules.push({
        test: /\/__tests__\//,
        loader: 'ignore-loader'
      });
    }
    
    if (!isServer) {
      // Don't bundle certain large test packages on client side
      config.resolve.alias = {
        ...config.resolve.alias,
        'msw/node': false,
        'jest-websocket-mock': false,
        '@testing-library/react': false,
        '@testing-library/jest-dom': false,
      };
    }
    
    // Optimize for Docker builds
    if (isServer) {
      config.externals = [...(config.externals || []), 'canvas', 'jsdom'];
    }
    
    return config;
  }
};

export default nextConfig;
