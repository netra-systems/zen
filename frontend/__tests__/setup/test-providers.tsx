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

// Mock WebSocket context value
export const mockWebSocketContextValue = {
  sendMessage: jest.fn(),
  connect: jest.fn(),
  disconnect: jest.fn(),
  isConnected: true,
  connectionState: 'connected' as const,
  error: null,
  lastMessage: null,
  reconnectAttempts: 0,
  messageQueue: [],
  status: 'OPEN' as const,
  messages: []
};

// Create a mock WebSocketProvider that doesn't actually connect
export const MockWebSocketProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const WebSocketContext = React.createContext(mockWebSocketContextValue);
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