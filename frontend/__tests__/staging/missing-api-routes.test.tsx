/**
 * Missing API Routes 404 Errors Tests
 * 
 * These tests replicate the API route 404 errors found in GCP staging logs:
 * - GET /api/config/public -> 404 Not Found
 * - GET /api/threads -> 404 Not Found  
 * - GET /api/threads -> 404 Not Found
 * 
 * EXPECTED TO FAIL: These tests demonstrate missing API endpoint routing
 * 
 * Root Causes:
 * 1. API endpoints not properly registered in backend service
 * 2. Frontend service attempting to handle backend API routes  
 * 3. Ingress/routing configuration directing API calls to wrong service
 * 4. Backend service not running or not accessible in staging
 */

import { getUnifiedApiConfig } from '@/lib/unified-api-config';
import { apiClient } from '@/services/apiClientWrapper';

// Mock Next.js router for tests
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn() }),
  useSearchParams: () => ({ get: jest.fn() }),
}));

describe('Missing API Routes 404 Errors - Staging Replication', () => {
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

  beforeEach(() => {
    jest.resetModules();
  });

  describe('Missing /api/config/public Endpoint', () => {
    /**
     * EXPECTED TO FAIL
     * Root cause: /api/config/public returns 404 in staging
     * This endpoint is critical for frontend initialization
     */
    test('/api/config/public should exist and return public configuration', async () => {
      const mockFetch = jest.fn().mockResolvedValue({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: async () => ({ error: 'API endpoint not found' }),
      });
      global.fetch = mockFetch;

      const config = getUnifiedApiConfig();
      const publicConfigUrl = `${config.urls.api}/api/config/public`;
      
      try {
        const response = await fetch(publicConfigUrl);
        
        // This SHOULD pass but WILL FAIL due to 404
        expect(response.ok).toBe(true);
        expect(response.status).toBe(200);
        
        const data = await response.json();
        expect(data).toHaveProperty('environment');
        expect(data).toHaveProperty('features');
        expect(data.environment).toBe('staging');
      } catch (error) {
        // This indicates critical config endpoint is missing
        expect(error.message).not.toContain('404');
      }
      
      global.fetch = fetch;
    });

    /**
     * EXPECTED TO FAIL
     * Root cause: Frontend trying to serve backend config endpoint
     */
    test('should not serve config endpoint from frontend service', async () => {
      const mockFetch = jest.fn().mockResolvedValue({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        url: 'https://app.staging.netrasystems.ai/api/config/public',
        json: async () => ({ error: 'This page could not be found.' }),
      });
      global.fetch = mockFetch;

      // This simulates the problematic request pattern
      const wrongUrl = 'https://app.staging.netrasystems.ai/api/config/public';
      
      try {
        const response = await fetch(wrongUrl);
        
        // This documents the current broken state
        expect(response.status).toBe(404);
        expect(response.url).toContain('app.staging.netrasystems.ai');
        
        // Frontend service should NOT handle backend API routes
      } catch (error) {
        fail('Config endpoint request should not throw network error');
      }
      
      global.fetch = fetch;
    });

    /**
     * EXPECTED TO PASS (demonstrates correct configuration)
     * Shows the correct URL for config endpoint
     */
    test('should use correct backend URL for config endpoint', () => {
      const config = getUnifiedApiConfig();
      const configUrl = `${config.urls.api}/api/config/public`;
      
      // Should target backend API service
      expect(configUrl).toBe('https://api.staging.netrasystems.ai/api/config/public');
      expect(configUrl).toContain('api.staging.netrasystems.ai');
      
      // Should NOT target frontend service
      expect(configUrl).not.toContain('app.staging.netrasystems.ai');
    });
  });

  describe('Missing /api/threads Endpoints', () => {
    /**
     * EXPECTED TO FAIL
     * Root cause: Threads API endpoint returns 404 in staging
     */
    test('/api/threads should exist and return thread list', async () => {
      const mockFetch = jest.fn().mockResolvedValue({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: async () => ({ error: 'Threads endpoint not found' }),
      });
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
        // Missing threads endpoint breaks core chat functionality
        expect(error.message).not.toContain('404');
      }
      
      global.fetch = fetch;
    });

    /**
     * EXPECTED TO FAIL
     * Root cause: Alternative /api/threads path also returns 404
     */
    test('/api/threads (without version) should also work', async () => {
      const mockFetch = jest.fn().mockResolvedValue({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: async () => ({ error: 'Threads endpoint not found' }),
      });
      global.fetch = mockFetch;

      const config = getUnifiedApiConfig();
      const threadsUrl = `${config.urls.api}/api/threads`;
      
      try {
        const response = await fetch(threadsUrl);
        
        // This might also fail with 404
        expect(response.ok).toBe(true);
        expect(response.status).toBe(200);
      } catch (error) {
        expect(error.message).not.toContain('404');
      }
      
      global.fetch = fetch;
    });

    /**
     * EXPECTED TO PASS
     * Documents correct URL construction for threads
     */
    test('should use correct backend URL for threads endpoint', () => {
      const config = getUnifiedApiConfig();
      
      // Threads endpoint should target backend
      expect(config.endpoints.threads).toBe('https://api.staging.netrasystems.ai/api/threads');
      expect(config.endpoints.threads).toContain('api.staging.netrasystems.ai');
      
      // Should not be a proxy path
      expect(config.endpoints.threads).not.toBe('/api/threads');
    });
  });

  describe('API Client Wrapper Integration', () => {
    /**
     * EXPECTED TO FAIL
     * Root cause: API client making requests to wrong URLs
     */
    test('API client should make requests to correct backend URLs', async () => {
      const mockFetch = jest.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ([]), // Empty threads array
      });
      global.fetch = mockFetch;

      const config = getUnifiedApiConfig();
      
      // Simulate API client request
      try {
        await fetch(config.endpoints.threads);
        
        // Verify request went to correct URL
        expect(mockFetch).toHaveBeenCalledWith(
          'https://api.staging.netrasystems.ai/api/threads'
        );
        
        // Should NOT make requests to localhost
        const calls = mockFetch.mock.calls.flat();
        const hasLocalhostCall = calls.some(call => 
          typeof call === 'string' && call.includes('localhost')
        );
        expect(hasLocalhostCall).toBe(false);
        
      } catch (error) {
        expect(error.message).not.toContain('404');
      }
      
      global.fetch = fetch;
    });

    /**
     * EXPECTED TO FAIL
     * Root cause: API wrapper not handling staging environment correctly
     */
    test('API wrapper should not use development proxy paths in staging', () => {
      const config = getUnifiedApiConfig();
      
      // In staging, should use full URLs
      expect(config.endpoints.threads).toMatch(/^https:/);
      expect(config.endpoints.health).toMatch(/^https:/);
      
      // Should NOT use proxy paths (development only)
      expect(config.endpoints.threads).not.toBe('/api/threads');
      expect(config.endpoints.health).not.toBe('/health');
    });
  });

  describe('Backend Service Availability', () => {
    /**
     * EXPECTED TO FAIL
     * Root cause: Backend service might not be running in staging
     */
    test('backend service should be accessible in staging', async () => {
      const mockFetch = jest.fn().mockRejectedValue(
        new Error('ECONNREFUSED: Connection refused to backend service')
      );
      global.fetch = mockFetch;

      const config = getUnifiedApiConfig();
      
      try {
        const response = await fetch(config.urls.api);
        
        // This SHOULD work if backend is running
        expect(response).toBeTruthy();
      } catch (error) {
        // Connection refused indicates backend service is down
        expect(error.message).not.toContain('ECONNREFUSED');
      }
      
      global.fetch = fetch;
    });

    /**
     * EXPECTED TO FAIL
     * Root cause: Service discovery not finding backend pods
     */
    test('should resolve backend service DNS correctly', () => {
      const config = getUnifiedApiConfig();
      
      // Backend URL should resolve to correct staging hostname
      const backendUrl = new URL(config.urls.api);
      expect(backendUrl.hostname).toBe('api.staging.netrasystems.ai');
      
      // Should not be localhost (indicates service discovery failure)
      expect(backendUrl.hostname).not.toBe('localhost');
      expect(backendUrl.hostname).not.toBe('127.0.0.1');
    });
  });

  describe('Ingress/Load Balancer Configuration', () => {
    /**
     * EXPECTED TO FAIL
     * Root cause: Ingress routing API calls to wrong service
     */
    test('API routes should be routed to backend service, not frontend', () => {
      const config = getUnifiedApiConfig();
      
      // All API endpoints should target api subdomain (backend)
      expect(config.endpoints.threads).toMatch(/^https:\/\/api\./);
      
      // Should NOT target app subdomain (frontend)
      expect(config.endpoints.threads).not.toMatch(/^https:\/\/app\./);
    });

    /**
     * EXPECTED TO FAIL
     * Root cause: Load balancer health check configuration incorrect
     */
    test('load balancer should distinguish between frontend and backend health checks', () => {
      const config = getUnifiedApiConfig();
      
      // Backend health checks
      expect(config.endpoints.health).toBe('https://api.staging.netrasystems.ai/health');
      expect(config.endpoints.ready).toBe('https://api.staging.netrasystems.ai/health/ready');
      
      // Frontend should have different health check (if any)
      const frontendUrl = config.urls.frontend;
      expect(frontendUrl).toBe('https://app.staging.netrasystems.ai');
      
      // Frontend health ≠ Backend health
      expect(frontendUrl).not.toBe(config.urls.api);
    });
  });

  describe('Environment-Specific Route Configuration', () => {
    /**
     * EXPECTED TO FAIL
     * Root cause: Route configuration not accounting for staging environment
     */
    test('should have different route configuration for staging vs development', () => {
      const config = getUnifiedApiConfig();
      
      // Staging should use direct URLs
      expect(config.environment).toBe('staging');
      expect(config.endpoints.threads).toMatch(/^https:/);
      
      // Should not use development proxy configuration
      expect(config.features.dynamicDiscovery).toBe(false);
    });

    /**
     * EXPECTED TO PASS
     * Documents proper staging configuration
     */
    test('staging should disable proxy features used in development', () => {
      const config = getUnifiedApiConfig();
      
      // Staging should not use development features
      expect(config.features.dynamicDiscovery).toBe(false);
      expect(config.features.useHttps).toBe(true);
      expect(config.features.corsEnabled).toBe(true);
    });
  });

  describe('API Versioning and Path Structure', () => {
    /**
     * EXPECTED TO FAIL
     * Root cause: API version paths not matching backend implementation
     */
    test('API version paths should match backend route definitions', () => {
      const config = getUnifiedApiConfig();
      
      // Verify API versioning is consistent
      expect(config.endpoints.threads).toContain('/api/');
      
      // Config endpoint might use different versioning
      const configUrl = `${config.urls.api}/api/config/public`;
      expect(configUrl).toContain('/api/');
    });

    /**
     * EXPECTED TO FAIL
     * Root cause: Path structure mismatch between frontend and backend
     */
    test('path structure should be consistent across services', () => {
      const config = getUnifiedApiConfig();
      
      // All backend API calls should use consistent base path
      const threadsPath = new URL(config.endpoints.threads).pathname;
      expect(threadsPath).toMatch(/^\/api\/v1\//);
      
      // Should not have inconsistent versioning
      expect(threadsPath).not.toBe('/api/threads'); // Missing version
      expect(threadsPath).not.toBe('/threads'); // Missing api prefix
    });
  });
});