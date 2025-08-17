/**
 * AuthContext Edge Cases Tests
 * Tests edge cases, store sync, permissions, and concurrent operations
 * All functions ≤8 lines per architecture requirements
 */

import React from 'react';
import { render, waitFor, act } from '@testing-library/react';
import { jwtDecode } from 'jwt-decode';
import { authService } from '@/auth/service';
import '@testing-library/jest-dom';
import {
  setupBasicMocks,
  setupAuthStore,
  setupTokenMocks,
  renderAuthHook,
  expectAuthStoreLogin,
  expectContextValues,
  mockToken,
  mockUser,
  mockAuthConfig
} from './helpers/test-helpers';

// Mock dependencies
jest.mock('@/auth/service');
jest.mock('jwt-decode');
jest.mock('@/store/authStore');

describe('AuthContext - Edge Cases', () => {
  let mockAuthStore: any;

  beforeEach(() => {
    mockAuthStore = setupAuthStore();
    setupBasicMocks();
  });

  const setupUserWithoutId = () => {
    const userWithoutId = { ...mockUser, id: undefined, sub: undefined };
    setupTokenMocks();
    (jwtDecode as jest.Mock).mockReturnValue(userWithoutId);
    return userWithoutId;
  };

  const expectEmptyIdHandling = async () => {
    await waitFor(() => {
      expect(mockAuthStore.login).toHaveBeenCalledWith(
        expect.objectContaining({ id: '' }),
        mockToken
      );
    });
  };

  it('should handle missing user ID gracefully', async () => {
    setupUserWithoutId();
    render(<div>Test</div>);
    await expectEmptyIdHandling();
  });

  const setupUserWithoutName = () => {
    const userWithoutName = { ...mockUser, full_name: undefined, name: undefined };
    setupTokenMocks();
    (jwtDecode as jest.Mock).mockReturnValue(userWithoutName);
    return userWithoutName;
  };

  const expectUndefinedNameHandling = async () => {
    await waitFor(() => {
      expect(mockAuthStore.login).toHaveBeenCalledWith(
        expect.objectContaining({ name: undefined }),
        mockToken
      );
    });
  };

  it('should handle missing user name gracefully', async () => {
    setupUserWithoutName();
    render(<div>Test</div>);
    await expectUndefinedNameHandling();
  });

  const setupPermissionsTest = () => {
    const userWithPermissions = {
      ...mockUser,
      permissions: ['read', 'write', 'admin']
    };
    setupTokenMocks();
    (jwtDecode as jest.Mock).mockReturnValue(userWithPermissions);
    return userWithPermissions;
  };

  const expectPermissionsInContext = async (result: any, user: any) => {
    await waitFor(() => {
      expect(result.current?.user).toMatchObject(user);
    });
  };

  it('should handle user permissions from token', async () => {
    const userWithPermissions = setupPermissionsTest();
    const { result } = renderAuthHook();
    await expectPermissionsInContext(result, userWithPermissions);
  });

  const setupRoleTest = () => {
    const userWithRole = {
      ...mockUser,
      role: 'admin',
      scope: 'full-access'
    };
    setupTokenMocks();
    (jwtDecode as jest.Mock).mockReturnValue(userWithRole);
    return userWithRole;
  };

  const expectRoleInContext = async (result: any) => {
    await waitFor(() => {
      expect(result.current?.user).toMatchObject({
        role: 'admin',
        scope: 'full-access'
      });
    });
  };

  it('should handle role-based access from token', async () => {
    setupRoleTest();
    const { result } = renderAuthHook();
    await expectRoleInContext(result);
  });

  const performConcurrentOperations = async (result: any) => {
    await act(async () => {
      result.current?.login();
    });
    await act(async () => {
      await result.current?.logout();
    });
    await act(async () => {
      result.current?.login();
    });
  };

  const expectConcurrentCalls = () => {
    expect(authService.handleLogin).toHaveBeenCalled();
    expect(authService.handleLogout).toHaveBeenCalled();
  };

  it('should handle concurrent auth operations', async () => {
    const { result } = renderAuthHook();
    await waitFor(() => {
      expect(result.current).toBeDefined();
    });
    await performConcurrentOperations(result);
    expectConcurrentCalls();
  });

  const expectStoreSync = async () => {
    await waitFor(() => {
      expect(mockAuthStore.logout).toHaveBeenCalled();
    });
  };

  it('should sync logout with Zustand store', async () => {
    const { result } = renderAuthHook();
    await waitFor(() => {
      expect(result.current?.authConfig).toEqual(mockAuthConfig);
    });
    await act(async () => {
      await result.current?.logout();
    });
    await expectStoreSync();
  });

  const expectContextProviderValues = async (result: any) => {
    await waitFor(() => {
      expectContextValues(result, {
        user: expect.objectContaining({
          id: mockUser.id,
          email: mockUser.email
        }),
        login: expect.any(Function),
        logout: expect.any(Function),
        loading: false,
        authConfig: mockAuthConfig,
        token: mockToken
      });
    });
  };

  it('should provide all context values', async () => {
    setupTokenMocks();
    const { result } = renderAuthHook();
    await expectContextProviderValues(result);
  });

  const expectNullUser = async (result: any) => {
    await waitFor(() => {
      expectContextValues(result, {
        user: null,
        token: null,
        loading: false
      });
    });
  };

  it('should provide null user when not authenticated', async () => {
    const { result } = renderAuthHook();
    await expectNullUser(result);
  });
});