/** @type {import('next').NextConfig} */
const nextConfig = {
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
  // Optimize based on environment
  experimental: {
    optimizeCss: process.env.NODE_ENV === 'production',
    optimizePackageImports: ['@radix-ui/*', 'framer-motion', 'react-markdown'],
  },
  async headers() {
    const isDevelopment = process.env.NODE_ENV === 'development';
    const isStaging = process.env.NEXT_PUBLIC_ENVIRONMENT === 'staging';
    
    // Static file caching headers for all environments
    const staticFileHeaders = [
      {
        source: '/favicon.ico',
        headers: [
          { key: 'Cache-Control', value: 'public, max-age=31536000, immutable' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
        ],
      },
      {
        source: '/robots.txt',
        headers: [
          { key: 'Cache-Control', value: 'public, max-age=86400' },
          { key: 'Content-Type', value: 'text/plain' },
        ],
      },
      {
        source: '/sitemap.xml',
        headers: [
          { key: 'Cache-Control', value: 'public, max-age=86400' },
          { key: 'Content-Type', value: 'application/xml' },
        ],
      },
      {
        source: '/manifest.json',
        headers: [
          { key: 'Cache-Control', value: 'public, max-age=86400' },
          { key: 'Content-Type', value: 'application/manifest+json' },
        ],
      },
      {
        source: '/_next/static/:path*',
        headers: [
          { key: 'Cache-Control', value: 'public, max-age=31536000, immutable' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
        ],
      },
    ];
    
    if (isDevelopment) {
      // In development, use a more permissive CSP without nonces
      return [
        ...staticFileHeaders,
        {
          source: '/:path*',
          headers: [
            {
              key: 'Content-Security-Policy',
              value: [
                "default-src 'self' http://localhost:* http://127.0.0.1:* ws://localhost:* ws://127.0.0.1:*",
                "script-src 'self' 'unsafe-eval' 'unsafe-inline' blob: http://localhost:* http://127.0.0.1:* https://www.googletagmanager.com https://tagmanager.google.com https://www.clarity.ms https://scripts.clarity.ms https://*.clarity.ms",
                "worker-src 'self' blob:",
                "style-src 'self' 'unsafe-inline' http://localhost:* http://127.0.0.1:*",
                "img-src 'self' data: blob: http://localhost:* http://127.0.0.1:* https://www.googletagmanager.com https://*.clarity.ms https://c.bing.com",
                "connect-src 'self' http://localhost:* http://127.0.0.1:* ws://localhost:* ws://127.0.0.1:* wss://localhost:* wss://127.0.0.1:* https://www.google-analytics.com https://analytics.google.com https://www.googletagmanager.com https://stats.g.doubleclick.net https://*.clarity.ms https://prodregistryv2.org https://*.ingest.sentry.io https://*.ingest.us.sentry.io https://featureassets.org https://cloudflare-dns.com",
                "font-src 'self' data: http://localhost:* http://127.0.0.1:*",
                "media-src 'self' http://localhost:* http://127.0.0.1:*",
                "frame-src 'self' http://localhost:* http://127.0.0.1:* https://www.googletagmanager.com"
              ].join('; ')
            }
          ]
        }
      ];
    }
    
    if (isStaging) {
      // Staging-specific security headers
      return [
        ...staticFileHeaders,
        {
          source: '/:path*',
          headers: [
            {
              key: 'Content-Security-Policy',
              value: [
                "default-src 'self' https://*.staging.netrasystems.ai",
                "script-src 'self' 'unsafe-inline' blob: https://*.staging.netrasystems.ai https://www.googletagmanager.com https://tagmanager.google.com https://www.clarity.ms https://scripts.clarity.ms https://*.clarity.ms",
                "worker-src 'self' blob:",
                "style-src 'self' 'unsafe-inline' https://*.staging.netrasystems.ai",
                "img-src 'self' data: blob: https://*.staging.netrasystems.ai https://www.googletagmanager.com https://*.clarity.ms https://c.bing.com",
                "connect-src 'self' https://*.staging.netrasystems.ai wss://*.staging.netrasystems.ai https://www.google-analytics.com https://analytics.google.com https://www.googletagmanager.com https://stats.g.doubleclick.net https://*.clarity.ms https://prodregistryv2.org https://*.ingest.sentry.io https://*.ingest.us.sentry.io https://featureassets.org https://cloudflare-dns.com",
                "font-src 'self' data: https://*.staging.netrasystems.ai",
                "media-src 'self' https://*.staging.netrasystems.ai",
                "frame-src 'self' https://*.staging.netrasystems.ai https://accounts.google.com https://www.googletagmanager.com"
              ].join('; ')
            },
            {
              key: 'X-Frame-Options',
              value: 'SAMEORIGIN'
            },
            {
              key: 'X-Content-Type-Options', 
              value: 'nosniff'
            },
            {
              key: 'Referrer-Policy',
              value: 'strict-origin-when-cross-origin'
            }
          ]
        }
      ];
    }
    
    // For production, return static file headers - CSP will be handled by middleware with proper nonce support
    return staticFileHeaders;
  },
  async rewrites() {
    // Only use proxy rewrites in development
    // In production, the frontend should call backend services directly using their public URLs
    if (process.env.NODE_ENV === 'development') {
      // Use API_URL for server-side proxying (works in Docker)
      // Falls back to NEXT_PUBLIC_API_URL for client-side compatibility
      const backendUrl = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
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
    }
    // No rewrites in production - frontend calls services directly
    return [];
  },
  outputFileTracingIncludes: {
    '/api': ['./node_modules/**/*.js'],
    '/_next': ['./node_modules/**/*.js']
  },
  images: {
    domains: ['localhost', 'staging.netrasystems.ai']
  },
  webpack: (config, { isServer, isProduction, dev }) => {
    // Configure hot reload polling interval for development
    if (dev && !isProduction) {
      config.watchOptions = {
        ...config.watchOptions,
        // Poll for changes every 2 seconds in Docker environment, 10 seconds otherwise
        poll: process.env.DOCKER_ENV ? 2000 : 10000,
        // Aggregate changes for 300ms before rebuilding
        aggregateTimeout: 300,
        // Ignore node_modules to reduce file watching overhead
        ignored: /node_modules/,
      };
    }
    
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

module.exports = nextConfig;
