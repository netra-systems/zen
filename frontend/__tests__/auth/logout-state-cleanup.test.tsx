/**
 * Logout State Cleanup Tests  
 * Tests token removal, localStorage cleanup, and memory management
 * BUSINESS VALUE: Security & compliance (enterprise data protection)
 * Following 450-line limit and 25-line function requirements
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { jest } from '@jest/globals';
import '@testing-library/jest-dom';
import { TestProviders } from '../setup/test-providers';
import { useAuthStore } from '@/store/authStore';

// Mock dependencies
jest.mock('@/store/authStore');
jest.mock('@/lib/logger');

// Test helpers following 25-line limit
const createUserData = () => ({
  id: 'user-123',
  email: 'test@example.com',
  full_name: 'Test User',
  role: 'admin',
  permissions: ['read', 'write'],
});

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
  jest.mocked(useAuthStore).mockReturnValue(mockStore);
  return mockStore;
};

const setupLocalStorageMocks = () => {
  const localStorageMock = {
    getItem: jest.fn(),
    setItem: jest.fn(),
    removeItem: jest.fn(),
    clear: jest.fn(),
  };
  Object.defineProperty(window, 'localStorage', { value: localStorageMock });
  return localStorageMock;
};

// Simple logout button component for testing
const LogoutButton: React.FC = () => {
  const { logout } = useAuthStore();
  return (
    <button onClick={logout} data-testid="logout-btn">
      Logout
    </button>
  );
};

const renderLogoutComponent = () => {
  return render(
    <TestProviders>
      <LogoutButton />
    </TestProviders>
  );
};

describe('Logout State Cleanup Tests', () => {
  let mockAuthStore: any;
  let localStorageMock: any;
  
  beforeEach(() => {
    jest.clearAllMocks();
    mockAuthStore = setupAuthStore();
    localStorageMock = setupLocalStorageMocks();
  });

  describe('Token Removal Verification', () => {
    const verifyTokenRemoval = async () => {
      const user = userEvent.setup();
      renderLogoutComponent();
      const logoutBtn = await screen.findByTestId('logout-btn');
      await user.click(logoutBtn);
    };

    it('should remove JWT token from localStorage', async () => {
      await act(async () => {
        await verifyTokenRemoval();
      });
      await waitFor(() => {
        expect(localStorageMock.removeItem).toHaveBeenCalledWith('jwt_token');
      });
    });

    it('should clear auth token from memory', async () => {
      await act(async () => {
        await verifyTokenRemoval();
      });
      await waitFor(() => {
        expect(mockAuthStore.logout).toHaveBeenCalled();
        expect(mockAuthStore.token).toBeNull();
      });
    });

    it('should remove all auth-related localStorage items', async () => {
      await act(async () => {
        await verifyTokenRemoval();
      });
      await waitFor(() => {
        expect(localStorageMock.removeItem).toHaveBeenCalledWith('jwt_token');
        expect(localStorageMock.removeItem).toHaveBeenCalledWith('authToken');
      });
    });

    it('should clear refresh tokens completely', async () => {
      await act(async () => {
        await verifyTokenRemoval();
      });
      await waitFor(() => {
        expect(localStorageMock.removeItem).toHaveBeenCalledWith('refresh_token');
      });
    });
  });

  describe('State Cleanup in Memory', () => {
    const verifyStateCleanup = async () => {
      const user = userEvent.setup();
      renderLogoutComponent();
      const logoutBtn = await screen.findByTestId('logout-btn');
      await user.click(logoutBtn);
    };

    it('should clear user state from auth store', async () => {
      await act(async () => {
        await verifyStateCleanup();
      });
      await waitFor(() => {
        expect(mockAuthStore.logout).toHaveBeenCalled();
      });
    });

    it('should reset authentication status', async () => {
      await act(async () => {
        await verifyStateCleanup();
      });
      await waitFor(() => {
        expect(mockAuthStore.logout).toHaveBeenCalled();
        expect(mockAuthStore.isAuthenticated).toBe(false);
      });
    });

    it('should clear all user data from memory', async () => {
      await act(async () => {
        await verifyStateCleanup();
      });
      await waitFor(() => {
        expect(mockAuthStore.user).toBeNull();
        expect(mockAuthStore.token).toBeNull();
      });
    });

    it('should reset store completely', async () => {
      await act(async () => {
        await verifyStateCleanup();
      });
      await waitFor(() => {
        expect(mockAuthStore.reset).toHaveBeenCalled();
      });
    });
  });

  describe('Memory Leak Prevention', () => {
    const verifyMemoryCleanup = async () => {
      const user = userEvent.setup();
      renderLogoutComponent();
      const logoutBtn = await screen.findByTestId('logout-btn');
      await user.click(logoutBtn);
    };

    it('should reset auth store completely', async () => {
      await act(async () => {
        await verifyMemoryCleanup();
      });
      await waitFor(() => {
        expect(mockAuthStore.reset).toHaveBeenCalled();
      });
    });

    it('should clear user object from memory', async () => {
      await act(async () => {
        await verifyMemoryCleanup();
      });
      await waitFor(() => {
        expect(mockAuthStore.user).toBeNull();
      });
    });

    it('should clear permissions from memory', async () => {
      await act(async () => {
        await verifyMemoryCleanup();
      });
      await waitFor(() => {
        expect(mockAuthStore.user?.permissions).toBeUndefined();
      });
    });

    it('should clear any cached API responses', async () => {
      await act(async () => {
        await verifyMemoryCleanup();
      });
      await waitFor(() => {
        expect(mockAuthStore.reset).toHaveBeenCalled();
      });
    });
  });

  describe('LocalStorage Cleanup', () => {
    const verifyLocalStorageCleanup = async () => {
      const user = userEvent.setup();
      renderLogoutComponent();
      const logoutBtn = await screen.findByTestId('logout-btn');
      await user.click(logoutBtn);
    };

    it('should remove user preferences from localStorage', async () => {
      await act(async () => {
        await verifyLocalStorageCleanup();
      });
      await waitFor(() => {
        expect(localStorageMock.removeItem).toHaveBeenCalledWith('user_preferences');
      });
    });

    it('should remove cached user data from localStorage', async () => {
      await act(async () => {
        await verifyLocalStorageCleanup();
      });
      await waitFor(() => {
        expect(localStorageMock.removeItem).toHaveBeenCalledWith('cached_user_data');
      });
    });

    it('should remove remember me flag from localStorage', async () => {
      await act(async () => {
        await verifyLocalStorageCleanup();
      });
      await waitFor(() => {
        expect(localStorageMock.removeItem).toHaveBeenCalledWith('remember_me');
      });
    });

    it('should not affect non-auth localStorage items', async () => {
      await act(async () => {
        await verifyLocalStorageCleanup();
      });
      await waitFor(() => {
        expect(localStorageMock.removeItem).not.toHaveBeenCalledWith('theme_preference');
      });
    });
  });

  describe('Session Data Cleanup', () => {
    const verifySessionCleanup = async () => {
      const user = userEvent.setup();
      renderLogoutComponent();
      const logoutBtn = await screen.findByTestId('logout-btn');
      await user.click(logoutBtn);
    };

    it('should clear session IDs from storage', async () => {
      await act(async () => {
        await verifySessionCleanup();
      });
      await waitFor(() => {
        expect(localStorageMock.removeItem).toHaveBeenCalledWith('session_id');
      });
    });

    it('should clear all user-specific cached data', async () => {
      await act(async () => {
        await verifySessionCleanup();
      });
      await waitFor(() => {
        expect(mockAuthStore.logout).toHaveBeenCalled();
        expect(mockAuthStore.user).toBeNull();
      });
    });

    it('should ensure complete session cleanup', async () => {
      await act(async () => {
        await verifySessionCleanup();
      });
      await waitFor(() => {
        expect(mockAuthStore.reset).toHaveBeenCalled();
      });
    });

    it('should clear permissions and role data', async () => {
      await act(async () => {
        await verifySessionCleanup();
      });
      await waitFor(() => {
        expect(mockAuthStore.user?.role).toBeUndefined();
      });
    });
  });

  describe('Cleanup Performance', () => {
    const measureCleanupTime = async () => {
      const startTime = performance.now();
      const user = userEvent.setup();
      renderLogoutComponent();
      const logoutBtn = await screen.findByTestId('logout-btn');
      await user.click(logoutBtn);
      await waitFor(() => {
        expect(mockAuthStore.logout).toHaveBeenCalled();
      });
      const endTime = performance.now();
      return endTime - startTime;
    };

    it('should complete cleanup within 100ms', async () => {
      const cleanupTime = await act(async () => {
        return await measureCleanupTime();
      });
      expect(cleanupTime).toBeLessThan(100);
    });

    it('should not block UI during cleanup', async () => {
      const cleanupTime = await act(async () => {
        return await measureCleanupTime();
      });
      expect(cleanupTime).toBeLessThan(50);
    });

    it('should clear localStorage efficiently', async () => {
      await act(async () => {
        const user = userEvent.setup();
        renderLogoutComponent();
        const logoutBtn = await screen.findByTestId('logout-btn');
        const startTime = performance.now();
        await user.click(logoutBtn);
        await waitFor(() => {
          expect(localStorageMock.removeItem).toHaveBeenCalled();
          const endTime = performance.now();
          expect(endTime - startTime).toBeLessThan(25);
        });
      });
    });

    it('should complete memory cleanup quickly', async () => {
      await act(async () => {
        const user = userEvent.setup();
        renderLogoutComponent();
        const logoutBtn = await screen.findByTestId('logout-btn');
        const startTime = performance.now();
        await user.click(logoutBtn);
        await waitFor(() => {
          expect(mockAuthStore.reset).toHaveBeenCalled();
          const endTime = performance.now();
          expect(endTime - startTime).toBeLessThan(30);
        });
      });
    });
  });
});