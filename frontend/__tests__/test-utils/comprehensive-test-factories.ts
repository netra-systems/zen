// ============================================================================
// COMPREHENSIVE TEST FACTORIES - UNIFIED DATA CREATION
// ============================================================================
// This file provides complete factories for all test entities to ensure
// consistent test data across all test suites.
// ============================================================================

export interface MockUser {
  id: string;
  email: string;
  full_name: string;
  created_at?: string;
  updated_at?: string;
}

export interface MockThread {
  id: string;
  title: string;
  messages: MockMessage[];
  created_at: string;
  updated_at: string;
  user_id?: string;
}

export interface MockMessage {
  id: string;
  content: string;
  type: 'user' | 'assistant' | 'system';
  role: 'user' | 'assistant' | 'system';
  timestamp: number;
  thread_id?: string;
  tempId?: string;
  optimisticTimestamp?: number;
  contentHash?: string;
  reconciliationStatus?: 'pending' | 'confirmed' | 'failed';
  sequenceNumber?: number;
  retryCount?: number;
}

export interface MockMCPServer {
  id: string;
  name: string;
  url: string;
  transport: 'HTTP' | 'WebSocket';
  status: 'CONNECTED' | 'DISCONNECTED' | 'ERROR';
  created_at: string;
  updated_at: string;
}

export interface MockMCPTool {
  name: string;
  server_name: string;
  description: string;
  input_schema: {
    type: string;
    properties: Record<string, any>;
  };
}

export interface MockMCPToolResult {
  tool_name: string;
  server_name: string;
  content: Array<{ type: string; text: string }>;
  is_error: boolean;
  execution_time_ms: number;
}

export interface MockAuthConfig {
  development_mode: boolean;
  google_client_id: string;
  endpoints: {
    login: string;
    logout: string;
    callback: string;
    token: string;
    user: string;
    dev_login: string;
  };
  authorized_javascript_origins: string[];
  authorized_redirect_uris: string[];
}

// ============================================================================
// USER FACTORIES
// ============================================================================
export const createMockUser = (overrides: Partial<MockUser> = {}): MockUser => ({
  id: 'test-user-123',
  email: 'test@example.com',
  full_name: 'Test User',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  ...overrides
});

export const createMockAdmin = (overrides: Partial<MockUser> = {}): MockUser => 
  createMockUser({
    id: 'admin-user-123',
    email: 'admin@example.com',
    full_name: 'Admin User',
    ...overrides
  });

// ============================================================================
// THREAD FACTORIES
// ============================================================================
export const createMockThread = (overrides: Partial<MockThread> = {}): MockThread => ({
  id: 'thread-123',
  title: 'Test Thread',
  messages: [],
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  user_id: 'test-user-123',
  ...overrides
});

export const createMockThreadWithMessages = (messageCount: number = 3): MockThread => {
  const messages = Array.from({ length: messageCount }, (_, index) => 
    createMockMessage({
      id: `message-${index + 1}`,
      content: `Test message ${index + 1}`,
      type: index % 2 === 0 ? 'user' : 'assistant'
    })
  );
  
  return createMockThread({
    messages,
    title: `Thread with ${messageCount} messages`
  });
};

// ============================================================================
// MESSAGE FACTORIES
// ============================================================================
export const createMockMessage = (overrides: Partial<MockMessage> = {}): MockMessage => ({
  id: 'message-123',
  content: 'Test message content',
  type: 'user',
  role: 'user',
  timestamp: Date.now(),
  thread_id: 'thread-123',
  tempId: `temp-${Date.now()}`,
  optimisticTimestamp: Date.now(),
  contentHash: 'hash-123',
  reconciliationStatus: 'pending',
  sequenceNumber: 1,
  retryCount: 0,
  ...overrides
});

export const createMockUserMessage = (content: string = 'User message'): MockMessage =>
  createMockMessage({
    content,
    type: 'user',
    role: 'user'
  });

export const createMockAssistantMessage = (content: string = 'Assistant message'): MockMessage =>
  createMockMessage({
    content,
    type: 'assistant',
    role: 'assistant'
  });

export const createMockOptimisticMessage = (overrides: Partial<MockMessage> = {}): MockMessage =>
  createMockMessage({
    reconciliationStatus: 'pending',
    optimisticTimestamp: Date.now(),
    tempId: `optimistic-${Date.now()}`,
    ...overrides
  });

// ============================================================================
// MCP FACTORIES
// ============================================================================
export const createMockMCPServer = (overrides: Partial<MockMCPServer> = {}): MockMCPServer => ({
  id: 'mock-server-1',
  name: 'mock-server',
  url: 'http://localhost:3001',
  transport: 'HTTP',
  status: 'CONNECTED',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  ...overrides
});

export const createMockMCPTool = (overrides: Partial<MockMCPTool> = {}): MockMCPTool => ({
  name: 'mock-tool',
  server_name: 'mock-server',
  description: 'Mock MCP tool for testing',
  input_schema: {
    type: 'object',
    properties: {
      input: { type: 'string', description: 'Test input' }
    }
  },
  ...overrides
});

export const createMockMCPToolResult = (overrides: Partial<MockMCPToolResult> = {}): MockMCPToolResult => ({
  tool_name: 'mock-tool',
  server_name: 'mock-server',
  content: [{ type: 'text', text: 'Mock result content' }],
  is_error: false,
  execution_time_ms: 150,
  ...overrides
});

export const createMockMCPErrorResult = (error: string = 'Mock error'): MockMCPToolResult =>
  createMockMCPToolResult({
    content: [{ type: 'text', text: error }],
    is_error: true,
    execution_time_ms: 50
  });

// ============================================================================
// AUTHENTICATION FACTORIES
// ============================================================================
export const createMockAuthConfig = (overrides: Partial<MockAuthConfig> = {}): MockAuthConfig => ({
  development_mode: true,
  google_client_id: 'mock-google-client-id',
  endpoints: {
    login: 'http://localhost:8081/auth/login',
    logout: 'http://localhost:8081/auth/logout',
    callback: 'http://localhost:8081/auth/callback',
    token: 'http://localhost:8081/auth/token',
    user: 'http://localhost:8081/auth/me',
    dev_login: 'http://localhost:8081/auth/dev/login'
  },
  authorized_javascript_origins: ['http://localhost:3000'],
  authorized_redirect_uris: ['http://localhost:3000/auth/callback'],
  ...overrides
});

export const createMockAuthToken = () => ({
  access_token: 'mock-access-token',
  token_type: 'Bearer',
  expires_in: 3600,
  refresh_token: 'mock-refresh-token'
});

// ============================================================================
// WEBSOCKET FACTORIES
// ============================================================================
export const createMockWebSocketMessage = (type: string, payload: any = {}) => ({
  type,
  payload,
  timestamp: Date.now(),
  id: `ws-message-${Date.now()}`
});

export const createMockWebSocketError = (error: string = 'Connection failed') => ({
  type: 'error',
  error,
  timestamp: Date.now()
});

// ============================================================================
// API RESPONSE FACTORIES
// ============================================================================
export const createMockApiResponse = <T>(data: T, status: number = 200) => ({
  data,
  status,
  statusText: status === 200 ? 'OK' : 'Error',
  headers: {},
  config: {}
});

export const createMockApiError = (message: string = 'API Error', status: number = 500) => ({
  message,
  status,
  response: {
    data: { error: message },
    status,
    statusText: 'Error'
  }
});

// ============================================================================
// STORE STATE FACTORIES
// ============================================================================
export const createMockAuthState = (overrides: any = {}) => ({
  isAuthenticated: true,
  user: createMockUser(),
  token: 'mock-token',
  loading: false,
  error: null,
  ...overrides
});

export const createMockChatState = (overrides: any = {}) => ({
  activeThreadId: 'thread-123',
  threads: [createMockThread()],
  messages: [createMockMessage()],
  isProcessing: false,
  error: null,
  ...overrides
});

export const createMockMCPState = (overrides: any = {}) => ({
  servers: [createMockMCPServer()],
  tools: [createMockMCPTool()],
  executions: [],
  isLoading: false,
  error: null,
  ...overrides
});

// ============================================================================
// COMPONENT PROP FACTORIES
// ============================================================================
export const createMockComponentProps = (overrides: any = {}) => ({
  className: 'test-class',
  'data-testid': 'test-component',
  ...overrides
});

export const createMockChatComponentProps = (overrides: any = {}) => ({
  ...createMockComponentProps(),
  thread: createMockThread(),
  messages: [createMockMessage()],
  onSendMessage: jest.fn(),
  isProcessing: false,
  ...overrides
});

// ============================================================================
// EVENT FACTORIES
// ============================================================================
export const createMockMouseEvent = (overrides: any = {}) => ({
  preventDefault: jest.fn(),
  stopPropagation: jest.fn(),
  target: { value: '' },
  currentTarget: { value: '' },
  ...overrides
});

export const createMockKeyboardEvent = (key: string = 'Enter', overrides: any = {}) => ({
  key,
  preventDefault: jest.fn(),
  stopPropagation: jest.fn(),
  target: { value: '' },
  currentTarget: { value: '' },
  ...overrides
});

export const createMockFormEvent = (formData: any = {}) => ({
  preventDefault: jest.fn(),
  target: {
    elements: formData,
    value: '',
    reset: jest.fn()
  }
});

// ============================================================================
// BATCH FACTORIES FOR COMPLEX SCENARIOS
// ============================================================================
export const createCompleteTestScenario = () => {
  const user = createMockUser();
  const thread = createMockThreadWithMessages(5);
  const servers = [createMockMCPServer(), createMockMCPServer({ name: 'server-2', id: 'server-2' })];
  const tools = [createMockMCPTool(), createMockMCPTool({ name: 'tool-2', server_name: 'server-2' })];

  return {
    user,
    thread,
    servers,
    tools,
    authState: createMockAuthState({ user }),
    chatState: createMockChatState({ activeThreadId: thread.id, threads: [thread], messages: thread.messages }),
    mcpState: createMockMCPState({ servers, tools })
  };
};

export const createErrorTestScenario = () => {
  const error = createMockApiError('Test error', 500);
  
  return {
    user: null,
    thread: null,
    authState: createMockAuthState({ isAuthenticated: false, user: null, error: error.message }),
    chatState: createMockChatState({ error: error.message, isProcessing: false }),
    mcpState: createMockMCPState({ error: error.message, isLoading: false }),
    apiError: error
  };
};