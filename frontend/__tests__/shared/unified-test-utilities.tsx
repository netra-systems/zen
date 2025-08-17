/**
 * Unified Test Utilities - Central utilities for consistent test setup
 * Addresses common patterns affecting multiple tests
 * Keeps functions ≤8 lines for maintainability
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import { AuthContext } from '@/auth/context';
import { WebSocketContext } from '@/providers/WebSocketProvider';

// Standard mock values for consistent testing
export const mockAuthValue = {
  token: 'test-token-123',
  user: { id: 'test-user', email: 'test@example.com', name: 'Test User' },
  isAuthenticated: true,
  login: jest.fn(),
  logout: jest.fn(),
  refreshToken: jest.fn()
};

export const mockWebSocketValue = {
  status: 'OPEN' as const,
  messages: [],
  sendMessage: jest.fn()
};

// Unified test wrapper with proper context providers
export const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <AuthContext.Provider value={mockAuthValue}>
    <WebSocketContext.Provider value={mockWebSocketValue}>
      {children}
    </WebSocketContext.Provider>
  </AuthContext.Provider>
);

// Safe render function with proper act wrapping
export const renderWithProviders = (component: React.ReactElement) => {
  let result: ReturnType<typeof render>;
  act(() => {
    result = render(component, { wrapper: TestWrapper });
  });
  return result!;
};

// Wait for element with timeout and proper error handling
export const waitForElement = async (testId: string, timeout = 5000) => {
  return await waitFor(() => screen.getByTestId(testId), { timeout });
};

// Safe async interaction wrapper
export const safeAsync = async (action: () => Promise<void> | void) => {
  await act(async () => {
    await action();
  });
};

// Mock cleanup helper for consistent state between tests
export const resetAllMocks = () => {
  jest.clearAllMocks();
  localStorage.clear();
  sessionStorage.clear();
};

// DOM assertion helper with better error messages
export const assertElementExists = (testId: string) => {
  const element = screen.queryByTestId(testId);
  if (!element) throw new Error(`Element with testId "${testId}" not found`);
  return element;
};