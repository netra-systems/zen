import React from 'react';
import { AuthContext, AuthContextType } from '@/auth/context';
import { User } from '@/types';

// Mock user object
const mockUser: User = {
  id: 'test-user',
  email: 'test@example.com',
  full_name: 'Test User',
  name: 'Test User'
};

// Mock auth context value matching AuthContextType
export const mockAuthContextValue: AuthContextType = {
  token: 'test-token-123',
  user: mockUser,
  login: jest.fn(),
  logout: jest.fn(),
  loading: false,
  authConfig: null
};

// Mock WebSocket context value
export const mockWebSocketContextValue = {
  status: 'OPEN' as const,
  messages: [],
  sendMessage: jest.fn(),
  connect: jest.fn(),
  disconnect: jest.fn(),
  isConnected: true,
  connectionState: 'connected' as const,
  error: null,
  lastMessage: null,
  reconnectAttempts: 0,
  messageQueue: [],
  ws: null,
  subscribe: jest.fn(),
  unsubscribe: jest.fn(),
};

// Create WebSocketContext here to ensure consistency
export const WebSocketContext = React.createContext(mockWebSocketContextValue);

// Mock WebSocketProvider that uses the same context
export const MockWebSocketProvider: React.FC<{ 
  children: React.ReactNode;
  value?: any;
}> = ({ children, value }) => {
  return (
    <WebSocketContext.Provider value={value || mockWebSocketContextValue}>
      {children}
    </WebSocketContext.Provider>
  );
};

// Mock Agent context for components that need it
export const mockAgentContextValue = {
  currentAgent: null,
  agents: [],
  selectAgent: jest.fn(),
  executeAgent: jest.fn(),
  isExecuting: false,
  agentResults: {},
  agentErrors: {},
};

export const AgentContext = React.createContext(mockAgentContextValue);

export const MockAgentProvider: React.FC<{ 
  children: React.ReactNode;
  value?: any;
}> = ({ children, value }) => {
  return (
    <AgentContext.Provider value={value || mockAgentContextValue}>
      {children}
    </AgentContext.Provider>
  );
};

/**
 * Test wrapper that provides all required contexts
 * Uses mock providers to avoid actual connections in tests
 */
export const TestProviders: React.FC<{ 
  children: React.ReactNode;
  authValue?: Partial<AuthContextType>;
  wsValue?: any;
  agentValue?: any;
}> = ({ children, authValue, wsValue, agentValue }) => {
  const finalAuthValue = { ...mockAuthContextValue, ...authValue };
  const finalWsValue = { ...mockWebSocketContextValue, ...wsValue };
  const finalAgentValue = { ...mockAgentContextValue, ...agentValue };
  
  return (
    <AuthContext.Provider value={finalAuthValue}>
      <MockWebSocketProvider value={finalWsValue}>
        <MockAgentProvider value={finalAgentValue}>
          {children}
        </MockAgentProvider>
      </MockWebSocketProvider>
    </AuthContext.Provider>
  );
};

/**
 * Test wrapper that provides only Auth context
 */
export const AuthTestProvider: React.FC<{ 
  children: React.ReactNode;
  value?: Partial<AuthContextType>;
}> = ({ children, value }) => {
  const finalValue = { ...mockAuthContextValue, ...value };
  return (
    <AuthContext.Provider value={finalValue}>
      {children}
    </AuthContext.Provider>
  );
};

/**
 * Test wrapper that provides only WebSocket context
 */
export const WebSocketTestProvider: React.FC<{ 
  children: React.ReactNode;
  value?: any;
}> = ({ children, value }) => {
  const finalValue = { ...mockWebSocketContextValue, ...value };
  return (
    <MockWebSocketProvider value={finalValue}>
      {children}
    </MockWebSocketProvider>
  );
};