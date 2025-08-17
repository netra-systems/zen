import React from 'react';
import { AuthContext } from '@/auth/context';
import { WebSocketContext } from '@/providers/WebSocketProvider';

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
  sendMessage: jest.fn()
};

// Use the real WebSocketContext to avoid context mismatches
export const MockWebSocketProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <WebSocketContext.Provider value={mockWebSocketContextValue}>
      {children}
    </WebSocketContext.Provider>
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