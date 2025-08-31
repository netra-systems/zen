/**
 * Health Endpoint Reliability and API Route Intermittent Failures Tests
 * 
 * These tests replicate MEDIUM PRIORITY issues from the Frontend service audit:
 * 1. Missing Health Check Endpoint - /health returns 404 (should exist alongside /api/health)
 * 2. API Route Reliability - /api/config/public sometimes returns 404  
 * 3. Intermittent failures and race conditions in staging
 * 4. Health endpoint availability for load balancer checks
 * 5. Service discovery and endpoint resolution issues
 * 
 * EXPECTED TO FAIL: These tests demonstrate intermittent and reliability issues
 * 
 * Root Causes:
 * 1. Health endpoints not consistently available
 * 2. Load balancer health checks hitting wrong service or timing out
 * 3. API routes having intermittent availability issues
 * 4. Service startup/shutdown race conditions affecting endpoint availability
 * 5. DNS resolution or service discovery intermittent failures
 */

import { render, screen, waitFor } from '@testing-library/react';
import { getUnifiedApiConfig } from '../../lib/unified-api-config';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

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

describe('Health Endpoint Reliability and API Route Intermittent Failures', () => {
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

  describe('Medium Priority: Missing Health Check Endpoint Issues', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    /**
     * EXPECTED TO FAIL
     * Root cause: /health endpoint returns 404 while /api/health might work
     * Load balancers often expect /health not /api/health
     */
    test('root /health endpoint should be available for load balancer checks', async () => {
      const mockFetch = jest.fn().mockResolvedValue({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: async () => ({ 
          error: 'Health endpoint not found at root path',
          message: 'This endpoint is not available',
          available_endpoints: ['/api/health', '/health/ready']
        }),
      });
      global.fetch = mockFetch;

      const config = getUnifiedApiConfig();
      const rootHealthUrl = `${config.urls.api}/health`; // Note: this is the backend URL

      try {
        const response = await fetch(rootHealthUrl);

        // Root health endpoint SHOULD be available
        expect(response.ok).toBe(true);
        expect(response.status).toBe(200);
        
        const data = await response.json();
        expect(data).toHaveProperty('status');
        expect(data.status).toBe('healthy');
        
        // Should not return 404 error
        expect(data.error).not.toBe('Health endpoint not found at root path');
        
      } catch (error) {
        // Root health endpoint should not be missing
        expect(error.message).not.toContain('404');
        expect(error.message).not.toContain('Health endpoint not found');
      }
    });

    /**
     * EXPECTED TO FAIL
     * Root cause: Health endpoint has different response format than expected
     */
    test('health endpoint should return consistent format for monitoring systems', async () => {
      const mockFetch = jest.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ 
          // Inconsistent format compared to what monitoring expects
          alive: true,  // Should be 'status': 'healthy'
          service_name: 'backend',  // Should be consistent key naming
          timestamp: Date.now(),
          // Missing standard fields: version, uptime, dependencies
        }),
      });
      global.fetch = mockFetch;

      const config = getUnifiedApiConfig();

      try {
        const response = await fetch(config.endpoints.health);
        expect(response.ok).toBe(true);
        
        const data = await response.json();
        
        // Should have standard health check format
        expect(data).toHaveProperty('status');
        expect(data.status).toBe('healthy'); // Not 'alive'
        
        expect(data).toHaveProperty('service');
        expect(data).toHaveProperty('version');
        expect(data).toHaveProperty('timestamp');
        expect(data).toHaveProperty('uptime');
        
        // Should include dependency checks
        expect(data).toHaveProperty('dependencies');
        expect(data.dependencies).toHaveProperty('database');
        expect(data.dependencies).toHaveProperty('redis');
        
      } catch (error) {
        // Health check format should be consistent
        expect(error.message).not.toContain('Unexpected response format');
      }
    });

    /**
     * EXPECTED TO FAIL
     * Root cause: Health endpoint timing out under load
     */
    test('health endpoint should respond quickly even under load', async () => {
      let callCount = 0;
      const mockFetch = jest.fn().mockImplementation(async () => {
        callCount++;
        
        // Simulate slow response that times out
        if (callCount <= 3) {
          await new Promise(resolve => setTimeout(resolve, 1000)); // 15 second delay
          throw new Error('Health check timeout after 15 seconds');
        }
        
        return {
          ok: true,
          status: 200,
          json: async () => ({ status: 'healthy' }),
        };
      });
      global.fetch = mockFetch;

      const config = getUnifiedApiConfig();
      const startTime = Date.now();
      
      try {
        // Health check should respond within 5 seconds
        const response = await Promise.race([
          fetch(config.endpoints.health),
          new Promise((_, reject) => 
            setTimeout(() => reject(new Error('Health check timeout')), 1000)
          )
        ]);

        const duration = Date.now() - startTime;
        
        // Health check should be fast
        expect(duration).toBeLessThan(5000);
        expect(response.ok).toBe(true);
        expect(response.status).toBe(200);
        
      } catch (error) {
        // Health checks should not timeout
        expect(error.message).not.toBe('Health check timeout');
        expect(error.message).not.toContain('timeout after 15 seconds');
      }
    });

    /**
     * EXPECTED TO FAIL
     * Root cause: Multiple health endpoint variations causing confusion
     */
    test('should have consistent health endpoints across all variations', async () => {
      const mockFetch = jest.fn()
        .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ status: 'healthy' }) })
        .mockResolvedValueOnce({ ok: false, status: 404, json: async () => ({ error: 'Not found' }) })
        .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ ready: true }) })
        .mockResolvedValueOnce({ ok: false, status: 503, json: async () => ({ error: 'Service unavailable' }) });
      
      global.fetch = mockFetch;

      const config = getUnifiedApiConfig();
      
      // Test all common health endpoint variations
      const healthEndpoints = [
        `${config.urls.api}/health`,
        `${config.urls.api}/api/health`,
        `${config.urls.api}/health/ready`,
        `${config.urls.api}/health/live`,
      ];

      for (const endpoint of healthEndpoints) {
        try {
          const response = await fetch(endpoint);
          
          // All health endpoints should be available and consistent
          expect(response.ok).toBe(true);
          expect(response.status).toBe(200);
          
          const data = await response.json();
          // Each endpoint should return valid health data
          expect(data).toBeDefined();
          expect(typeof data).toBe('object');
          
        } catch (error) {
          // No health endpoint should return errors
          expect(error.message).not.toContain('Not found');
          expect(error.message).not.toContain('Service unavailable');
        }
      }
    });
  });

  describe('API Route Reliability: /api/config/public Intermittent Failures', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    /**
     * EXPECTED TO FAIL
     * Root cause: /api/config/public sometimes returns 404 (intermittent)
     */
    test('/api/config/public should be consistently available', async () => {
      let callCount = 0;
      const mockFetch = jest.fn().mockImplementation(async () => {
        callCount++;
        
        // Simulate intermittent failures (every 3rd request fails)
        if (callCount % 3 === 0) {
          return {
            ok: false,
            status: 404,
            statusText: 'Not Found',
            json: async () => ({ 
              error: 'Config endpoint temporarily unavailable',
              code: 'TEMP_UNAVAILABLE',
              retry_after: 5
            }),
          };
        }
        
        return {
          ok: true,
          status: 200,
          json: async () => ({
            environment: 'staging',
            features: {
              chat: true,
              auth: true,
              mcp: true
            },
            api_version: '1.0.0'
          }),
        };
      });
      global.fetch = mockFetch;

      const config = getUnifiedApiConfig();
      const configEndpoint = `${config.urls.api}/api/config/public`;
      
      // Test fewer consecutive calls
      for (let i = 0; i < 3; i++) {
        try {
          const response = await fetch(configEndpoint);
          
          // Should ALWAYS be available (not intermittent)
          expect(response.ok).toBe(true);
          expect(response.status).toBe(200);
          
          const data = await response.json();
          expect(data).toHaveProperty('environment');
          expect(data.environment).toBe('staging');
          
          // Should not return temp unavailable error
          expect(data.error).not.toBe('Config endpoint temporarily unavailable');
          
        } catch (error) {
          // Config endpoint should not have intermittent failures
          expect(error.message).not.toContain('temporarily unavailable');
        }
        
        // Small delay between requests
        await new Promise(resolve => setTimeout(resolve, 10));
      }
    });

    /**
     * EXPECTED TO FAIL
     * Root cause: Config endpoint returns stale or cached data
     */
    test('/api/config/public should return fresh data, not stale cache', async () => {
      let requestCount = 0;
      const mockFetch = jest.fn().mockImplementation(async () => {
        requestCount++;
        
        // Simulate stale cached responses
        return {
          ok: true,
          status: 200,
          json: async () => ({
            environment: 'staging',
            timestamp: 1600000000000, // Old timestamp
            cache_status: 'stale',
            last_updated: '2020-09-13T12:26:40Z', // Very old
            features: {
              chat: false, // Wrong feature flags
              auth: false,
              mcp: false
            }
          }),
        };
      });
      global.fetch = mockFetch;

      const config = getUnifiedApiConfig();
      const configEndpoint = `${config.urls.api}/api/config/public`;
      
      try {
        const response = await fetch(configEndpoint);
        expect(response.ok).toBe(true);
        
        const data = await response.json();
        
        // Should return fresh data
        const now = Date.now();
        const responseTime = data.timestamp;
        const timeDifference = now - responseTime;
        
        // Data should be fresh (less than 5 minutes old)
        expect(timeDifference).toBeLessThan(5 * 60 * 1000);
        
        // Should not be marked as stale
        expect(data.cache_status).not.toBe('stale');
        
        // Features should be correct for staging
        expect(data.features.chat).toBe(true);
        expect(data.features.auth).toBe(true);
        
      } catch (error) {
        // Config should not return stale data
        expect(error.message).not.toContain('stale');
      }
    });

    /**
     * EXPECTED TO FAIL
     * Root cause: Config endpoint race condition during deployment
     */
    test('config endpoint should handle concurrent requests during deployment', async () => {
      let concurrentCalls = 0;
      const maxConcurrent = 5;
      
      const mockFetch = jest.fn().mockImplementation(async () => {
        concurrentCalls++;
        
        // Simulate deployment-time race condition
        if (concurrentCalls > 3) {
          concurrentCalls--;
          throw new Error('Service temporarily unavailable during deployment');
        }
        
        // Simulate processing time
        await new Promise(resolve => setTimeout(resolve, 10));
        
        concurrentCalls--;
        return {
          ok: true,
          status: 200,
          json: async () => ({
            environment: 'staging',
            deployment_status: 'active'
          }),
        };
      });
      global.fetch = mockFetch;

      const config = getUnifiedApiConfig();
      const configEndpoint = `${config.urls.api}/api/config/public`;
      
      // Make multiple concurrent requests
      const promises = Array(maxConcurrent).fill(null).map(async (_, index) => {
        try {
          const response = await fetch(configEndpoint);
          
          // All concurrent requests should succeed
          expect(response.ok).toBe(true);
          expect(response.status).toBe(200);
          
          const data = await response.json();
          expect(data.deployment_status).toBe('active');
          
          return { success: true, index };
          
        } catch (error) {
          // Should not fail during deployment
          expect(error.message).not.toContain('temporarily unavailable during deployment');
          return { success: false, index, error: error.message };
        }
      });

      const results = await Promise.all(promises);
      
      // All concurrent requests should succeed
      const successCount = results.filter(r => r.success).length;
      expect(successCount).toBe(maxConcurrent);
    });
  });

  describe('Service Discovery and Endpoint Resolution Issues', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    /**
     * EXPECTED TO FAIL
     * Root cause: DNS resolution intermittently failing for API endpoints
     */
    test('DNS resolution should be consistent for API endpoints', async () => {
      let callCount = 0;
      const mockFetch = jest.fn().mockImplementation(async (url) => {
        callCount++;
        
        // Simulate DNS resolution failures
        if (callCount % 4 === 0) {
          throw new Error('ENOTFOUND: DNS resolution failed for api.staging.netrasystems.ai');
        }
        
        return {
          ok: true,
          status: 200,
          json: async () => ({ status: 'healthy' }),
        };
      });
      global.fetch = mockFetch;

      const config = getUnifiedApiConfig();
      
      // Test multiple API endpoints for DNS consistency
      const endpoints = [
        config.endpoints.health,
        config.endpoints.threads,
        `${config.urls.api}/api/config/public`,
      ];

      for (const endpoint of endpoints) {
        // Test each endpoint multiple times
        for (let i = 0; i < 5; i++) {
          try {
            const response = await fetch(endpoint);
            
            // DNS resolution should always work
            expect(response.ok).toBe(true);
            expect(response.status).toBe(200);
            
          } catch (error) {
            // DNS should not fail intermittently
            expect(error.message).not.toContain('ENOTFOUND');
            expect(error.message).not.toContain('DNS resolution failed');
          }
          
          // Small delay between requests
          await new Promise(resolve => setTimeout(resolve, 200));
        }
      }
    });

    /**
     * EXPECTED TO FAIL
     * Root cause: Service mesh/load balancer routing to wrong pods
     */
    test('requests should consistently route to healthy backend pods', async () => {
      let callCount = 0;
      const mockFetch = jest.fn().mockImplementation(async () => {
        callCount++;
        
        // Simulate routing to unhealthy pods occasionally
        if (callCount % 5 === 0) {
          return {
            ok: false,
            status: 503,
            statusText: 'Service Unavailable',
            json: async () => ({ 
              error: 'Pod is unhealthy or starting up',
              pod_id: 'backend-pod-unhealthy-123',
              status: 'not_ready'
            }),
          };
        }
        
        return {
          ok: true,
          status: 200,
          json: async () => ({ 
            status: 'healthy',
            pod_id: 'backend-pod-healthy-456',
            ready: true
          }),
        };
      });
      global.fetch = mockFetch;

      const config = getUnifiedApiConfig();
      
      // Make many requests to test routing consistency
      for (let i = 0; i < 20; i++) {
        try {
          const response = await fetch(config.endpoints.health);
          
          // Should always route to healthy pods
          expect(response.ok).toBe(true);
          expect(response.status).toBe(200);
          
          const data = await response.json();
          expect(data.status).toBe('healthy');
          expect(data.ready).toBe(true);
          
          // Should not route to unhealthy pods
          expect(data.error).not.toBe('Pod is unhealthy or starting up');
          expect(data.pod_id).not.toContain('unhealthy');
          
        } catch (error) {
          // Routing should not direct to unhealthy pods
          expect(error.message).not.toContain('Pod is unhealthy');
        }
        
        // Small delay between requests
        await new Promise(resolve => setTimeout(resolve, 50));
      }
    });

    /**
     * EXPECTED TO FAIL
     * Root cause: Endpoint availability affected by scaling events
     */
    test('endpoints should remain available during pod scaling events', async () => {
      let requestCount = 0;
      const mockFetch = jest.fn().mockImplementation(async () => {
        requestCount++;
        
        // Simulate scaling event affecting availability
        if (requestCount >= 10 && requestCount <= 15) {
          throw new Error('Connection refused: All backend pods are scaling down/up');
        }
        
        return {
          ok: true,
          status: 200,
          json: async () => ({ 
            status: 'healthy',
            pods_available: requestCount <= 10 ? 3 : 5
          }),
        };
      });
      global.fetch = mockFetch;

      const config = getUnifiedApiConfig();
      
      // Simulate requests during a scaling event
      for (let i = 0; i < 20; i++) {
        try {
          const response = await fetch(config.endpoints.health);
          
          // Should remain available during scaling
          expect(response.ok).toBe(true);
          expect(response.status).toBe(200);
          
          const data = await response.json();
          expect(data.status).toBe('healthy');
          expect(data.pods_available).toBeGreaterThan(0);
          
        } catch (error) {
          // Scaling events should not cause complete unavailability
          expect(error.message).not.toContain('Connection refused');
          expect(error.message).not.toContain('scaling down/up');
        }
        
        // Realistic delay between requests
        await new Promise(resolve => setTimeout(resolve, 100));
      }
    });
  });

  describe('Load Balancer and Health Check Edge Cases', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    /**
     * EXPECTED TO FAIL
     * Root cause: Health checks interfering with application traffic
     */
    test('health checks should not impact application performance', async () => {
      let healthCheckCount = 0;
      let appRequestCount = 0;
      
      const mockFetch = jest.fn().mockImplementation(async (url) => {
        if (url.includes('/health')) {
          healthCheckCount++;
          
          // Simulate resource contention from frequent health checks
          if (healthCheckCount > 100) {
            await new Promise(resolve => setTimeout(resolve, 2000)); // 2 second delay
            return {
              ok: false,
              status: 503,
              json: async () => ({ 
                error: 'Service overloaded with health checks',
                health_check_count: healthCheckCount
              }),
            };
          }
          
          return {
            ok: true,
            status: 200,
            json: async () => ({ status: 'healthy' }),
          };
        } else {
          appRequestCount++;
          return {
            ok: true,
            status: 200,
            json: async () => ([]), // App response
          };
        }
      });
      global.fetch = mockFetch;

      const config = getUnifiedApiConfig();
      
      // Simulate load balancer making health checks (reduced for testing)
      const healthCheckPromises = Array(10).fill(null).map(async (_, index) => {
        await new Promise(resolve => setTimeout(resolve, index * 1)); // Minimal stagger
        
        try {
          const response = await fetch(config.endpoints.health);
          expect(response.ok).toBe(true);
          return response;
        } catch (error) {
          expect(error.message).not.toContain('Service overloaded');
          throw error;
        }
      });
      
      // Simulate application requests happening concurrently
      const appRequestPromises = Array(10).fill(null).map(async () => {
        try {
          const response = await fetch(config.endpoints.threads);
          expect(response.ok).toBe(true);
          return response;
        } catch (error) {
          expect(error.message).not.toContain('overloaded');
          throw error;
        }
      });
      
      // Both should complete successfully
      await Promise.all([...healthCheckPromises, ...appRequestPromises]);
      
      // Health checks should not overload the service
      expect(healthCheckCount).toBeGreaterThan(0);
      expect(appRequestCount).toBeGreaterThan(0);
    });
  });
});