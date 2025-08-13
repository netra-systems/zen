import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  productionBrowserSourceMaps: true,
  output: 'standalone',
  outputFileTracingIncludes: {
    '/api': ['./node_modules/**/*.js'],
    '/_next': ['./node_modules/**/*.js']
  },
  images: {
    domains: ['localhost', 'staging.netrasystems.ai']
  },
  // Turbopack doesn't use webpack config, so we omit it
  experimental: {
    // Enable any turbopack-specific optimizations here
    turbo: {
      rules: {
        // Add any turbopack-specific rules if needed
      }
    }
  }
};

export default nextConfig;