import React from 'react';
import { AuthContext } from '@/auth/context';

// Mock auth context value
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
 * Test wrapper that provides both Auth and mocked WebSocket contexts
 */
export const TestProviders: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <AuthContext.Provider value={mockAuthContextValue}>
      <MockWebSocketProvider>{children}</MockWebSocketProvider>
    </AuthContext.Provider>
  );
};

/**
 * Test wrapper that provides only Auth context
 */
export const AuthTestProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <AuthContext.Provider value={mockAuthContextValue}>
      {children}
    </AuthContext.Provider>
  );
};