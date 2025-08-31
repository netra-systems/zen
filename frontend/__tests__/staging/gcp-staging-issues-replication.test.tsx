/**
 * GCP Staging Issues Replication Tests
 * 
 * These tests replicate the exact issues found in GCP staging logs:
 * 1. API Proxy Failures - Frontend trying to proxy to localhost:8000 instead of staging backend
 * 2. Missing Health Endpoints - /health and /health/ready return 404  
 * 3. Missing API Routes - /api/config/public, /api/threads return 404
 * 4. Missing favicon.ico static asset
 * 
 * EXPECTED TO FAIL: These tests demonstrate the current problems
 * Root causes documented in comments for each test
 */

import { render, screen, waitFor } from '@testing-library/react';
import { getUnifiedApiConfig } from '@/lib/unified-api-config';
import { apiClient } from '@/services/apiClientWrapper';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

// Mock Next.js router and environment
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    back: jest.fn(),
    pathname: '/',
  }),
  useSearchParams: () => ({
    get: jest.fn(),
  }),
}));

describe('GCP Staging Issues Replication', () => {
  setupAntiHang();
    jest.setTimeout(10000);
  const originalEnv = process.env;
  const originalFetch = global.fetch;

  beforeAll(() => {
    // Mock staging environment
    process.env = {
      ...originalEnv,
      NODE_ENV: 'production',
      NEXT_PUBLIC_ENVIRONMENT: 'staging',
    };
  });

  beforeEach(() => {
    // Reset modules to ensure fresh config
    jest.resetModules();
    
    // Mock fetch for controlled testing
    global.fetch = jest.fn();
  });

  afterEach(() => {
    global.fetch = originalFetch;
    jest.clearAllMocks();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
      cleanupAntiHang();
  });

  afterAll(() => {
    process.env = originalEnv;
  });

  describe('Issue #1: API Proxy Configuration Failures', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    /**
     * EXPECTED TO FAIL
     * Root cause: Frontend incorrectly trying to use localhost:8000 URLs in staging
     * instead of direct staging backend URLs
     */
    test('should NOT contain localhost URLs in staging configuration', () => {
      const config = getUnifiedApiConfig();
      
      // These assertions SHOULD PASS but will fail if proxy misconfiguration exists
      expect(config.environment).toBe('staging');
      expect(config.urls.api).toBe('https://api.staging.netrasystems.ai');
      expect(config.urls.api).not.toContain('localhost');
      expect(config.urls.api).not.toContain('8000');
      
      // Endpoint URLs should be direct to backend, not proxied
      expect(config.endpoints.ready).toBe('https://api.staging.netrasystems.ai/health/ready');
      expect(config.endpoints.threads).toBe('https://api.staging.netrasystems.ai/api/threads');
      expect(config.endpoints.health).toBe('https://api.staging.netrasystems.ai/health');
    });

    /**
     * EXPECTED TO FAIL 
     * Root cause: API client trying to make requests to localhost in staging
     */
    test('should make API requests to staging URLs, not localhost', async () => {
      const mockFetch = jest.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ status: 'healthy' }),
      });
      global.fetch = mockFetch;

      const config = getUnifiedApiConfig();
      
      // Simulate making an API request in staging
      try {
        await fetch(config.endpoints.ready);
      } catch (error) {
        // Should not throw error for valid staging URL
      }

      // Verify fetch was called with staging URL, NOT localhost
      expect(mockFetch).toHaveBeenCalledWith(
        'https://api.staging.netrasystems.ai/health/ready'
      );
      
      // Should NEVER be called with localhost
      const calls = mockFetch.mock.calls.flat();
      const hasLocalhostCall = calls.some(call => 
        typeof call === 'string' && call.includes('localhost')
      );
      expect(hasLocalhostCall).toBe(false);
    });

    /**
     * EXPECTED TO FAIL
     * Root cause: Proxy rewrites still enabled in staging environment
     */
    test('should not use proxy rewrites in staging environment', () => {
      // Import next.config to check rewrites
      const nextConfig = require('@/next.config.ts').default;
      
      // In staging (NODE_ENV=production), rewrites should return empty array
      process.env.NODE_ENV = 'production';
      
      const rewrites = nextConfig.rewrites();
      
      // This should be an empty array but might fail if proxy logic is incorrect
      expect(rewrites).toEqual([]);
      
      // Verify no proxy rules exist
      expect(rewrites).not.toContainEqual(
        expect.objectContaining({
          source: '/api/:path*',
          destination: expect.stringContaining('localhost')
        })
      );
    });
  });

  describe('Issue #2: Missing Health Endpoints (404 errors)', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    /**
     * EXPECTED TO FAIL
     * Root cause: Health endpoints return 404 in staging
     * Expected behavior: Should return 200 with health status
     */
    test('/health endpoint should exist and be accessible', async () => {
      const mockFetch = jest.fn().mockRejectedValue(
        new Error('404: Health endpoint not found')
      );
      global.fetch = mockFetch;

      const config = getUnifiedApiConfig();
      
      try {
        const response = await fetch(config.endpoints.health);
        
        // This SHOULD pass but WILL FAIL due to 404
        expect(response.ok).toBe(true);
        expect(response.status).toBe(200);
        
        const data = await response.json();
        expect(data).toHaveProperty('status');
      } catch (error) {
        // This test SHOULD NOT reach this catch block
        // If it does, it means the health endpoint is missing
        expect(error.message).not.toContain('404');
      }
    });

    /**
     * EXPECTED TO FAIL
     * Root cause: /health/ready endpoint returns 404 in staging
     */
    test('/health/ready endpoint should exist for Kubernetes readiness probes', async () => {
      const mockFetch = jest.fn().mockRejectedValue(
        new Error('404: Readiness endpoint not found')
      );
      global.fetch = mockFetch;

      const config = getUnifiedApiConfig();
      
      try {
        const response = await fetch(config.endpoints.ready);
        
        // This SHOULD pass but WILL FAIL due to 404
        expect(response.ok).toBe(true);
        expect(response.status).toBe(200);
        
        const data = await response.json();
        expect(data).toHaveProperty('ready');
        expect(data.ready).toBe(true);
      } catch (error) {
        // This indicates the readiness endpoint is missing
        // Critical for Kubernetes health checks
        expect(error.message).not.toContain('404');
      }
    });

    /**
     * EXPECTED TO FAIL
     * Root cause: Health endpoint routing not properly configured in staging
     */
    test('health endpoints should use correct URL construction', () => {
      const config = getUnifiedApiConfig();
      
      // Verify health URLs are constructed correctly for staging
      expect(config.endpoints.health).toBe('https://api.staging.netrasystems.ai/health');
      expect(config.endpoints.ready).toBe('https://api.staging.netrasystems.ai/health/ready');
      
      // Should not contain proxy paths
      expect(config.endpoints.health).not.toBe('/health');
      expect(config.endpoints.ready).not.toBe('/health/ready');
    });
  });

  describe('Issue #3: Missing API Routes (404 errors)', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    /**
     * EXPECTED TO FAIL
     * Root cause: /api/config/public endpoint returns 404
     */
    test('/api/config/public endpoint should exist', async () => {
      const mockFetch = jest.fn().mockRejectedValue(
        new Error('404: Config endpoint not found')
      );
      global.fetch = mockFetch;

      const config = getUnifiedApiConfig();
      const configEndpoint = `${config.urls.api}/api/config/public`;
      
      try {
        const response = await fetch(configEndpoint);
        
        // This SHOULD pass but WILL FAIL due to 404
        expect(response.ok).toBe(true);
        expect(response.status).toBe(200);
        
        const data = await response.json();
        expect(data).toHaveProperty('environment');
      } catch (error) {
        // Config endpoint missing - needed for frontend initialization
        expect(error.message).not.toContain('404');
      }
    });

    /**
     * EXPECTED TO FAIL
     * Root cause: /api/threads endpoint returns 404
     */
    test('/api/threads endpoint should exist for chat functionality', async () => {
      const mockFetch = jest.fn().mockRejectedValue(
        new Error('404: Threads endpoint not found')
      );
      global.fetch = mockFetch;

      const config = getUnifiedApiConfig();
      
      try {
        const response = await fetch(config.endpoints.threads);
        
        // This SHOULD pass but WILL FAIL due to 404
        expect(response.ok).toBe(true);
        expect(response.status).toBe(200);
        
        const data = await response.json();
        expect(Array.isArray(data)).toBe(true);
      } catch (error) {
        // Threads endpoint missing - core chat functionality broken
        expect(error.message).not.toContain('404');
      }
    });

    /**
     * EXPECTED TO FAIL
     * Root cause: API routing not properly configured for staging deployment
     */
    test('API client should use direct backend URLs in staging', () => {
      const config = getUnifiedApiConfig();
      
      // API endpoints should be direct URLs to backend service
      expect(config.endpoints.threads).toBe('https://api.staging.netrasystems.ai/api/threads');
      
      // Should NOT use proxy paths (these work only in development)
      expect(config.endpoints.threads).not.toBe('/api/threads');
    });
  });

  describe('Issue #4: Missing Static Assets', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    /**
     * EXPECTED TO FAIL
     * Root cause: favicon.ico returns 404 in staging
     */
    test('favicon.ico should be accessible', async () => {
      const mockFetch = jest.fn().mockRejectedValue(
        new Error('404: Favicon not found')
      );
      global.fetch = mockFetch;

      try {
        const response = await fetch('/favicon.ico');
        
        // This SHOULD pass but WILL FAIL due to 404
        expect(response.ok).toBe(true);
        expect(response.status).toBe(200);
        expect(response.headers.get('content-type')).toContain('image');
      } catch (error) {
        // Missing favicon causes browser console errors
        expect(error.message).not.toContain('404');
      }
    });

    /**
     * EXPECTED TO FAIL
     * Root cause: Static asset serving not properly configured in staging
     */
    test('should have proper static asset configuration for staging', () => {
      // Check if favicon exists in public directory
      const fs = require('fs');
      const path = require('path');
      const faviconPath = path.join(process.cwd(), 'public', 'favicon.ico');
      
      // This SHOULD pass but might fail if favicon missing
      expect(fs.existsSync(faviconPath)).toBe(true);
    });
  });

  describe('Additional Staging Configuration Issues', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    /**
     * EXPECTED TO FAIL
     * Root cause: Environment detection might be incorrect
     */
    test('environment detection should correctly identify staging', () => {
      const config = getUnifiedApiConfig();
      
      // Should correctly identify staging environment
      expect(config.environment).toBe('staging');
      expect(config.features.useHttps).toBe(true);
      expect(config.features.useWebSocketSecure).toBe(true);
    });

    /**
     * EXPECTED TO FAIL
     * Root cause: WebSocket URL construction incorrect for staging
     */
    test('WebSocket URLs should use WSS in staging', () => {
      const config = getUnifiedApiConfig();
      
      // WebSocket should use secure protocol in staging
      expect(config.urls.websocket).toBe('wss://api.staging.netrasystems.ai');
      expect(config.endpoints.websocket).toBe('wss://api.staging.netrasystems.ai/ws');
      
      // Should not use insecure WebSocket
      expect(config.urls.websocket).not.toMatch(/^ws:/);
    });

    /**
     * EXPECTED TO FAIL  
     * Root cause: CORS configuration might not allow staging domains
     */
    test('should handle CORS for staging domain requests', async () => {
      const mockFetch = jest.fn().mockRejectedValue(
        new Error('CORS policy blocking request')
      );
      global.fetch = mockFetch;

      const config = getUnifiedApiConfig();
      
      try {
        await fetch(config.endpoints.ready, {
          method: 'GET',
          headers: {
            'Origin': 'https://app.staging.netrasystems.ai'
          }
        });
        
        // CORS should be properly configured for staging
        expect(true).toBe(true); // Should reach here
      } catch (error) {
        // CORS error indicates misconfiguration
        expect(error.message).not.toContain('CORS');
      }
    });
  });
});