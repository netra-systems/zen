import React from 'react';
import { AuthContext, AuthContextType } from '@/auth/context';
import { MockWebSocketProvider } from '../../__mocks__/mock-websocket-provider';
import { User } from '@/types';

// Mock user object
const mockUser: User = {
  id: 'test-user',
  email: 'test@example.com',
  full_name: 'Test User',
  name: 'Test User'
};

// Mock auth context value matching AuthContextType
const mockAuthContextValue: AuthContextType = {
  token: 'test-token-123',
  user: mockUser,
  login: jest.fn(),
  logout: jest.fn(),
  loading: false,
  authConfig: null
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