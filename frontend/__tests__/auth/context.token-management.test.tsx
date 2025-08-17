/**
 * AuthContext Token Management Tests
 * Tests token validation, refresh, and storage functionality
 * All functions ≤8 lines per architecture requirements
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { AuthProvider } from '@/auth/context';
import { authService } from '@/auth/service';
import { jwtDecode } from 'jwt-decode';
import '@testing-library/jest-dom';
import {
  setupBasicMocks,
  setupAuthStore,
  setupTokenMocks,
  expectAuthStoreLogin,
  mockToken,
  mockUser,
  mockAuthConfig
} from './helpers/test-helpers';

// Mock dependencies
jest.mock('@/auth/service');
jest.mock('jwt-decode');
jest.mock('@/store/authStore');

describe('AuthContext - Token Management', () => {
  let mockAuthStore: any;

  beforeEach(() => {
    mockAuthStore = setupAuthStore();
    setupBasicMocks();
  });

  const renderWithToken = () => {
    setupTokenMocks();
    return render(
      <AuthProvider>
        <div>Test Content</div>
      </AuthProvider>
    );
  };

  const waitForTokenProcessing = async () => {
    await waitFor(() => {
      expect(jwtDecode).toHaveBeenCalledWith(mockToken);
    });
  };

  it('should use existing token from storage', async () => {
    renderWithToken();
    await waitForTokenProcessing();
    expectAuthStoreLogin(mockAuthStore);
  });

  const setupInvalidToken = () => {
    const consoleError = jest.spyOn(console, 'error').mockImplementation();
    setupTokenMocks();
    (jwtDecode as jest.Mock).mockImplementation(() => {
      throw new Error('Invalid token');
    });
    return consoleError;
  };

  const expectInvalidTokenHandling = async (consoleError: jest.SpyInstance) => {
    await waitFor(() => {
      expect(consoleError).toHaveBeenCalledWith('Invalid token:', expect.any(Error));
      expect(authService.removeToken).toHaveBeenCalled();
      expect(mockAuthStore.logout).toHaveBeenCalled();
    });
    consoleError.mockRestore();
  };

  it('should handle invalid token gracefully', async () => {
    const consoleError = setupInvalidToken();
    render(<AuthProvider><div>Test Content</div></AuthProvider>);
    await expectInvalidTokenHandling(consoleError);
  });

  const renderWithoutToken = () => {
    (authService.getToken as jest.Mock).mockReturnValue(null);
    return render(
      <AuthProvider>
        <div>Test Content</div>
      </AuthProvider>
    );
  };

  const setupTokenRefresh = () => {
    jest.clearAllMocks();
    (authService.getAuthConfig as jest.Mock).mockResolvedValue(mockAuthConfig);
    (authService.getToken as jest.Mock).mockReturnValue(mockToken);
  };

  const performRerender = (rerender: any) => {
    rerender(
      <AuthProvider>
        <div>Test Content Updated</div>
      </AuthProvider>
    );
  };

  const waitForUpdatedContent = async () => {
    await waitFor(() => {
      expect(screen.getByText('Test Content Updated')).toBeInTheDocument();
    }, { timeout: 3000 });
  };

  it('should handle token refresh mechanism', async () => {
    const { rerender } = renderWithoutToken();
    await waitFor(() => {
      expect(screen.getByText('Test Content')).toBeInTheDocument();
    });
    setupTokenRefresh();
    performRerender(rerender);
    await waitForUpdatedContent();
  });
});