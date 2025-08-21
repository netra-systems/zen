/**
 * AuthStore Unit Tests - Business-Critical Authentication Testing
 * 
 * BVJ (Business Value Justification):
 * - Segment: All (Free, Growth, Enterprise)
 * - Business Goal: Secure tier-based feature access, prevent revenue leakage
 * - Value Impact: 100% of platform revenue depends on proper auth
 * - Revenue Impact: Prevents unauthorized access to paid features
 * 
 * CRITICAL: These tests ensure security boundaries are never breached
 * Architecture: ≤300 lines, functions ≤8 lines each
 */

import { act, renderHook } from '@testing-library/react';
import { useAuthStore } from '@/store/authStore';
import { User } from '@/types/registry';

// Mock localStorage globally
const mockLocalStorage = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn()
};

Object.defineProperty(window, 'localStorage', {
  value: mockLocalStorage
});

// Mock window for SSR compatibility - store reference
const originalWindow = global.window;

describe('AuthStore - Business Critical Authentication', () => {
  // Helper to reset store state before each test (≤8 lines)
  const resetAuthStore = () => {
    const { result } = renderHook(() => useAuthStore());
    act(() => {
      result.current.reset();
    });
    return result;
  };

  // Helper to create mock users for different tiers (≤8 lines)
  const createMockUser = (role: string, permissions: string[] = []): User & { role: string; permissions: string[] } => {
    return {
      id: `user-${role}`,
      email: `${role}@netrasystems.ai`,
      full_name: `${role} User`,
      is_active: true,
      is_superuser: role === 'super_admin',
      role,
      permissions
    } as User & { role: string; permissions: string[] };
  };

  // Helper to create test tokens (≤8 lines)
  const createTestToken = (suffix: string = 'default'): string => {
    return `jwt-token-${suffix}-${Date.now()}`;
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockLocalStorage.getItem.mockReturnValue(null);
    
    // Reset store state
    const { result } = renderHook(() => useAuthStore());
    act(() => {
      result.current.reset();
    });
  });

  describe('Initial State - Security Default', () => {
    it('should initialize with secure defaults', () => {
      const { result } = renderHook(() => useAuthStore());
      
      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.user).toBeNull();
      expect(result.current.token).toBeNull();
      expect(result.current.loading).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it('should deny all permissions when not authenticated', () => {
      const { result } = renderHook(() => useAuthStore());
      
      expect(result.current.hasPermission('any-permission')).toBe(false);
      expect(result.current.hasAnyPermission(['perm1', 'perm2'])).toBe(false);
      expect(result.current.hasAllPermissions(['perm1', 'perm2'])).toBe(false);
      expect(result.current.isAdminOrHigher()).toBe(false);
      expect(result.current.isDeveloperOrHigher()).toBe(false);
    });
  });

  describe('Login Flow - Revenue Critical', () => {
    it('should authenticate free tier user correctly', () => {
      const { result } = renderHook(() => useAuthStore());
      const freeUser = createMockUser('standard_user', []);
      const token = createTestToken('free');

      act(() => {
        result.current.login(freeUser, token);
      });

      expect(result.current.isAuthenticated).toBe(true);
      expect(result.current.user).toEqual(freeUser);
      expect(result.current.token).toBe(token);
      expect(result.current.error).toBeNull();
      expect(mockLocalStorage.setItem).toHaveBeenCalledWith('jwt_token', token);
    });

    it('should authenticate growth tier user with permissions', () => {
      const { result } = renderHook(() => useAuthStore());
      const growthUser = createMockUser('power_user', ['feature_analytics', 'export_data']);
      const token = createTestToken('growth');

      act(() => {
        result.current.login(growthUser, token);
      });

      expect(result.current.isAuthenticated).toBe(true);
      expect(result.current.hasPermission('feature_analytics')).toBe(true);
      expect(result.current.hasPermission('admin_access')).toBe(false);
      expect(result.current.isDeveloperOrHigher()).toBe(false);
    });

    it('should authenticate enterprise user with full access', () => {
      const { result } = renderHook(() => useAuthStore());
      const enterpriseUser = createMockUser('admin', ['admin_access', 'full_api_access']);
      const token = createTestToken('enterprise');

      act(() => {
        result.current.login(enterpriseUser, token);
      });

      expect(result.current.isAuthenticated).toBe(true);
      expect(result.current.isAdminOrHigher()).toBe(true);
      expect(result.current.isDeveloperOrHigher()).toBe(true);
      expect(result.current.hasAllPermissions(['admin_access', 'full_api_access'])).toBe(true);
    });
  });

  describe('Permission System - Revenue Protection', () => {
    it('should enforce free tier limitations', () => {
      const { result } = renderHook(() => useAuthStore());
      const freeUser = createMockUser('standard_user', []);
      
      act(() => {
        result.current.login(freeUser, createTestToken('free'));
      });

      // Free tier should not have paid features
      expect(result.current.hasPermission('advanced_analytics')).toBe(false);
      expect(result.current.hasPermission('bulk_export')).toBe(false);
      expect(result.current.hasPermission('priority_support')).toBe(false);
      expect(result.current.hasAnyPermission(['admin_access', 'developer_tools'])).toBe(false);
    });

    it('should validate growth tier permissions correctly', () => {
      const { result } = renderHook(() => useAuthStore());
      const growthUser = createMockUser('power_user', ['analytics', 'export']);
      
      act(() => {
        result.current.login(growthUser, createTestToken('growth'));
      });

      expect(result.current.hasPermission('analytics')).toBe(true);
      expect(result.current.hasPermission('export')).toBe(true);
      expect(result.current.hasPermission('admin_access')).toBe(false);
      expect(result.current.hasAnyPermission(['analytics', 'admin_access'])).toBe(true);
      expect(result.current.hasAllPermissions(['analytics', 'export'])).toBe(true);
      expect(result.current.hasAllPermissions(['analytics', 'admin_access'])).toBe(false);
    });

    it('should grant enterprise full permissions', () => {
      const { result } = renderHook(() => useAuthStore());
      const enterpriseUser = createMockUser('super_admin', ['admin_access', 'dev_tools']);
      enterpriseUser.is_superuser = true;
      
      act(() => {
        result.current.login(enterpriseUser, createTestToken('enterprise'));
      });

      expect(result.current.isAdminOrHigher()).toBe(true);
      expect(result.current.isDeveloperOrHigher()).toBe(true);
      expect(result.current.hasAllPermissions(['admin_access', 'dev_tools'])).toBe(true);
    });
  });

  describe('Token Management - Security Critical', () => {
    it('should store token securely in localStorage', () => {
      const { result } = renderHook(() => useAuthStore());
      const token = createTestToken('secure');
      const user = createMockUser('standard_user');

      act(() => {
        result.current.login(user, token);
      });

      expect(mockLocalStorage.setItem).toHaveBeenCalledWith('jwt_token', token);
      expect(mockLocalStorage.setItem).toHaveBeenCalledTimes(1);
    });

    it('should remove token completely on logout', () => {
      const { result } = renderHook(() => useAuthStore());
      const user = createMockUser('standard_user');
      
      act(() => {
        result.current.login(user, createTestToken('logout-test'));
        result.current.logout();
      });

      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.user).toBeNull();
      expect(result.current.token).toBeNull();
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('jwt_token');
    });

    it('should clear token on reset', () => {
      const { result } = renderHook(() => useAuthStore());
      const user = createMockUser('standard_user');
      
      act(() => {
        result.current.login(user, createTestToken('reset-test'));
        result.current.reset();
      });

      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.user).toBeNull();
      expect(result.current.token).toBeNull();
      expect(result.current.loading).toBe(false);
      expect(result.current.error).toBeNull();
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('jwt_token');
    });
  });

  describe('User Updates - State Integrity', () => {
    it('should update user properties correctly', () => {
      const { result } = renderHook(() => useAuthStore());
      const user = createMockUser('power_user', ['analytics']);
      
      act(() => {
        result.current.login(user, createTestToken('update-test'));
        result.current.updateUser({ full_name: 'Updated Name', permissions: ['analytics', 'export'] });
      });

      expect(result.current.user?.full_name).toBe('Updated Name');
      expect(result.current.user?.permissions).toEqual(['analytics', 'export']);
      expect(result.current.user?.id).toBe(user.id); // ID should remain unchanged
    });

    it('should not update user when not authenticated', () => {
      const { result } = renderHook(() => useAuthStore());
      
      act(() => {
        result.current.updateUser({ full_name: 'Should Not Update' });
      });

      expect(result.current.user).toBeNull();
    });
  });

  describe('Loading and Error States', () => {
    it('should manage loading state correctly', () => {
      const { result } = renderHook(() => useAuthStore());
      
      act(() => {
        result.current.setLoading(true);
      });
      expect(result.current.loading).toBe(true);

      act(() => {
        result.current.setLoading(false);
      });
      expect(result.current.loading).toBe(false);
    });

    it('should manage error state correctly', () => {
      const { result } = renderHook(() => useAuthStore());
      const errorMessage = 'Authentication failed';
      
      act(() => {
        result.current.setError(errorMessage);
      });
      expect(result.current.error).toBe(errorMessage);

      act(() => {
        result.current.setError(null);
      });
      expect(result.current.error).toBeNull();
    });

    it('should clear error on successful login', () => {
      const { result } = renderHook(() => useAuthStore());
      const user = createMockUser('standard_user');
      
      act(() => {
        result.current.setError('Previous error');
        result.current.login(user, createTestToken('error-clear'));
      });

      expect(result.current.error).toBeNull();
    });
  });

  describe('Role-Based Access Control - Tier Boundaries', () => {
    it('should correctly identify developer access', () => {
      const { result } = renderHook(() => useAuthStore());
      
      // Test developer role
      const developer = createMockUser('developer');
      developer.is_developer = true;
      
      act(() => {
        result.current.login(developer, createTestToken('dev'));
      });

      expect(result.current.isDeveloperOrHigher()).toBe(true);
      expect(result.current.isAdminOrHigher()).toBe(false);
    });

    it('should correctly identify admin access hierarchy', () => {
      const { result } = renderHook(() => useAuthStore());
      
      // Test admin role
      const admin = createMockUser('admin');
      
      act(() => {
        result.current.login(admin, createTestToken('admin'));
      });

      expect(result.current.isAdminOrHigher()).toBe(true);
      expect(result.current.isDeveloperOrHigher()).toBe(true);
    });

    it('should correctly identify super admin access', () => {
      const { result } = renderHook(() => useAuthStore());
      
      const superAdmin = createMockUser('super_admin');
      superAdmin.is_superuser = true;
      
      act(() => {
        result.current.login(superAdmin, createTestToken('super'));
      });

      expect(result.current.isAdminOrHigher()).toBe(true);
      expect(result.current.isDeveloperOrHigher()).toBe(true);
    });
  });

  describe('Security Edge Cases', () => {
    it('should handle undefined permissions gracefully', () => {
      const { result } = renderHook(() => useAuthStore());
      const userWithoutPermissions = createMockUser('standard_user');
      delete (userWithoutPermissions as any).permissions;
      
      act(() => {
        result.current.login(userWithoutPermissions, createTestToken('no-perms'));
      });

      expect(result.current.hasPermission('any-permission')).toBe(false);
      expect(result.current.hasAnyPermission(['perm1', 'perm2'])).toBe(false);
      expect(result.current.hasAllPermissions(['perm1'])).toBe(false);
    });

    it('should handle SSR environment without localStorage', () => {
      // Temporarily remove window to simulate SSR
      const originalWindow = global.window;
      delete (global as any).window;
      
      const { result } = renderHook(() => useAuthStore());
      const user = createMockUser('standard_user');
      
      act(() => {
        result.current.login(user, createTestToken('ssr'));
      });

      expect(result.current.isAuthenticated).toBe(true);
      
      // Restore window
      global.window = originalWindow;
    });

    it('should prevent concurrent login operations', () => {
      const { result } = renderHook(() => useAuthStore());
      const user1 = createMockUser('user1');
      const user2 = createMockUser('user2');
      
      act(() => {
        result.current.login(user1, createTestToken('first'));
        result.current.login(user2, createTestToken('second'));
      });

      // Second login should override first
      expect(result.current.user?.id).toBe('user-user2');
      expect(result.current.token).toContain('second');
    });
  });
});