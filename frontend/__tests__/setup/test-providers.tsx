import React from 'react';

// Mock auth context value (maintain compatibility with old context-based tests)
export const mockAuthContextValue = {
  token: 'test-token-123',
  user: {
    id: 'test-user',
    email: 'test@example.com',
    name: 'Test User'
  },
  isAuthenticated: true,
  login: jest.fn(),
  logout: jest.fn(),
  refreshToken: jest.fn()
};

// Mock WebSocket context value (aligned with actual interface)
export const mockWebSocketContextValue = {
  status: 'OPEN' as const,
  messages: [],
  sendMessage: jest.fn(),
  sendOptimisticMessage: jest.fn(),
  reconciliationStats: { optimisticCount: 0, confirmedCount: 0, rejectedCount: 0 }
};

// Create a mock WebSocket context
const MockWebSocketContext = React.createContext(mockWebSocketContextValue);

// Mock WebSocket provider
export const MockWebSocketProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <MockWebSocketContext.Provider value={mockWebSocketContextValue}>
      {children}
    </MockWebSocketContext.Provider>
  );
};

/**
 * Test wrapper that provides mocked WebSocket contexts for Zustand-based tests
 * Auth is handled via Zustand store mocks in individual tests
 */
export const TestProviders: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <MockWebSocketProvider>{children}</MockWebSocketProvider>
  );
};

/**
 * Test wrapper that provides legacy auth context (for backward compatibility)
 */
export const AuthTestProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  try {
    // Try to use AuthContext if it exists (legacy support)
    const { AuthContext } = require('@/auth/context');
    return (
      <AuthContext.Provider value={mockAuthContextValue}>
        {children}
      </AuthContext.Provider>
    );
  } catch {
    // Fallback to just children if AuthContext doesn't exist
    return <>{children}</>;
  }
};