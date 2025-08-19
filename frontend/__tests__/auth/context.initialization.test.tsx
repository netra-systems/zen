/**
 * AuthContext Initialization Tests
 * Tests provider mounting, loading states, and config fetching
 * All functions ≤8 lines per architecture requirements
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { AuthProvider } from '@/auth/context';
import { authService } from '@/auth/service';
import { logger } from '@/lib/logger';
import '@testing-library/jest-dom';
import {
  setupBasicMocks,
  setupAuthStore,
  setupAuthConfigError,
  mockAuthConfig
} from './helpers/test-helpers';

// Mock dependencies
jest.mock('@/auth/service');
jest.mock('jwt-decode');
jest.mock('@/store/authStore');
jest.mock('@/lib/logger', () => ({
  logger: {
    info: jest.fn(),
    warn: jest.fn(),
    error: jest.fn(),
    debug: jest.fn()
  }
}));

// Mock auth service client for independent service
jest.mock('@/lib/auth-service-config', () => ({
  authService: {
    getConfig: jest.fn().mockResolvedValue({
      development_mode: false,
      google_client_id: 'mock-google-client-id',
      oauth_enabled: true,
      offline_mode: false
    }),
    getSession: jest.fn(),
    getCurrentUser: jest.fn(),
    validateToken: jest.fn(),
    refreshToken: jest.fn()
  },
  getAuthServiceConfig: jest.fn().mockReturnValue({
    baseUrl: 'http://localhost:8081',
    endpoints: {
      login: 'http://localhost:8081/auth/login',
      logout: 'http://localhost:8081/auth/logout',
      callback: 'http://localhost:8081/auth/callback',
      token: 'http://localhost:8081/auth/token',
      refresh: 'http://localhost:8081/auth/refresh',
      validate_token: 'http://localhost:8081/auth/validate',
      config: 'http://localhost:8081/auth/config',
      session: 'http://localhost:8081/auth/session',
      me: 'http://localhost:8081/auth/me'
    },
    oauth: {
      googleClientId: 'mock-google-client-id',
      redirectUri: 'http://localhost:3000/auth/callback',
      javascriptOrigins: ['http://localhost:3000']
    }
  })
}));

describe('AuthContext - Initialization', () => {
  let mockAuthStore: any;

  beforeEach(() => {
    mockAuthStore = setupAuthStore();
    setupBasicMocks();
  });

  const renderAuthProvider = () => {
    return render(
      <AuthProvider>
        <div>Test Content</div>
      </AuthProvider>
    );
  };

  const waitForContentLoad = async () => {
    await waitFor(() => {
      expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
    });
  };

  it('should render loading state initially', async () => {
    renderAuthProvider();
    expect(screen.getByText('Loading...')).toBeInTheDocument();
    await waitForContentLoad();
  });

  it('should fetch auth config on mount', async () => {
    renderAuthProvider();
    await waitFor(() => {
      expect(authService.getAuthConfig).toHaveBeenCalledTimes(1);
    });
  });

  const setupConfigError = () => {
    setupAuthConfigError();
  };

  const expectConfigErrorHandling = async () => {
    await waitFor(() => {
      expect(logger.error).toHaveBeenCalledWith(
        'Failed to fetch auth config - backend may be offline',
        expect.any(Error),
        {
          component: 'AuthContext',
          action: 'fetch_auth_config_failed'
        }
      );
    });
  };

  it('should handle auth config fetch error gracefully', async () => {
    setupConfigError();
    renderAuthProvider();
    await expectConfigErrorHandling();
  });
});