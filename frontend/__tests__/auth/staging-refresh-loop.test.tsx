/**
 * Tests for staging environment refresh loop issue
 * These tests recreate the scenarios that cause infinite refresh loops in staging
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth } from '@/auth';
import { useRouter } from 'next/navigation';
import HomePage from '@/app/page';
import AuthCallbackClient from '@/app/auth/callback/client';
import { logger } from '@/lib/logger';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

// Mock Next.js navigation
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
  useSearchParams: jest.fn(),
}));

// Mock logger
jest.mock('@/lib/logger', () => ({
  logger: {
    info: jest.fn(),
    error: jest.fn(),
    warn: jest.fn(),
    debug: jest.fn(),
  },
}));

// Mock unified auth service
jest.mock('@/auth/unified-auth-service', () => ({
  unifiedAuthService: {
    getAuthConfig: jest.fn(),
    handleDevLogin: jest.fn(),
    handleLogin: jest.fn(),
    handleLogout: jest.fn(),
    getToken: jest.fn(),
    setToken: jest.fn(),
    removeToken: jest.fn(),
    needsRefresh: jest.fn(),
    refreshToken: jest.fn(),
  },
}));

// Mock auth service client
jest.mock('@/lib/auth-service-client', () => ({
  authServiceClient: {
    getAuthConfig: jest.fn(),
    initiateLogin: jest.fn(),
    logout: jest.fn(),
  },
}));

describe('Staging Refresh Loop Tests', () => {
      setupAntiHang();
    jest.setTimeout(10000);
  // Set test timeout to prevent hanging
  jest.setTimeout(8000);
  let mockPush: jest.Mock;
  let mockReload: jest.Mock;
  let originalLocation: Location;

  beforeEach(() => {
    jest.clearAllMocks();
    mockPush = jest.fn();
    mockReload = jest.fn();
    
    (useRouter as jest.Mock).mockReturnValue({
      push: mockPush,
      replace: jest.fn(),
      refresh: jest.fn(),
    });

    // Save original location
    originalLocation = window.location;
    
    // Mock window.location properties
    Object.defineProperty(window, 'location', {
      value: {
        ...originalLocation,
        reload: mockReload,
        href: 'https://app.staging.netrasystems.ai/',
        hostname: 'app.staging.netrasystems.ai',
      },
      writable: true,
      configurable: true,
    });

    // Clear localStorage
    localStorage.clear();

    // Set staging environment
    process.env.NEXT_PUBLIC_ENVIRONMENT = 'staging';
  });

  afterEach(() => {
    window.location = originalLocation;
    delete process.env.NEXT_PUBLIC_ENVIRONMENT;
    // Clean up timers to prevent hanging
    jest.clearAllTimers();
    jest.useFakeTimers();
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
      cleanupAntiHang();
  });

  describe('Test 1: Auth Token Refresh Loop', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should detect infinite loop when token refresh keeps triggering on every render', async () => {
      const { unifiedAuthService } = require('@/auth/unified-auth-service');
      
      // Setup: Token exists but always needs refresh
      localStorage.setItem('jwt_token', 'expired_token');
      unifiedAuthService.getToken.mockReturnValue('expired_token');
      unifiedAuthService.needsRefresh.mockReturnValue(true);
      
      // Simulate refresh that returns same expired token (common in staging)
      let refreshCount = 0;
      unifiedAuthService.refreshToken.mockImplementation(async () => {
        refreshCount++;
        if (refreshCount > 3) {
          throw new Error('Too many refresh attempts - infinite loop detected!');
        }
        return { access_token: 'expired_token' }; // Returns same token
      });

      const TestComponent = () => {
        const { token, loading } = useAuth();
        return (
          <div>
            {loading ? 'Loading' : 'Loaded'}
            {token && <span>Token: {token}</span>}
          </div>
        );
      };

      // This should trigger the refresh loop
      await expect(async () => {
        render(
          <AuthProvider>
            <TestComponent />
          </AuthProvider>
        );
        
        await waitFor(() => {
          expect(refreshCount).toBeGreaterThan(3);
        }, { timeout: 5000 });
      }).rejects.toThrow('Too many refresh attempts');
    });

    it('should detect refresh loop when auth config fetch fails repeatedly', async () => {
      const { authServiceClient } = require('@/lib/auth-service-client');
      
      // Simulate auth service being unreachable (common in staging)
      let configFetchCount = 0;
      authServiceClient.getAuthConfig.mockImplementation(async () => {
        configFetchCount++;
        if (configFetchCount > 5) {
          throw new Error('Auth config fetch loop detected!');
        }
        throw new Error('Network error: auth service unreachable');
      });

      const TestComponent = () => {
        const { authConfig, loading } = useAuth();
        return <div>{loading ? 'Loading' : `Config: ${authConfig ? 'loaded' : 'missing'}`}</div>;
      };

      // This should trigger repeated auth config fetches
      await expect(async () => {
        render(
          <AuthProvider>
            <TestComponent />
          </AuthProvider>
        );

        await waitFor(() => {
          expect(configFetchCount).toBeGreaterThan(5);
        }, { timeout: 5000 });
      }).rejects.toThrow('Auth config fetch loop detected');
    });
  });

  describe('Test 2: Route Guard Infinite Redirect', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should detect infinite redirect between login and home page', async () => {
      const { unifiedAuthService } = require('@/auth/unified-auth-service');
      
      // Setup: No token, auth initialized but user is null
      unifiedAuthService.getToken.mockReturnValue(null);
      
      let redirectCount = 0;
      const mockPushWithLimit = jest.fn((path) => {
        redirectCount++;
        if (redirectCount > 5) {
          throw new Error(`Infinite redirect loop detected! Redirecting to ${path} for the ${redirectCount}th time`);
        }
        
        // Simulate the navigation behavior
        if (path === '/login') {
          // Login page redirects to chat if it thinks user is logged in
          setTimeout(() => mockPushWithLimit('/chat'), 0);
        } else if (path === '/chat' || path === '/') {
          // Chat/Home redirects to login if no user
          setTimeout(() => mockPushWithLimit('/login'), 0);
        }
      });

      (useRouter as jest.Mock).mockReturnValue({
        push: mockPushWithLimit,
      });

      // Render home page which should start the redirect loop
      render(<HomePage />);

      await waitFor(() => {
        expect(redirectCount).toBeGreaterThan(5);
      }, { timeout: 5000 });
    });

    it('should detect callback page refresh loop on OAuth error', async () => {
      const { useSearchParams } = require('next/navigation');
      
      // Simulate OAuth callback with error
      useSearchParams.mockReturnValue({
        get: (key: string) => {
          if (key === 'error') return 'oauth_config_error';
          if (key === 'message') return 'OAuth Configuration Error';
          return null;
        },
      });

      let reloadCount = 0;
      window.location.reload = jest.fn(() => {
        reloadCount++;
        if (reloadCount > 2) {
          throw new Error('Page reload loop detected on OAuth error!');
        }
      });

      render(<AuthCallbackClient />);

      // Wait for component to process error
      await waitFor(() => {
        expect(screen.getByText(/CRITICAL AUTHENTICATION ERROR/)).toBeInTheDocument();
      });

      // Click retry button which triggers reload
      const retryButton = screen.getByText('Retry Authentication');
      retryButton.click();

      expect(window.location.reload).toHaveBeenCalled();
    });
  });

  describe('Test 3: Environment Config Mismatch', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should detect issues when staging URLs resolve to localhost', async () => {
      const { unifiedApiConfig } = require('@/lib/unified-api-config');
      
      // This simulates a common staging misconfiguration
      const config = {
        environment: 'staging',
        urls: {
          api: 'http://localhost:3003', // Wrong! Should be staging URL
          auth: 'http://localhost:3001', // Wrong! Should be staging URL
          websocket: 'ws://localhost:3003',
          frontend: 'https://app.staging.netrasystems.ai',
        },
      };

      // Test that this misconfiguration causes issues
      expect(config.urls.api).not.toContain('staging');
      expect(config.urls.auth).not.toContain('staging');
      
      // In staging, these should never be localhost
      expect(config.environment === 'staging' && config.urls.api.includes('localhost')).toBe(true);
      
      // This configuration would cause CORS errors and auth failures
      throw new Error('Environment config mismatch: Staging environment using localhost URLs!');
    });

    it('should detect when auth service returns dev mode config in staging', async () => {
      const { authServiceClient } = require('@/lib/auth-service-client');
      
      // Auth service incorrectly returns dev mode config in staging
      authServiceClient.getAuthConfig.mockResolvedValue({
        development_mode: true, // Wrong! Should be false in staging
        google_client_id: '',
        endpoints: {
          login: 'http://localhost:3001/auth/login', // Wrong URLs
          callback: 'http://localhost:3000/auth/callback',
        },
      });

      const TestComponent = () => {
        const { authConfig } = useAuth();
        
        if (authConfig && process.env.NEXT_PUBLIC_ENVIRONMENT === 'staging') {
          if (authConfig.development_mode) {
            throw new Error('Critical: Development mode enabled in staging environment!');
          }
          if (authConfig.endpoints.login.includes('localhost')) {
            throw new Error('Critical: Localhost URLs in staging auth config!');
          }
        }
        
        return <div>Config loaded</div>;
      };

      await expect(async () => {
        render(
          <AuthProvider>
            <TestComponent />
          </AuthProvider>
        );

        await waitFor(() => {
          const { authConfig } = useAuth();
          return authConfig !== null;
        });
      }).rejects.toThrow(/Critical:/);
    });

    it('should detect infinite loop when frontend and backend environment mismatch', async () => {
      // Frontend thinks it's staging
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'staging';
      window.location.hostname = 'app.staging.netrasystems.ai';
      
      // But backend returns development configuration
      const { authServiceClient } = require('@/lib/auth-service-client');
      authServiceClient.getAuthConfig.mockResolvedValue({
        development_mode: true,
        endpoints: {
          login: '/auth/dev/login',
          callback: 'http://localhost:3000/auth/callback',
        },
      });

      // This mismatch causes the app to try dev login in staging
      // which fails, causing a redirect loop
      let loginAttempts = 0;
      global.fetch = jest.fn().mockImplementation((url) => {
        if (url.includes('/auth/dev/login')) {
          loginAttempts++;
          if (loginAttempts > 3) {
            throw new Error('Dev login attempted multiple times in staging - loop detected!');
          }
          return Promise.reject(new Error('Dev login not available in staging'));
        }
        return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
      });

      const TestComponent = () => {
        const { login, authConfig } = useAuth();
        
        React.useEffect(() => {
          if (authConfig?.development_mode && process.env.NEXT_PUBLIC_ENVIRONMENT === 'staging') {
            // Try dev login which will fail
            login();
          }
        }, [authConfig, login]);
        
        return <div>Testing environment mismatch</div>;
      };

      await expect(async () => {
        render(
          <AuthProvider>
            <TestComponent />
          </AuthProvider>
        );

        await waitFor(() => {
          expect(loginAttempts).toBeGreaterThan(3);
        }, { timeout: 5000 });
      }).rejects.toThrow('Dev login attempted multiple times');
    });
  });
});