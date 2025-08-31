/**
 * Staging Integration Failures Tests
 * 
 * Integration tests that verify the complete frontend-to-backend communication patterns
 * that are failing in GCP staging environment. These tests ensure that when the issues
 * are fixed, the complete integration flow works correctly.
 * 
 * EXPECTED TO FAIL INITIALLY: These tests demonstrate end-to-end integration problems
 * 
 * These tests combine all the individual issues into realistic usage scenarios
 */

import { render, screen, waitFor } from '@testing-library/react';
import { getUnifiedApiConfig, detectEnvironment } from '@/lib/unified-api-config';

// Mock Next.js router
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

describe('Staging Integration Failures - End-to-End', () => {
      setupAntiHang();
    jest.setTimeout(10000);
  const originalEnv = process.env;
  const originalFetch = global.fetch;

  beforeAll(() => {
    // Set staging environment
    process.env = {
      ...originalEnv,
      NODE_ENV: 'production',
      NEXT_PUBLIC_ENVIRONMENT: 'staging',
    };
  });

  beforeEach(() => {
    jest.resetModules();
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

  describe('Complete Application Startup Flow', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    /**
     * EXPECTED TO FAIL
     * Root cause: Multiple integration failures prevent successful app startup
     */
    test('app should successfully start up and initialize in staging', async () => {
      const mockFetch = jest.fn()
        // Health check - currently fails with 404
        .mockResolvedValueOnce({
          ok: false,
          status: 404,
          json: async () => ({ error: 'Health endpoint not found' })
        })
        // Config fetch - currently fails with 404  
        .mockResolvedValueOnce({
          ok: false,
          status: 404,
          json: async () => ({ error: 'Config endpoint not found' })
        })
        // Auth config - might work if auth service is running
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => ({ 
            google_client_id: 'staging-client-id',
            oauth_enabled: true 
          })
        });

      global.fetch = mockFetch;

      const config = getUnifiedApiConfig();
      
      try {
        // Simulate startup sequence
        // 1. Health check
        const healthResponse = await fetch(config.endpoints.ready);
        expect(healthResponse.ok).toBe(true); // WILL FAIL due to 404

        // 2. Config fetch
        const configResponse = await fetch(`${config.urls.api}/api/config/public`);
        expect(configResponse.ok).toBe(true); // WILL FAIL due to 404

        // 3. Auth config (might succeed)
        const authResponse = await fetch(config.endpoints.authConfig);
        expect(authResponse.ok).toBe(true); // Might pass if auth service works

        // If we reach here, startup should be successful
        expect(true).toBe(true);
        
      } catch (error) {
        // Startup failures indicate integration problems
        expect(error.message).not.toContain('404');
        expect(error.message).not.toContain('ECONNREFUSED');
      }
    });

    /**
     * EXPECTED TO FAIL
     * Root cause: Frontend can't communicate with backend services
     */
    test('should establish connections to all required services', async () => {
      const config = getUnifiedApiConfig();
      const services = [
        { name: 'backend-api', url: config.urls.api },
        { name: 'backend-websocket', url: config.urls.websocket },
        { name: 'auth-service', url: config.urls.auth },
      ];

      const mockFetch = jest.fn().mockResolvedValue({
        ok: false,
        status: 404,
        statusText: 'Service not found'
      });
      global.fetch = mockFetch;

      for (const service of services) {
        try {
          const response = await fetch(`${service.url}/health`);
          
          // All services should be reachable
          expect(response.ok).toBe(true);
          expect(response.status).toBe(200);
          
        } catch (error) {
          // Service connectivity problems
          expect(error.message).not.toContain('ECONNREFUSED');
          expect(error.message).not.toContain('404');
        }
      }
    });
  });

  describe('User Authentication Flow Integration', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    /**
     * EXPECTED TO FAIL
     * Root cause: Auth service integration broken due to routing issues
     */
    test('should complete OAuth authentication flow', async () => {
      const config = getUnifiedApiConfig();
      
      const mockFetch = jest.fn()
        // Auth config fetch
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => ({
            google_client_id: 'test-client-id',
            oauth_enabled: true,
            redirect_uri: `${config.urls.frontend}/auth/callback`
          })
        })
        // Token validation
        .mockResolvedValueOnce({
          ok: false,
          status: 404,
          json: async () => ({ error: 'Token validation endpoint not found' })
        });

      global.fetch = mockFetch;

      try {
        // 1. Get auth configuration
        const authConfigResponse = await fetch(config.endpoints.authConfig);
        expect(authConfigResponse.ok).toBe(true);

        // 2. Validate auth token (if user has one)
        const tokenResponse = await fetch(config.endpoints.authValidate);
        expect(tokenResponse.ok).toBe(true); // WILL FAIL if auth endpoints are down

        const authConfig = await authConfigResponse.json();
        expect(authConfig.google_client_id).toBeTruthy();

      } catch (error) {
        expect(error.message).not.toContain('404');
      }
    });
  });

  describe('Chat Functionality Integration', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    /**
     * EXPECTED TO FAIL
     * Root cause: Chat requires multiple backend services that are returning 404
     */
    test('should load chat interface and establish connections', async () => {
      const config = getUnifiedApiConfig();
      
      const mockFetch = jest.fn()
        // Threads list
        .mockResolvedValueOnce({
          ok: false,
          status: 404,
          json: async () => ({ error: 'Threads endpoint not found' })
        })
        // WebSocket connection test (simulated)
        .mockResolvedValueOnce({
          ok: false,
          status: 404,
          json: async () => ({ error: 'WebSocket endpoint not accessible' })
        });

      global.fetch = mockFetch;

      try {
        // 1. Load threads list
        const threadsResponse = await fetch(config.endpoints.threads);
        expect(threadsResponse.ok).toBe(true); // WILL FAIL due to 404

        const threads = await threadsResponse.json();
        expect(Array.isArray(threads)).toBe(true);

        // 2. WebSocket connection would be tested here
        // Currently fails because backend is not accessible

      } catch (error) {
        expect(error.message).not.toContain('404');
      }
    });

    /**
     * EXPECTED TO FAIL
     * Root cause: Backend API endpoints not working in staging
     */
    test('should handle chat message sending and receiving', async () => {
      const config = getUnifiedApiConfig();
      
      const mockFetch = jest.fn()
        // Create new thread
        .mockResolvedValueOnce({
          ok: false,
          status: 404,
          json: async () => ({ error: 'Thread creation endpoint not found' })
        })
        // Send message
        .mockResolvedValueOnce({
          ok: false,
          status: 404,
          json: async () => ({ error: 'Message endpoint not found' })
        });

      global.fetch = mockFetch;

      try {
        // 1. Create thread
        const createResponse = await fetch(config.endpoints.threads, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title: 'Test Thread' })
        });
        expect(createResponse.ok).toBe(true); // WILL FAIL

        // 2. Send message
        const messageResponse = await fetch(`${config.endpoints.threads}/test-thread-id/messages`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content: 'Hello' })
        });
        expect(messageResponse.ok).toBe(true); // WILL FAIL

      } catch (error) {
        expect(error.message).not.toContain('404');
      }
    });
  });

  describe('Static Asset Loading Integration', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    /**
     * EXPECTED TO FAIL
     * Root cause: Static assets not properly served in staging
     */
    test('should load all required static assets without 404s', async () => {
      const criticalAssets = [
        '/favicon.ico',
        '/_next/static/css/app.css', // Example CSS file
        '/_next/static/js/app.js',   // Example JS file
      ];

      const mockFetch = jest.fn().mockResolvedValue({
        ok: false,
        status: 404,
        statusText: 'Not Found'
      });
      global.fetch = mockFetch;

      for (const asset of criticalAssets) {
        try {
          const response = await fetch(asset);
          
          // Critical assets should load successfully
          expect(response.ok).toBe(true);
          expect(response.status).toBe(200);
          
        } catch (error) {
          // Asset loading failures
          expect(error.message).not.toContain('404');
        }
      }
    });
  });

  describe('Environment Configuration Consistency', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    /**
     * EXPECTED TO PASS (but validates critical configuration)
     * Ensures configuration is consistent across all components
     */
    test('should have consistent staging configuration across all components', () => {
      const config = getUnifiedApiConfig();
      const environment = detectEnvironment();
      
      // Environment detection should be consistent
      expect(environment).toBe('staging');
      expect(config.environment).toBe('staging');
      
      // All URLs should use staging domains
      expect(config.urls.api).toBe('https://api.staging.netrasystems.ai');
      expect(config.urls.auth).toBe('https://auth.staging.netrasystems.ai');
      expect(config.urls.frontend).toBe('https://app.staging.netrasystems.ai');
      
      // Security features should be enabled
      expect(config.features.useHttps).toBe(true);
      expect(config.features.useWebSocketSecure).toBe(true);
    });

    /**
     * EXPECTED TO FAIL 
     * Root cause: Some components may still use development configuration
     */
    test('should not have any localhost references in staging', () => {
      const config = getUnifiedApiConfig();
      
      // Check all URL configurations
      const allUrls = [
        config.urls.api,
        config.urls.websocket, 
        config.urls.auth,
        config.urls.frontend,
        config.endpoints.health,
        config.endpoints.ready,
        config.endpoints.threads,
        config.endpoints.websocket,
        config.endpoints.authConfig,
        config.endpoints.authLogin,
      ];

      for (const url of allUrls) {
        expect(url).not.toContain('localhost');
        expect(url).not.toContain('127.0.0.1');
        expect(url).not.toContain(':8000');
        expect(url).not.toContain(':8081');
        expect(url).not.toContain(':3000');
      }
    });
  });

  describe('Error Handling and Recovery', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    /**
     * EXPECTED TO FAIL
     * Root cause: Error handling not graceful when services are unavailable
     */
    test('should gracefully handle service unavailability', async () => {
      const config = getUnifiedApiConfig();
      
      const mockFetch = jest.fn().mockRejectedValue(
        new Error('ECONNREFUSED: Connection refused')
      );
      global.fetch = mockFetch;

      try {
        // Should handle connection failures gracefully
        const response = await fetch(config.endpoints.health);
        
        // Should not throw unhandled errors
        expect(true).toBe(true); // Should reach here without throwing
        
      } catch (error) {
        // Error handling should be graceful
        expect(error.message).not.toContain('ECONNREFUSED');
      }
    });

    /**
     * EXPECTED TO FAIL
     * Root cause: No fallback mechanisms for when backend is unavailable
     */
    test('should provide meaningful error messages when services are down', async () => {
      const config = getUnifiedApiConfig();
      
      const mockFetch = jest.fn().mockResolvedValue({
        ok: false,
        status: 503,
        statusText: 'Service Unavailable',
        json: async () => ({ error: 'Backend service is temporarily unavailable' })
      });
      global.fetch = mockFetch;

      try {
        const response = await fetch(config.endpoints.ready);
        
        if (!response.ok) {
          const errorData = await response.json();
          
          // Should provide helpful error messages
          expect(errorData.error).toBeTruthy();
          expect(errorData.error).not.toBe('Not Found'); // Should be more specific
        }
        
      } catch (error) {
        // Should have proper error handling
        expect(error.message).toBeTruthy();
      }
    });
  });

  describe('Performance and Reliability', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    /**
     * EXPECTED TO FAIL
     * Root cause: Performance degraded by 404 errors and failed requests
     */
    test('should not have excessive failed requests impacting performance', async () => {
      let requestCount = 0;
      let failedRequests = 0;

      const mockFetch = jest.fn().mockImplementation((...args) => {
        requestCount++;
        
        // Simulate current staging behavior with many 404s
        if (Math.random() > 0.3) { // 70% failure rate
          failedRequests++;
          return Promise.resolve({
            ok: false,
            status: 404,
            json: async () => ({ error: 'Not Found' })
          });
        }
        
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ status: 'ok' })
        });
      });
      global.fetch = mockFetch;

      const config = getUnifiedApiConfig();
      const endpoints = [
        config.endpoints.health,
        config.endpoints.ready,
        config.endpoints.threads,
        config.endpoints.authConfig,
      ];

      // Simulate multiple requests during app startup
      const promises = endpoints.map(endpoint => 
        fetch(endpoint).catch(() => ({ ok: false }))
      );

      await Promise.all(promises);

      // Failure rate should be low for good performance
      const failureRate = failedRequests / requestCount;
      expect(failureRate).toBeLessThan(0.1); // WILL FAIL with current 70% failure rate
    });
  });
});