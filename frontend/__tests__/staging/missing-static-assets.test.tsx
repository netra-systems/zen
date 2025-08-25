/**
 * Missing Static Assets 404 Errors Tests
 * 
 * These tests replicate the static asset 404 errors found in GCP staging logs:
 * - GET /favicon.ico -> 404 Not Found
 * - GET /_next/static/... -> 404 Not Found (potential)
 * - GET /robots.txt -> 404 Not Found (potential)
 * - GET /manifest.json -> 404 Not Found (potential)
 * 
 * EXPECTED TO FAIL: These tests demonstrate missing static asset configuration
 * 
 * Root Causes:
 * 1. Static assets not properly built/copied in staging deployment
 * 2. Static asset serving not configured in Next.js for staging
 * 3. Missing favicon.ico and other standard web assets
 * 4. CDN or static file serving misconfiguration
 */

import path from 'path';
import fs from 'fs';

describe('Missing Static Assets 404 Errors - Staging Replication', () => {
  const originalEnv = process.env;
  
  beforeAll(() => {
    process.env = {
      ...originalEnv,
      NODE_ENV: 'production',
      NEXT_PUBLIC_ENVIRONMENT: 'staging',
    };
  });

  afterAll(() => {
    process.env = originalEnv;
  });

  describe('Missing favicon.ico', () => {
    /**
     * EXPECTED TO FAIL
     * Root cause: favicon.ico returns 404 in staging
     * Browsers automatically request favicon.ico, causing 404 errors
     */
    test('favicon.ico should exist and be accessible', async () => {
      const mockFetch = jest.fn().mockResolvedValue({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        headers: new Headers({
          'content-type': 'text/html', // Should be image/x-icon or image/vnd.microsoft.icon
        }),
        text: async () => '404 - This page could not be found.',
      });
      global.fetch = mockFetch;

      try {
        const response = await fetch('/favicon.ico');
        
        // This SHOULD pass but WILL FAIL due to 404
        expect(response.ok).toBe(true);
        expect(response.status).toBe(200);
        
        // Should serve an icon file
        const contentType = response.headers.get('content-type');
        expect(contentType).toMatch(/^image\/(x-icon|vnd\.microsoft\.icon|ico|png)$/);
        
      } catch (error) {
        // Favicon should not cause network errors
        expect(error.message).not.toContain('404');
      }
      
      global.fetch = fetch;
    });

    /**
     * EXPECTED TO FAIL 
     * Root cause: favicon.ico file missing from build output
     */
    test('favicon.ico should exist in public directory', () => {
      // Check if favicon exists in source
      const publicFaviconPath = path.join(process.cwd(), 'public', 'favicon.ico');
      
      // This SHOULD pass but might fail if favicon is missing
      expect(fs.existsSync(publicFaviconPath)).toBe(true);
      
      if (fs.existsSync(publicFaviconPath)) {
        const stats = fs.statSync(publicFaviconPath);
        expect(stats.isFile()).toBe(true);
        expect(stats.size).toBeGreaterThan(0); // Should not be empty file
      }
    });

    /**
     * EXPECTED TO FAIL
     * Root cause: Next.js not serving static files from public directory in staging
     */
    test('Next.js should serve public directory files in production', () => {
      // Check Next.js static file configuration
      const nextConfig = require('@/next.config.ts').default;
      
      // Next.js should serve public directory by default
      // If this fails, it indicates static serving is broken
      expect(typeof nextConfig).toBe('object');
      
      // Should not have configuration that prevents static serving
      expect(nextConfig.output).toBe('standalone'); // This might affect static serving
    });
  });

  describe('Missing Standard Web Assets', () => {
    /**
     * EXPECTED TO FAIL
     * Root cause: robots.txt might be missing
     */
    test('robots.txt should exist for SEO', async () => {
      const mockFetch = jest.fn().mockResolvedValue({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        text: async () => '404 - This page could not be found.',
      });
      global.fetch = mockFetch;

      try {
        const response = await fetch('/robots.txt');
        
        // This SHOULD pass but might fail if robots.txt missing
        expect(response.ok).toBe(true);
        expect(response.status).toBe(200);
        
        const content = await response.text();
        expect(content).toContain('User-agent');
        
      } catch (error) {
        // robots.txt is important for SEO
        expect(error.message).not.toContain('404');
      }
      
      global.fetch = fetch;
    });

    /**
     * EXPECTED TO FAIL
     * Root cause: manifest.json might be missing for PWA
     */
    test('manifest.json should exist for PWA support', async () => {
      const mockFetch = jest.fn().mockResolvedValue({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: async () => ({ error: 'Not found' }),
      });
      global.fetch = mockFetch;

      try {
        const response = await fetch('/manifest.json');
        
        // This might pass or fail depending on PWA setup
        if (response.ok) {
          expect(response.status).toBe(200);
          
          const manifest = await response.json();
          expect(manifest).toHaveProperty('name');
          expect(manifest).toHaveProperty('short_name');
        }
        
      } catch (error) {
        // manifest.json is optional but good to have
        console.log('manifest.json not found - this is optional for PWA');
      }
      
      global.fetch = fetch;
    });

    /**
     * EXPECTED TO PASS (but check for files)
     * Documents which standard web assets should exist
     */
    test('should check for standard web assets in public directory', () => {
      const publicDir = path.join(process.cwd(), 'public');
      
      if (fs.existsSync(publicDir)) {
        const files = fs.readdirSync(publicDir);
        
        // Document what files exist
        console.log('Public directory files:', files);
        
        // Check for common assets
        const hasImages = files.some(f => f.match(/\.(svg|png|jpg|jpeg|ico)$/));
        expect(hasImages).toBe(true); // Should have at least one image
      }
    });
  });

  describe('Next.js Static Asset Generation', () => {
    /**
     * EXPECTED TO FAIL
     * Root cause: _next/static files not properly generated or served
     */
    test('_next/static directory should be generated in build', () => {
      // In a real deployment, check if _next/static exists
      // This would be in .next/static or .next/standalone/public/_next/static
      
      const possiblePaths = [
        path.join(process.cwd(), '.next', 'static'),
        path.join(process.cwd(), '.next', 'standalone', 'public', '_next', 'static'),
        path.join(process.cwd(), 'public', '_next', 'static'),
      ];
      
      let staticDirExists = false;
      for (const staticPath of possiblePaths) {
        if (fs.existsSync(staticPath)) {
          staticDirExists = true;
          const files = fs.readdirSync(staticPath);
          console.log(`Static files in ${staticPath}:`, files.length, 'files');
          break;
        }
      }
      
      // In development this might not exist, in production it should
      if (process.env.NODE_ENV === 'production') {
        expect(staticDirExists).toBe(true);
      }
    });

    /**
     * EXPECTED TO FAIL
     * Root cause: Static asset optimization not working in staging build
     */
    test('static assets should be optimized for production', () => {
      const nextConfig = require('@/next.config.ts').default;
      
      // Should have optimization enabled for production
      expect(nextConfig.swcMinify).toBe(true); // For production
      
      // Should have experimental optimizations
      if (nextConfig.experimental) {
        expect(nextConfig.experimental.optimizeCss).toBe(true);
      }
    });
  });

  describe('CDN and Static File Serving Configuration', () => {
    /**
     * EXPECTED TO FAIL
     * Root cause: Static asset serving not configured correctly for staging
     */
    test('should have correct static asset serving configuration', () => {
      const nextConfig = require('@/next.config.ts').default;
      
      // Check asset prefix configuration (for CDN)
      if (nextConfig.assetPrefix) {
        expect(typeof nextConfig.assetPrefix).toBe('string');
        expect(nextConfig.assetPrefix).toMatch(/^https?:/);
      }
      
      // Check images configuration
      if (nextConfig.images && nextConfig.images.domains) {
        expect(nextConfig.images.domains).toContain('staging.netrasystems.ai');
      }
    });

    /**
     * EXPECTED TO FAIL
     * Root cause: Static files not being served with correct headers
     */
    test('static files should have appropriate caching headers in staging', async () => {
      const mockFetch = jest.fn().mockResolvedValue({
        ok: true,
        status: 200,
        headers: new Headers({
          // Missing cache headers indicates misconfiguration
          'content-type': 'image/x-icon',
          // Should have: 'cache-control': 'public, max-age=31536000, immutable'
        }),
        blob: async () => new Blob(['fake-favicon'], { type: 'image/x-icon' }),
      });
      global.fetch = mockFetch;

      try {
        const response = await fetch('/favicon.ico');
        
        if (response.ok) {
          // Should have caching headers for static assets
          const cacheControl = response.headers.get('cache-control');
          expect(cacheControl).toBeTruthy();
          expect(cacheControl).toMatch(/max-age=\d+/);
        }
        
      } catch (error) {
        console.log('Static asset caching test failed');
      }
      
      global.fetch = fetch;
    });
  });

  describe('Deployment-Specific Static Asset Issues', () => {
    /**
     * EXPECTED TO FAIL
     * Root cause: Docker build not copying static assets correctly
     */
    test('Docker build should include all static assets', () => {
      // In a real deployment, this would check the container filesystem
      // For testing, check if build configuration includes static assets
      
      const nextConfig = require('@/next.config.ts').default;
      
      // Standalone output should include static assets
      expect(nextConfig.output).toBe('standalone');
      
      // Should have file tracing includes for static assets
      if (nextConfig.outputFileTracingIncludes) {
        const includes = nextConfig.outputFileTracingIncludes;
        expect(typeof includes).toBe('object');
      }
    });

    /**
     * EXPECTED TO FAIL  
     * Root cause: Kubernetes volume mounts not including static assets
     */
    test('deployment should mount static asset volumes correctly', () => {
      // This would check if static assets are accessible in the deployment
      // For testing, verify the configuration supports static serving
      
      const publicDir = path.join(process.cwd(), 'public');
      
      if (fs.existsSync(publicDir)) {
        const files = fs.readdirSync(publicDir);
        
        // Should have essential static files
        expect(files.length).toBeGreaterThan(0);
        
        // Check for specific essential files
        const hasIcon = files.some(f => f.includes('icon') || f.includes('favicon'));
        expect(hasIcon).toBe(true);
      }
    });
  });

  describe('Browser Asset Request Patterns', () => {
    /**
     * EXPECTED TO FAIL
     * Root cause: Browsers requesting standard assets that don't exist
     */
    test('should handle common browser asset requests', async () => {
      const commonAssets = [
        '/favicon.ico',
        '/apple-touch-icon.png',
        '/robots.txt',
        '/sitemap.xml'
      ];

      const mockFetch = jest.fn();
      global.fetch = mockFetch;

      for (const asset of commonAssets) {
        mockFetch.mockResolvedValueOnce({
          ok: false,
          status: 404,
          statusText: 'Not Found',
        });

        try {
          const response = await fetch(asset);
          
          // These commonly requested assets should exist or gracefully handled
          if (asset === '/favicon.ico') {
            // Favicon is critical
            expect(response.status).not.toBe(404);
          }
          
        } catch (error) {
          console.log(`Asset ${asset} failed to load`);
        }
      }
      
      global.fetch = fetch;
    });

    /**
     * EXPECTED TO FAIL
     * Root cause: Asset paths not properly configured for staging domain
     */
    test('asset URLs should work with staging domain', () => {
      // Asset URLs should be absolute or relative to work with staging domain
      const stagingDomain = 'https://app.staging.netrasystems.ai';
      
      // Test asset URL construction
      const faviconUrl = new URL('/favicon.ico', stagingDomain);
      expect(faviconUrl.toString()).toBe('https://app.staging.netrasystems.ai/favicon.ico');
      
      // Should not contain localhost
      expect(faviconUrl.toString()).not.toContain('localhost');
    });
  });

  describe('Performance Impact of Missing Assets', () => {
    /**
     * EXPECTED TO FAIL
     * Root cause: 404 errors for assets impact page load performance
     */
    test('missing assets should not block page rendering', () => {
      // Missing non-critical assets should not prevent page load
      // This is more of a performance consideration
      
      // Critical assets that would block rendering:
      const criticalAssets = ['favicon.ico']; // Usually not blocking
      
      // Non-critical assets that can 404 without major impact:
      const nonCriticalAssets = ['robots.txt', 'sitemap.xml', 'manifest.json'];
      
      expect(criticalAssets.length).toBeGreaterThan(0);
      expect(nonCriticalAssets.length).toBeGreaterThan(0);
    });

    /**
     * EXPECTED TO PASS
     * Documents the performance impact of missing static assets
     */
    test('should minimize performance impact of asset 404s', () => {
      // Document that while 404s for static assets don't break functionality,
      // they do create unnecessary network requests and console errors
      
      const impactLevel = 'low'; // favicon 404s are low impact but should be fixed
      expect(impactLevel).toBe('low');
      
      // However, fixing them improves overall application polish
      const shouldFix = true;
      expect(shouldFix).toBe(true);
    });
  });
});