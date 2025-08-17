/**
 * AuthContext Initialization Tests
 * Tests provider mounting, loading states, and config fetching
 * All functions ≤8 lines per architecture requirements
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { AuthProvider } from '@/auth/context';
import { authService } from '@/auth/service';
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
    const consoleError = jest.spyOn(console, 'error').mockImplementation();
    setupAuthConfigError();
    return consoleError;
  };

  const expectConfigErrorHandling = async (consoleError: jest.SpyInstance) => {
    await waitFor(() => {
      expect(consoleError).toHaveBeenCalledWith(
        'Failed to fetch auth config:',
        expect.any(Error)
      );
    });
    consoleError.mockRestore();
  };

  it('should handle auth config fetch error gracefully', async () => {
    const consoleError = setupConfigError();
    renderAuthProvider();
    await expectConfigErrorHandling(consoleError);
  });
});