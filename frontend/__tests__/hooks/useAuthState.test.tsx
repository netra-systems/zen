/**
 * useAuthState Hook Tests - Revenue-Critical Auth State Management
 * 
 * BVJ: Free→Paid conversion depends on accurate auth state and tier detection
 * Tests cover: auth loading, user tiers, permissions, token management, session handling
 * 
 * @compliance testing.xml - Hook testing patterns with 100% coverage
 * @prevents auth-tier-detection-failures regression
 * @prevents session-management-failures regression
 */

import React from 'react';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useAuthState, UserTier } from '@/hooks/useAuthState';
import { useAuthStore } from '@/store/authStore';
import { User } from '@/types/registry';

// Mock the auth store dependency
jest.mock('@/store/authStore', () => ({
  useAuthStore: jest.fn()
}));

// Mock localStorage for token management tests
Object.defineProperty(window, 'localStorage', {
  value: {
    getItem: jest.fn(),
    setItem: jest.fn(),
    removeItem: jest.fn(),
    clear: jest.fn(),
  },
  writable: true,
});

describe('useAuthState Hook - Revenue Critical Auth Management', () => {
  const mockUseAuthStore = useAuthStore as jest.MockedFunction<typeof useAuthStore>;
  const mockLocalStorage = window.localStorage as jest.Mocked<typeof window.localStorage>;

  // Helper: Get permissions by role (≤8 lines)
  const getTestPermissions = (role: string): string[] => {
    if (role === 'admin') return ['manage_users', 'view_analytics'];
    return ['basic_access'];
  };

  // Test user fixtures for different tiers (≤8 lines)
  const createTestUser = (role: string, additionalProps = {}): User => ({
    id: `user_${role}`,
    email: `${role}@netrasystems.ai`,
    full_name: `Test ${role} User`,
    is_active: true,
    is_superuser: role === 'super_admin',
    role,
    permissions: getTestPermissions(role),
    ...additionalProps
  } as any);

  // Helper: Create base auth store state (≤8 lines)
  const createBaseAuthState = () => ({
    setError: jest.fn(),
    logout: jest.fn(),
    hasPermission: jest.fn().mockReturnValue(false),
    isAdminOrHigher: jest.fn().mockReturnValue(false),
    isDeveloperOrHigher: jest.fn().mockReturnValue(false)
  });

  // Helper: Create unauthenticated auth store state (≤8 lines)
  const createUnauthenticatedState = () => ({
    isAuthenticated: false,
    user: null,
    loading: false,
    error: null,
    token: null,
    ...createBaseAuthState()
  });

  // Helper: Create loading auth store state (≤8 lines)
  const createLoadingState = () => ({
    ...createUnauthenticatedState(),
    loading: true
  });

  // Helper: Create authenticated user state (≤8 lines)
  const createAuthenticatedUserState = (user: User, role: string) => ({
    isAuthenticated: true,
    user,
    loading: false,
    error: null,
    token: 'valid_token',
    ...createBaseAuthState(),
    hasPermission: jest.fn().mockReturnValue(true),
    isAdminOrHigher: jest.fn().mockReturnValue(role.includes('admin')),
    isDeveloperOrHigher: jest.fn().mockReturnValue(['developer', 'admin', 'super_admin'].includes(role))
  });

  beforeEach(() => {
    jest.clearAllMocks();
    mockLocalStorage.getItem.mockClear();
    mockLocalStorage.setItem.mockClear();
    mockLocalStorage.removeItem.mockClear();
  });

  /**
   * Test Suite 1: Initial Auth State Loading
   * Critical for user experience and conversion flow
   */
  describe('Initial Auth State Loading', () => {
    // Helper: Assert unauthenticated state (≤8 lines)
    const expectUnauthenticatedState = (state: any) => {
      expect(state.isAuthenticated).toBe(false);
      expect(state.user).toBe(null);
      expect(state.userTier).toBe('Free');
      expect(state.isLoading).toBe(false);
      expect(state.error).toBe(null);
    };

    it('should initialize with unauthenticated state when no user', async () => {
      const mockState = createUnauthenticatedState();
      mockUseAuthStore.mockReturnValue(mockState);
      const { result } = renderHook(() => useAuthState());
      
      expectUnauthenticatedState(result.current);
    });

    // Helper: Assert loading state (≤8 lines)
    const expectLoadingState = (state: any) => {
      expect(state.isLoading).toBe(true);
      expect(state.isAuthenticated).toBe(false);
      expect(state.userTier).toBe('Free');
    };

    it('should show loading state when auth store is loading', async () => {
      const mockState = createLoadingState();
      mockUseAuthStore.mockReturnValue(mockState);
      const { result } = renderHook(() => useAuthState());
      
      expectLoadingState(result.current);
    });

    // Helper: Create authenticated but no user state (≤8 lines)
    const createAuthenticatedNoUserState = () => ({
      ...createUnauthenticatedState(),
      isAuthenticated: true,
      token: 'valid_token'
    });

    // Helper: Assert authenticated but no user state (≤8 lines)
    const expectAuthenticatedNoUserState = (state: any) => {
      expect(state.isLoading).toBe(true);
      expect(state.isAuthenticated).toBe(true);
      expect(state.user).toBe(null);
    };

    it('should show loading when authenticated but user not loaded', async () => {
      const mockState = createAuthenticatedNoUserState();
      mockUseAuthStore.mockReturnValue(mockState);
      const { result } = renderHook(() => useAuthState());
      
      expectAuthenticatedNoUserState(result.current);
    });
  });

  /**
   * Test Suite 2: User Tier Detection - CRITICAL FOR CONVERSION
   * Tests all tier detection logic for Free→Paid conversion flow
   */
  describe('User Tier Detection - Conversion Critical', () => {
    const tierTestCases = [
      { role: 'super_admin', expectedTier: 'Enterprise' as UserTier },
      { role: 'admin', expectedTier: 'Enterprise' as UserTier },
      { role: 'developer', expectedTier: 'Mid' as UserTier },
      { role: 'power_user', expectedTier: 'Early' as UserTier },
      { role: 'standard_user', expectedTier: 'Free' as UserTier },
      { role: 'unknown_role', expectedTier: 'Free' as UserTier }
    ];

    // Helper: Assert user tier state (≤8 lines)
    const expectUserTierState = (state: any, user: User, tier: string) => {
      expect(state.userTier).toBe(tier);
      expect(state.user).toEqual(user);
      expect(state.isAuthenticated).toBe(true);
    };

    tierTestCases.forEach(({ role, expectedTier }) => {
      it(`should detect ${expectedTier} tier for ${role} role`, async () => {
        const testUser = createTestUser(role);
        const mockState = createAuthenticatedUserState(testUser, role);
        mockUseAuthStore.mockReturnValue(mockState);
        
        const { result } = renderHook(() => useAuthState());
        expectUserTierState(result.current, testUser, expectedTier);
      });
    });

    // Helper: Assert free tier state (≤8 lines)
    const expectFreeTierState = (state: any) => {
      expect(state.userTier).toBe('Free');
      expect(state.user).toBe(null);
    };

    it('should default to Free tier when user is null', async () => {
      const mockState = createUnauthenticatedState();
      mockUseAuthStore.mockReturnValue(mockState);
      const { result } = renderHook(() => useAuthState());
      
      expectFreeTierState(result.current);
    });
  });

  /**
   * Test Suite 3: Permission Management - Feature Gating
   * Critical for tier-based feature access control
   */
  describe('Permission Management - Feature Gating', () => {
    // Helper: Create permission function mocks (≤8 lines)
    const createPermissionMocks = () => ({
      hasPermission: jest.fn(),
      isAdminOrHigher: jest.fn(),
      isDeveloperOrHigher: jest.fn()
    });

    // Helper: Create permission test state (≤8 lines)
    const createPermissionTestState = (mocks: any) => ({
      isAuthenticated: true,
      user: createTestUser('developer'),
      loading: false,
      error: null,
      token: 'valid_token',
      setError: jest.fn(),
      logout: jest.fn(),
      ...mocks
    });

    // Helper: Assert permission delegation (≤8 lines)
    const expectPermissionDelegation = (state: any, mocks: any) => {
      expect(typeof state.hasPermission).toBe('function');
      expect(typeof state.isAdminOrHigher).toBe('function');
      expect(typeof state.isDeveloperOrHigher).toBe('function');
      expect(state.hasPermission).toBe(mocks.hasPermission);
      expect(state.isAdminOrHigher).toBe(mocks.isAdminOrHigher);
      expect(state.isDeveloperOrHigher).toBe(mocks.isDeveloperOrHigher);
    };

    it('should delegate permission checks to auth store', async () => {
      const permissionMocks = createPermissionMocks();
      const mockState = createPermissionTestState(permissionMocks);
      mockUseAuthStore.mockReturnValue(mockState);
      
      const { result } = renderHook(() => useAuthState());
      expectPermissionDelegation(result.current, permissionMocks);
    });

    // Helper: Create enterprise permission mock (≤8 lines)
    const createEnterprisePermissionMock = () => {
      return jest.fn().mockImplementation((permission: string) => {
        return permission === 'manage_billing' || permission === 'view_analytics';
      });
    };

    // Helper: Create enterprise user state (≤8 lines)
    const createEnterpriseUserState = (hasPermission: any) => ({
      isAuthenticated: true,
      user: createTestUser('admin'),
      loading: false,
      error: null,
      token: 'valid_token',
      setError: jest.fn(),
      logout: jest.fn(),
      hasPermission,
      isAdminOrHigher: jest.fn().mockReturnValue(true),
      isDeveloperOrHigher: jest.fn().mockReturnValue(true)
    });

    // Helper: Assert enterprise permissions (≤8 lines)
    const expectEnterprisePermissions = (state: any) => {
      expect(state.hasPermission('manage_billing')).toBe(true);
      expect(state.hasPermission('view_analytics')).toBe(true);
      expect(state.hasPermission('unknown_permission')).toBe(false);
      expect(state.userTier).toBe('Enterprise');
    };

    it('should handle permission checks for enterprise features', async () => {
      const mockHasPermission = createEnterprisePermissionMock();
      const mockState = createEnterpriseUserState(mockHasPermission);
      mockUseAuthStore.mockReturnValue(mockState);
      
      const { result } = renderHook(() => useAuthState());
      expectEnterprisePermissions(result.current);
    });
  });

  /**
   * Test Suite 4: Error Handling - User-Friendly Messages
   * Critical for maintaining user trust during auth issues
   */
  describe('Error Handling - User Experience', () => {
    const errorTestCases = [
      { storeError: 'network_timeout', expectedError: 'Connection issue. Please try again.' },
      { storeError: 'invalid_token', expectedError: 'Session expired. Please log in again.' },
      { storeError: 'token_expired', expectedError: 'Session expired. Please log in again.' },
      { storeError: 'unknown_error', expectedError: 'Authentication error. Please try again.' },
      { storeError: null, expectedError: null }
    ];

    // Helper: Create error state (≤8 lines)
    const createErrorState = (error: string | null) => ({
      ...createUnauthenticatedState(),
      error
    });

    // Helper: Assert error transformation (≤8 lines)
    const expectErrorTransformation = (state: any, expectedError: string | null) => {
      expect(state.error).toBe(expectedError);
    };

    errorTestCases.forEach(({ storeError, expectedError }) => {
      it(`should transform ${storeError || 'no error'} to user-friendly message`, async () => {
        const mockState = createErrorState(storeError);
        mockUseAuthStore.mockReturnValue(mockState);
        const { result } = renderHook(() => useAuthState());
        
        expectErrorTransformation(result.current, expectedError);
      });
    });

    // Helper: Create clear error test state (≤8 lines)
    const createClearErrorTestState = (setError: any) => ({
      ...createUnauthenticatedState(),
      error: 'test_error',
      setError
    });

    // Helper: Test clear error functionality (≤8 lines)
    const testClearError = (state: any, mockSetError: any) => {
      act(() => {
        state.clearError();
      });
      expect(mockSetError).toHaveBeenCalledWith(null);
    };

    it('should provide clearError function', async () => {
      const mockSetError = jest.fn();
      const mockState = createClearErrorTestState(mockSetError);
      mockUseAuthStore.mockReturnValue(mockState);
      
      const { result } = renderHook(() => useAuthState());
      testClearError(result.current, mockSetError);
    });
  });

  /**
   * Test Suite 5: Session Management - Token Refresh
   * Critical for maintaining authenticated sessions
   */
  describe('Session Management - Token Refresh', () => {
    // Helper: Setup token refresh test (≤8 lines)
    const setupTokenRefreshTest = () => {
      mockLocalStorage.getItem.mockReturnValue('existing_jwt_token');
    };

    // Helper: Create token refresh state (≤8 lines)
    const createTokenRefreshState = () => ({
      isAuthenticated: true,
      user: createTestUser('power_user'),
      loading: false,
      error: null,
      token: 'existing_jwt_token',
      ...createBaseAuthState(),
      hasPermission: jest.fn().mockReturnValue(true)
    });

    // Helper: Test token refresh (≤8 lines)
    const testTokenRefresh = async (state: any) => {
      await act(async () => {
        await state.refreshAuth();
      });
      expect(mockLocalStorage.getItem).toHaveBeenCalledWith('jwt_token');
    };

    it('should handle refreshAuth with existing token', async () => {
      setupTokenRefreshTest();
      const mockState = createTokenRefreshState();
      mockUseAuthStore.mockReturnValue(mockState);
      
      const { result } = renderHook(() => useAuthState());
      await testTokenRefresh(result.current);
    });

    // Helper: Setup no token test (≤8 lines)
    const setupNoTokenTest = () => {
      mockLocalStorage.getItem.mockReturnValue(null);
    };

    // Helper: Test refresh without token (≤8 lines)
    const testRefreshWithoutToken = async (state: any) => {
      await act(async () => {
        await state.refreshAuth();
      });
      expect(state.isAuthenticated).toBe(false);
    };

    it('should handle refreshAuth without token gracefully', async () => {
      setupNoTokenTest();
      const mockState = createUnauthenticatedState();
      mockUseAuthStore.mockReturnValue(mockState);
      
      const { result } = renderHook(() => useAuthState());
      await testRefreshWithoutToken(result.current);
    });
  });

  /**
   * Test Suite 6: Logout and Cleanup - Session Termination
   * Critical for security and clean session management
   */
  describe('Logout and Cleanup', () => {
    // Helper: Create logout test state (≤8 lines)
    const createLogoutTestState = (logout: any) => ({
      isAuthenticated: true,
      user: createTestUser('standard_user'),
      loading: false,
      error: null,
      token: 'active_token',
      ...createBaseAuthState(),
      logout,
      hasPermission: jest.fn().mockReturnValue(true)
    });

    // Helper: Test logout cleanup (≤8 lines)
    const testLogoutCleanup = (state: any, mockLogout: any) => {
      act(() => {
        state.logout();
      });
      expect(mockLogout).toHaveBeenCalled();
    };

    it('should handle logout with cleanup', async () => {
      const mockLogout = jest.fn();
      const mockState = createLogoutTestState(mockLogout);
      mockUseAuthStore.mockReturnValue(mockState);
      
      const { result } = renderHook(() => useAuthState());
      testLogoutCleanup(result.current, mockLogout);
    });
  });
});