/**
 * Mock implementation for Zustand auth store
 * Provides proper mock functions for testing
 */

import { jest } from '@jest/globals';

// Create a mock store factory
const createMockAuthStore = () => ({
  isAuthenticated: false,
  user: null,
  token: null,
  loading: false,
  error: null,
  login: jest.fn(),
  logout: jest.fn(),
  setLoading: jest.fn(),
  setError: jest.fn(),
  setUser: jest.fn(),
  setToken: jest.fn(),
  clearError: jest.fn(),
  updateUser: jest.fn(),
  reset: jest.fn(),
  hasPermission: jest.fn(() => false),
  hasAnyPermission: jest.fn(() => false),
  hasAllPermissions: jest.fn(() => false),
  isAdminOrHigher: jest.fn(() => false),
  isDeveloper: jest.fn(() => false),
});

// Export the mock hook that returns the store
export const useAuthStore = jest.fn(createMockAuthStore);

// Export helper to reset the mock
export const resetAuthStoreMock = () => {
  useAuthStore.mockClear();
  useAuthStore.mockImplementation(createMockAuthStore);
};

// Export helper to configure the mock
export const configureAuthStoreMock = (overrides: Partial<ReturnType<typeof createMockAuthStore>>) => {
  useAuthStore.mockImplementation(() => ({
    ...createMockAuthStore(),
    ...overrides,
  }));
};