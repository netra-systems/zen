import React from 'react';
import { AuthContext } from '@/auth/context';
import { MockWebSocketProvider } from '../../__mocks__/mock-websocket-provider';

// Mock auth context value
const mockAuthContextValue = {
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

/**
 * Test wrapper that provides both Auth and WebSocket contexts
 * Uses MockWebSocketProvider to avoid actual WebSocket connections in tests
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

export { mockAuthContextValue };