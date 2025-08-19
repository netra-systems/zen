/**
 * Shared test setup for all chat component tests
 * Provides comprehensive mocking and test utilities
 */
import React from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { jest } from '@jest/globals';

// Authentication Context Mock
export const mockAuthContext = {
  token: 'test-token-123',
  user: {
    id: 'test-user',
    email: 'test@example.com',
    full_name: 'Test User',
    name: 'Test User'
  },
  login: jest.fn(),
  logout: jest.fn(),
  loading: false,
  authConfig: null
};

// WebSocket Mock
export const mockWebSocket = {
  sendMessage: jest.fn(),
  connected: true,
  error: null,
  status: 'OPEN' as const,
  messages: [],
  connect: jest.fn(),
  disconnect: jest.fn(),
  isConnected: true,
  connectionState: 'connected' as const,
  lastMessage: null,
  reconnectAttempts: 0,
  messageQueue: [],
  ws: null,
  subscribe: jest.fn(),
  unsubscribe: jest.fn(),
};

// Chat Store Mock
export const mockChatStore = {
  subAgentName: 'Test Agent',
  subAgentStatus: { lifecycle: 'running' },
  isProcessing: false,
  messages: [],
  setProcessing: jest.fn(),
  addMessage: jest.fn(),
  clearMessages: jest.fn(),
  updateLayerData: jest.fn(),
  fastLayerData: null,
  mediumLayerData: null,
  slowLayerData: null,
  currentRunId: null,
};

// Unified Chat Store Mock
export const mockUnifiedChatStore = {
  isProcessing: false,
  messages: [],
  fastLayerData: null,
  mediumLayerData: null,
  slowLayerData: null,
  currentRunId: null,
  addMessage: jest.fn(),
  setProcessing: jest.fn(),
  clearMessages: jest.fn(),
  updateLayerData: jest.fn(),
  activeThreadId: 'thread-1',
  setActiveThread: jest.fn(),
};

// Auth Store Mock
export const mockAuthStore = {
  isAuthenticated: true,
  user: mockAuthContext.user,
  token: mockAuthContext.token,
  login: jest.fn(),
  logout: jest.fn(),
  loading: false,
};

// Thread Store Mock
export const mockThreadStore = {
  currentThreadId: 'thread-1',
  setCurrentThread: jest.fn(),
  addThread: jest.fn(),
  threads: [],
  isLoading: false,
};

// Chat WebSocket Hook Mock
export const mockChatWebSocket = {
  connected: true,
  error: null,
  sendMessage: jest.fn(),
  subscribe: jest.fn(),
  unsubscribe: jest.fn(),
};

// MCP Tools Mock
export const mockMCPTools = {
  tools: [],
  servers: [],
  executions: [],
  isLoading: false,
  error: null,
  refreshTools: jest.fn(),
};

/**
 * Setup all jest mocks for chat components
 */
export const setupChatMocks = () => {
  // Mock external dependencies
  global.fetch = jest.fn().mockResolvedValue({
    json: jest.fn().mockResolvedValue({
      ws_url: 'ws://localhost:8000/ws'
    })
  });

  // Mock RawJsonView to render JSON as readable text
  jest.mock('@/components/chat/RawJsonView', () => ({
    RawJsonView: ({ data }: { data: any }) => (
      <div data-testid="raw-json-view">
        {JSON.stringify(data, null, 2)}
      </div>
    )
  }));

  jest.clearAllMocks();
};

/**
 * Reset all mocks to clean state
 */
export const resetChatMocks = () => {
  Object.values(mockChatStore).forEach(mock => 
    typeof mock === 'function' && (mock as jest.Mock).mockClear?.()
  );
  Object.values(mockUnifiedChatStore).forEach(mock => 
    typeof mock === 'function' && (mock as jest.Mock).mockClear?.()
  );
  Object.values(mockWebSocket).forEach(mock => 
    typeof mock === 'function' && (mock as jest.Mock).mockClear?.()
  );
  Object.values(mockAuthStore).forEach(mock => 
    typeof mock === 'function' && (mock as jest.Mock).mockClear?.()
  );
  Object.values(mockThreadStore).forEach(mock => 
    typeof mock === 'function' && (mock as jest.Mock).mockClear?.()
  );
  Object.values(mockChatWebSocket).forEach(mock => 
    typeof mock === 'function' && (mock as jest.Mock).mockClear?.()
  );
  jest.clearAllMocks();
};

/**
 * Override specific mock values for individual tests
 */
export const overrideChatMocks = (overrides: {
  chatStore?: Partial<typeof mockChatStore>;
  unifiedChatStore?: Partial<typeof mockUnifiedChatStore>;
  authStore?: Partial<typeof mockAuthStore>;
  webSocket?: Partial<typeof mockWebSocket>;
  threadStore?: Partial<typeof mockThreadStore>;
  chatWebSocket?: Partial<typeof mockChatWebSocket>;
}) => {
  if (overrides.chatStore) {
    Object.assign(mockChatStore, overrides.chatStore);
  }
  if (overrides.unifiedChatStore) {
    Object.assign(mockUnifiedChatStore, overrides.unifiedChatStore);
  }
  if (overrides.authStore) {
    Object.assign(mockAuthStore, overrides.authStore);
  }
  if (overrides.webSocket) {
    Object.assign(mockWebSocket, overrides.webSocket);
  }
  if (overrides.threadStore) {
    Object.assign(mockThreadStore, overrides.threadStore);
  }
  if (overrides.chatWebSocket) {
    Object.assign(mockChatWebSocket, overrides.chatWebSocket);
  }
};

/**
 * Test wrapper that provides all required contexts
 */
export const ChatTestProvider: React.FC<{ 
  children: React.ReactNode;
  authValue?: Partial<typeof mockAuthContext>;
  wsValue?: Partial<typeof mockWebSocket>;
}> = ({ children, authValue, wsValue }) => {
  const AuthContext = React.createContext({ ...mockAuthContext, ...authValue });
  const WebSocketContext = React.createContext({ ...mockWebSocket, ...wsValue });
  
  return (
    <AuthContext.Provider value={{ ...mockAuthContext, ...authValue }}>
      <WebSocketContext.Provider value={{ ...mockWebSocket, ...wsValue }}>
        {children}
      </WebSocketContext.Provider>
    </AuthContext.Provider>
  );
};

/**
 * Custom render function with chat test setup
 */
export const renderWithChatSetup = (
  ui: React.ReactElement,
  options?: RenderOptions & {
    authValue?: Partial<typeof mockAuthContext>;
    wsValue?: Partial<typeof mockWebSocket>;
  }
) => {
  const { authValue, wsValue, ...renderOptions } = options || {};
  
  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <ChatTestProvider authValue={authValue} wsValue={wsValue}>
      {children}
    </ChatTestProvider>
  );

  return render(ui, { wrapper: Wrapper, ...renderOptions });
};