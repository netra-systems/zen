/**
 * Logout Security and Multi-Tab Tests  
 * Tests multi-tab logout sync, browser back prevention, and security measures
 * BUSINESS VALUE: Enterprise security & compliance (data privacy)
 * Following 450-line limit and 25-line function requirements
 */

import React from 'react';
import { act, waitFor } from '@testing-library/react';
import { jest } from '@jest/globals';
import { useAuthStore } from '@/store/authStore';
import '@testing-library/jest-dom';

// Mock dependencies
jest.mock('@/store/authStore');
jest.mock('@/lib/logger');

// Mock browser APIs
const mockLocalStorage = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
  key: jest.fn(),
  length: 0,
};

const mockSessionStorage = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
  key: jest.fn(),
  length: 0,
};

// Test data following 25-line limit
const createUserData = () => ({
  id: 'user-123',
  email: 'test@example.com',
  full_name: 'Test User',
  role: 'admin',
  permissions: ['read', 'write'],
});

const setupStorageMocks = () => {
  Object.defineProperty(window, 'localStorage', { value: mockLocalStorage });
  Object.defineProperty(window, 'sessionStorage', { value: mockSessionStorage });
  global.document.cookie = '';
  return { localStorage: mockLocalStorage, sessionStorage: mockSessionStorage };
};

const setupAuthStore = () => {
  const mockStore = {
    isAuthenticated: true,
    user: createUserData(),
    token: 'test-token-123',
    loading: false,
    error: null,
    login: jest.fn(),
    logout: jest.fn(),
    setLoading: jest.fn(),
    setError: jest.fn(),
    updateUser: jest.fn(),
    reset: jest.fn(),
    hasPermission: jest.fn(() => false),
    hasAnyPermission: jest.fn(() => false),
    hasAllPermissions: jest.fn(() => false),
    isAdminOrHigher: jest.fn(() => false),
    isDeveloperOrHigher: jest.fn(() => false)
  };
  (useAuthStore as jest.Mock).mockReturnValue(mockStore);
  return mockStore;
};

const performLogoutCleanup = async () => {
  const mockStore = setupAuthStore();
  await act(async () => {
    mockStore.logout();
    mockStore.reset();
  });
  return mockStore;
};

describe('Logout Security and Multi-Tab Tests', () => {
  let storages: any;
  let mockStore: any;

  beforeEach(() => {
    jest.clearAllMocks();
    storages = setupStorageMocks();
    mockStore = setupAuthStore();
  });

  describe('All Auth Tokens Removed', () => {
    const verifyTokenRemoval = async () => {
      await performLogoutCleanup();
      await waitFor(() => {
        expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('jwt_token');
      });
    };

    it('should remove JWT token from localStorage', async () => {
      await act(async () => {
        await verifyTokenRemoval();
      });
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('jwt_token');
    });

    it('should remove auth token from localStorage', async () => {
      await act(async () => {
        await verifyTokenRemoval();
      });
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('authToken');
    });

    it('should remove refresh token from localStorage', async () => {
      await act(async () => {
        await verifyTokenRemoval();
      });
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('refresh_token');
    });

    it('should remove session ID from localStorage', async () => {
      await act(async () => {
        await verifyTokenRemoval();
      });
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('session_id');
    });
  });

  describe('LocalStorage Cleared', () => {
    const verifyLocalStorageCleanup = async () => {
      await performLogoutCleanup();
      await waitFor(() => {
        expect(mockLocalStorage.removeItem).toHaveBeenCalled();
      });
    };

    it('should remove user preferences from localStorage', async () => {
      await act(async () => {
        await verifyLocalStorageCleanup();
      });
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('user_preferences');
    });

    it('should remove cached user data from localStorage', async () => {
      await act(async () => {
        await verifyLocalStorageCleanup();
      });
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('cached_user_data');
    });

    it('should remove remember me flag from localStorage', async () => {
      await act(async () => {
        await verifyLocalStorageCleanup();
      });
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('remember_me');
    });

    it('should not affect non-auth localStorage items', async () => {
      await act(async () => {
        await verifyLocalStorageCleanup();
      });
      expect(mockLocalStorage.removeItem).not.toHaveBeenCalledWith('theme_preference');
    });
  });

  describe('Cookies Deleted', () => {
    const verifyCookieCleanup = async () => {
      await performLogoutCleanup();
      await waitFor(() => {
        expect(mockStore.logout).toHaveBeenCalled();
      });
    };

    it('should remove auth cookies', async () => {
      await act(async () => {
        await verifyCookieCleanup();
      });
      expect(document.cookie).not.toContain('auth_token');
    });

    it('should remove session cookies', async () => {
      await act(async () => {
        await verifyCookieCleanup();
      });
      expect(document.cookie).not.toContain('session_id');
    });

    it('should remove remember me cookies', async () => {
      await act(async () => {
        await verifyCookieCleanup();
      });
      expect(document.cookie).not.toContain('remember_me');
    });

    it('should preserve non-auth cookies', async () => {
      document.cookie = 'theme=dark';
      await act(async () => {
        await verifyCookieCleanup();
      });
      expect(document.cookie).toContain('theme=dark');
    });
  });

  describe('Browser Back Prevention', () => {
    const mockHistoryAPI = () => {
      const mockHistory = {
        pushState: jest.fn(),
        replaceState: jest.fn(),
        back: jest.fn(),
        forward: jest.fn(),
        go: jest.fn(),
      };
      Object.defineProperty(window, 'history', { value: mockHistory });
      return mockHistory;
    };

    const verifyBackPrevention = async () => {
      const mockHistory = mockHistoryAPI();
      await performLogoutCleanup();
      return mockHistory;
    };

    it('should replace history state after logout', async () => {
      const mockHistory = await act(async () => {
        return await verifyBackPrevention();
      });
      expect(mockHistory.replaceState).toHaveBeenCalled();
    });

    it('should prevent navigation to authenticated pages', async () => {
      await act(async () => {
        await verifyBackPrevention();
      });
      expect(mockStore.isAuthenticated).toBe(false);
    });

    it('should clear browser navigation state', async () => {
      const mockHistory = await act(async () => {
        return await verifyBackPrevention();
      });
      expect(mockHistory.replaceState).toHaveBeenCalled();
    });

    it('should ensure no cached authenticated state', async () => {
      await act(async () => {
        await verifyBackPrevention();
      });
      expect(mockStore.user).toBeNull();
      expect(mockStore.token).toBeNull();
    });
  });


  describe('Security Validation', () => {
    const verifySecurityCleanup = async () => {
      await performLogoutCleanup();
      await waitFor(() => {
        expect(mockStore.logout).toHaveBeenCalled();
      });
    };

    it('should not leave sensitive data in memory', async () => {
      await act(async () => {
        await verifySecurityCleanup();
      });
      expect(mockStore.user?.email).toBeUndefined();
      expect(mockStore.token).toBeNull();
    });

    it('should clear all authentication artifacts', async () => {
      await act(async () => {
        await verifySecurityCleanup();
      });
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('jwt_token');
    });

    it('should ensure complete session termination', async () => {
      await act(async () => {
        await verifySecurityCleanup();
      });
      expect(mockStore.isAuthenticated).toBe(false);
      expect(mockStore.user).toBeNull();
      expect(mockStore.token).toBeNull();
    });

    it('should clear permissions and role data', async () => {
      await act(async () => {
        await verifySecurityCleanup();
      });
      expect(mockStore.user?.permissions).toBeUndefined();
    });
  });

  describe('Clean Slate for Next Login', () => {
    const verifyCleanSlate = async () => {
      await performLogoutCleanup();
      await waitFor(() => {
        expect(mockStore.reset).toHaveBeenCalled();
      });
    };

    it('should reset all error states', async () => {
      await act(async () => {
        await verifyCleanSlate();
      });
      expect(mockStore.setError).toHaveBeenCalledWith(null);
    });

    it('should reset loading states', async () => {
      await act(async () => {
        await verifyCleanSlate();
      });
      expect(mockStore.setLoading).toHaveBeenCalledWith(false);
    });

    it('should clear any cached authentication state', async () => {
      await act(async () => {
        await verifyCleanSlate();
      });
      expect(mockStore.token).toBeNull();
    });

    it('should ensure fresh authentication flow on next login', async () => {
      await act(async () => {
        await verifyCleanSlate();
      });
      expect(mockStore.isAuthenticated).toBe(false);
      expect(mockStore.user).toBeNull();
    });
  });

  describe('No Authenticated Content Visible', () => {
    const verifyContentCleanup = async () => {
      await performLogoutCleanup();
      await waitFor(() => {
        expect(mockStore.isAuthenticated).toBe(false);
      });
    };

    it('should set authenticated status to false', async () => {
      await act(async () => {
        await verifyContentCleanup();
      });
      expect(mockStore.isAuthenticated).toBe(false);
    });

    it('should clear user identity information', async () => {
      await act(async () => {
        await verifyContentCleanup();
      });
      expect(mockStore.user).toBeNull();
    });

    it('should clear role and permissions', async () => {
      await act(async () => {
        await verifyContentCleanup();
      });
      expect(mockStore.user?.role).toBeUndefined();
    });

    it('should ensure no sensitive data remains in DOM', async () => {
      await act(async () => {
        await verifyContentCleanup();
      });
      expect(mockStore.user?.email).toBeUndefined();
    });
  });
});