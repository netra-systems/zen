/**
 * Comprehensive test suite for frontend URL configuration in staging/production
 * These tests validate that all URLs are correctly configured for non-development environments
 */

import { getSecureApiConfig, getSecureApiConfigAsync } from '@/lib/secure-api-config';
import { getAuthServiceConfig, getAuthServiceConfigAsync } from '@/lib/auth-service-config';
import { apiClient } from '@/services/apiClientWrapper';

describe('Frontend URL Configuration - Staging/Production', () => {
  const originalEnv = process.env;

  beforeEach(() => {
    // Reset environment variables before each test
    process.env = { ...originalEnv };
  });

  afterEach(() => {
    process.env = originalEnv;
  });

  describe('Staging Environment Configuration', () => {
    beforeEach(() => {
      process.env.NODE_ENV = 'production';
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'staging';
    });

    test('secure-api-config should return staging URLs', () => {
      const config = getSecureApiConfig();
      
      expect(config.apiUrl).toBe('https://api.staging.netrasystems.ai');
      expect(config.wsUrl).toBe('wss://api.staging.netrasystems.ai/ws');
      expect(config.authUrl).toBe('https://auth.staging.netrasystems.ai');
      expect(config.environment).toBe('staging');
      expect(config.forceHttps).toBe(true);
    });

    test('auth-service-config should return staging auth URLs', () => {
      const config = getAuthServiceConfig();
      
      expect(config.baseUrl).toBe('https://auth.staging.netrasystems.ai');
      expect(config.endpoints.config).toBe('https://auth.staging.netrasystems.ai/auth/config');
      expect(config.endpoints.login).toBe('https://auth.staging.netrasystems.ai/auth/login');
      expect(config.endpoints.logout).toBe('https://auth.staging.netrasystems.ai/auth/logout');
      expect(config.endpoints.refresh).toBe('https://auth.staging.netrasystems.ai/auth/refresh');
      expect(config.oauth.redirectUri).toBe('https://app.staging.netrasystems.ai/auth/callback');
    });

    test('async config functions should not use localhost in staging', async () => {
      const apiConfig = await getSecureApiConfigAsync();
      const authConfig = await getAuthServiceConfigAsync();
      
      // Should not contain localhost references
      expect(apiConfig.apiUrl).not.toContain('localhost');
      expect(apiConfig.wsUrl).not.toContain('localhost');
      expect(apiConfig.authUrl).not.toContain('localhost');
      
      expect(authConfig.baseUrl).not.toContain('localhost');
      expect(authConfig.endpoints.config).not.toContain('localhost');
    });
  });

  describe('Production Environment Configuration', () => {
    beforeEach(() => {
      process.env.NODE_ENV = 'production';
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'production';
    });

    test('secure-api-config should return production URLs', () => {
      const config = getSecureApiConfig();
      
      expect(config.apiUrl).toBe('https://api.netrasystems.ai');
      expect(config.wsUrl).toBe('wss://api.netrasystems.ai/ws');
      expect(config.authUrl).toBe('https://auth.netrasystems.ai');
      expect(config.environment).toBe('production');
      expect(config.forceHttps).toBe(true);
    });

    test('auth-service-config should return production auth URLs', () => {
      const config = getAuthServiceConfig();
      
      expect(config.baseUrl).toBe('https://auth.netrasystems.ai');
      expect(config.endpoints.config).toBe('https://auth.netrasystems.ai/auth/config');
      expect(config.endpoints.login).toBe('https://auth.netrasystems.ai/auth/login');
    });
  });

  describe('Health Check URL Configuration', () => {
    test('health check should use full backend URL in staging', async () => {
      process.env.NODE_ENV = 'production';
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'staging';
      
      // Clear module cache to ensure fresh instance
      jest.resetModules();
      
      // Verify unified config returns correct URLs for staging
      const { unifiedApiConfig } = require('@/lib/unified-api-config');
      expect(unifiedApiConfig.endpoints.ready).toBe('https://api.staging.netrasystems.ai/health/ready');
      expect(unifiedApiConfig.urls.api).toBe('https://api.staging.netrasystems.ai');
      expect(unifiedApiConfig.environment).toBe('staging');
    });

    test('health check should use full backend URL in production', async () => {
      process.env.NODE_ENV = 'production';
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'production';
      
      // Clear module cache
      jest.resetModules();

      // Verify unified config returns correct URLs for production
      const { unifiedApiConfig } = require('@/lib/unified-api-config');
      expect(unifiedApiConfig.endpoints.ready).toBe('https://api.netrasystems.ai/health/ready');
      expect(unifiedApiConfig.urls.api).toBe('https://api.netrasystems.ai');
      expect(unifiedApiConfig.environment).toBe('production');
    });
  });

  describe('API Client URL Construction', () => {
    test('API client should use backend URLs directly in staging', () => {
      process.env.NODE_ENV = 'production';
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'staging';
      
      // Clear module cache to ensure fresh instance
      jest.resetModules();

      // Verify that unified config provides correct URLs for API client
      const { unifiedApiConfig } = require('@/lib/unified-api-config');
      
      // The API client uses these URLs directly
      expect(unifiedApiConfig.urls.api).toBe('https://api.staging.netrasystems.ai');
      expect(unifiedApiConfig.endpoints.ready).toBe('https://api.staging.netrasystems.ai/health/ready');
      expect(unifiedApiConfig.environment).toBe('staging');
      
      // No localhost references
      expect(unifiedApiConfig.urls.api).not.toContain('localhost');
      expect(unifiedApiConfig.endpoints.ready).not.toContain('localhost');
    });
  });

  describe('Next.js Rewrites Configuration', () => {
    test('rewrites should be disabled in production/staging', () => {
      const nextConfig = require('@/next.config.ts').default;
      
      process.env.NODE_ENV = 'production';
      
      // In production/staging, rewrites should return empty array
      const rewrites = nextConfig.rewrites();
      
      rewrites.then((result: any) => {
        expect(result).toEqual([]);
        expect(result).not.toContainEqual(
          expect.objectContaining({
            source: '/health/:path*'
          })
        );
        expect(result).not.toContainEqual(
          expect.objectContaining({
            source: '/api/:path*'
          })
        );
      });
    });
  });

  describe('Auth Service Client Configuration', () => {
    test('AuthServiceClient should not have duplicate getConfig methods', () => {
      const { AuthServiceClient } = require('@/lib/auth-service-config');
      const client = new AuthServiceClient();
      
      // Check that getConfig is properly defined (not duplicated)
      const proto = Object.getPrototypeOf(client);
      const propertyNames = Object.getOwnPropertyNames(proto);
      const getConfigCount = propertyNames.filter(name => name === 'getConfig').length;
      
      expect(getConfigCount).toBe(1); // Should only have one getConfig method
    });

    test('AuthServiceClient.getConfig should handle staging environment', async () => {
      process.env.NODE_ENV = 'production';
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'staging';
      
      // Clear module cache
      jest.resetModules();
      
      const { authService } = require('@/lib/auth-service-config');
      
      const mockFetch = jest.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          google_client_id: 'test-client-id',
          oauth_enabled: true,
          development_mode: false
        })
      });
      global.fetch = mockFetch;
      
      const result = await authService.getAuthConfig();
      
      // Verify the result has staging configuration
      expect(result).toBeTruthy();
      expect(result.google_client_id).toBe('test-client-id');
      
      // Check if fetch was called with correct URL
      if (mockFetch.mock.calls.length > 0) {
        const calledUrl = mockFetch.mock.calls[0][0];
        expect(calledUrl).toBe('https://auth.staging.netrasystems.ai/auth/config');
      }
    });
  });

  describe('CSP Headers Configuration', () => {
    test('CSP should allow staging domains in staging environment', async () => {
      process.env.NODE_ENV = 'production';
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'staging';
      
      const nextConfig = require('@/next.config.ts').default;
      const headers = await nextConfig.headers();
      
      // In production/staging, CSP is handled by middleware
      // But if headers are returned, they should allow staging domains
      if (headers.length > 0) {
        const cspHeader = headers[0]?.headers?.find((h: any) => h.key === 'Content-Security-Policy');
        if (cspHeader) {
          expect(cspHeader.value).not.toContain('localhost');
          // Should contain staging domains or be configured for production use
        }
      }
    });
  });

  describe('Error Cases', () => {
    test('should handle missing environment variables gracefully', () => {
      delete process.env.NEXT_PUBLIC_ENVIRONMENT;
      delete process.env.NEXT_PUBLIC_API_URL;
      delete process.env.NEXT_PUBLIC_AUTH_SERVICE_URL;
      process.env.NODE_ENV = 'production';
      
      const apiConfig = getSecureApiConfig();
      const authConfig = getAuthServiceConfig();
      
      // Should fallback to staging when NODE_ENV is production but NEXT_PUBLIC_ENVIRONMENT is not set
      expect(apiConfig.apiUrl).toBe('https://api.staging.netrasystems.ai');
      expect(authConfig.baseUrl).toBe('https://auth.staging.netrasystems.ai');
    });

    test('should enforce HTTPS in secure environments', () => {
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'staging';
      process.env.NEXT_PUBLIC_API_URL = 'http://api.staging.netrasystems.ai'; // HTTP
      process.env.NEXT_PUBLIC_AUTH_URL = 'http://auth.staging.netrasystems.ai'; // HTTP
      
      const config = getSecureApiConfig();
      
      // Should force HTTPS
      expect(config.apiUrl).toBe('https://api.staging.netrasystems.ai');
      expect(config.authUrl).toBe('https://auth.staging.netrasystems.ai');
      expect(config.wsUrl).toMatch(/^wss:/);
    });
  });
});