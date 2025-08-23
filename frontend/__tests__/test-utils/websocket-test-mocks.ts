// ============================================================================
// WEBSOCKET TEST MOCKS - COMPREHENSIVE WEBSOCKET TESTING INFRASTRUCTURE
// ============================================================================
// This file provides complete WebSocket mocking for all WebSocket-related tests
// to ensure consistent WebSocket behavior across all test scenarios.
// ============================================================================

export interface MockWebSocketMessage {
  type: string;
  payload: any;
  timestamp: number;
  id: string;
}

export interface MockWebSocketError {
  type: 'error';
  error: string;
  timestamp: number;
}

export class MockWebSocket {
  public url: string;
  public readyState: number;
  public onopen: ((event: Event) => void) | null = null;
  public onclose: ((event: CloseEvent) => void) | null = null;
  public onerror: ((event: ErrorEvent) => void) | null = null;
  public onmessage: ((event: MessageEvent) => void) | null = null;
  
  public send = jest.fn();
  public close = jest.fn();
  public addEventListener = jest.fn();
  public removeEventListener = jest.fn();
  
  private messageQueue: MockWebSocketMessage[] = [];
  private errorQueue: MockWebSocketError[] = [];
  
  constructor(url: string) {
    this.url = url + `-test-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    this.readyState = MockWebSocket.OPEN;
    
    // Simulate async connection
    setTimeout(() => {
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    }, 0);
  }
  
  // Simulate receiving a message
  simulateMessage(data: any) {
    const message: MockWebSocketMessage = {
      type: typeof data === 'object' ? data.type || 'message' : 'message',
      payload: data,
      timestamp: Date.now(),
      id: `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    };
    
    this.messageQueue.push(message);
    
    const event = new MessageEvent('message', { 
      data: typeof data === 'string' ? data : JSON.stringify(data) 
    });
    
    if (this.onmessage) {
      this.onmessage(event);
    }
  }
  
  // Simulate an error
  simulateError(error: string | Error) {
    const errorObj: MockWebSocketError = {
      type: 'error',
      error: error instanceof Error ? error.message : error,
      timestamp: Date.now()
    };
    
    this.errorQueue.push(errorObj);
    
    const event = new ErrorEvent('error', { 
      error: error instanceof Error ? error : new Error(error)
    });
    
    if (this.onerror) {
      this.onerror(event);
    }
  }
  
  // Simulate connection close
  simulateClose(code: number = 1000, reason: string = 'Normal closure') {
    this.readyState = MockWebSocket.CLOSED;
    
    const event = new CloseEvent('close', {
      code,
      reason,
      wasClean: code === 1000
    });
    
    if (this.onclose) {
      this.onclose(event);
    }
  }
  
  // Get message history
  getMessages(): MockWebSocketMessage[] {
    return [...this.messageQueue];
  }
  
  // Get error history
  getErrors(): MockWebSocketError[] {
    return [...this.errorQueue];
  }
  
  // Clear history
  clearHistory() {
    this.messageQueue = [];
    this.errorQueue = [];
  }
  
  // Static constants
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSING = 2;
  static readonly CLOSED = 3;
}

// ============================================================================
// WEBSOCKET CONTEXT MOCK
// ============================================================================
export const createMockWebSocketContext = (overrides: any = {}) => ({
  // Connection state
  status: 'OPEN',
  isConnected: true,
  connectionState: 'connected',
  readyState: MockWebSocket.OPEN,
  
  // Messages
  messages: [],
  lastMessage: null,
  messageQueue: [],
  
  // Methods
  sendMessage: jest.fn(),
  addOptimisticMessage: jest.fn(),
  sendOptimisticMessage: jest.fn(() => ({
    id: 'mock-optimistic-id',
    content: 'mock-content',
    type: 'user',
    role: 'user',
    timestamp: Date.now(),
    tempId: 'mock-temp-id',
    optimisticTimestamp: Date.now(),
    contentHash: 'mock-hash',
    reconciliationStatus: 'pending',
    sequenceNumber: 1,
    retryCount: 0
  })),
  
  // Connection management
  connect: jest.fn(),
  disconnect: jest.fn(),
  reconnect: jest.fn(),
  
  // Event handling
  subscribe: jest.fn(),
  unsubscribe: jest.fn(),
  
  // Error handling
  error: null,
  reconnectAttempts: 0,
  maxReconnectAttempts: 5,
  
  // Statistics
  reconciliationStats: {
    totalOptimistic: 0,
    totalConfirmed: 0,
    totalFailed: 0,
    totalTimeout: 0,
    averageReconciliationTime: 0,
    currentPendingCount: 0
  },
  
  // WebSocket instance (mock)
  ws: null,
  
  // Override any values
  ...overrides
});

// ============================================================================
// WEBSOCKET HOOK MOCKS
// ============================================================================
export const createMockWebSocketHook = (overrides: any = {}) => ({
  // Connection state
  isConnected: true,
  connectionState: 'connected',
  status: 'OPEN',
  error: null,
  
  // Messages
  messages: [],
  lastMessage: null,
  messageQueue: [],
  
  // Methods
  sendMessage: jest.fn().mockResolvedValue(undefined),
  addOptimisticMessage: jest.fn().mockReturnValue({
    id: 'mock-optimistic-id',
    tempId: 'mock-temp-id',
    content: 'mock-content',
    timestamp: Date.now()
  }),
  
  // Connection management
  connect: jest.fn().mockResolvedValue(undefined),
  disconnect: jest.fn().mockResolvedValue(undefined),
  reconnect: jest.fn().mockResolvedValue(undefined),
  
  // Event handling
  subscribe: jest.fn(),
  unsubscribe: jest.fn(),
  
  // Statistics
  reconnectAttempts: 0,
  
  // WebSocket instance
  ws: null,
  
  // Override any values
  ...overrides
});

// ============================================================================
// WEBSOCKET SERVICE MOCK
// ============================================================================
export const createMockWebSocketService = (overrides: any = {}) => ({
  // Connection management
  connect: jest.fn().mockResolvedValue(undefined),
  disconnect: jest.fn().mockResolvedValue(undefined),
  reconnect: jest.fn().mockResolvedValue(undefined),
  isConnected: jest.fn().mockReturnValue(true),
  
  // Message handling
  sendMessage: jest.fn().mockResolvedValue(undefined),
  sendJSON: jest.fn().mockResolvedValue(undefined),
  
  // Event handling
  on: jest.fn(),
  off: jest.fn(),
  emit: jest.fn(),
  
  // Connection state
  connectionState: 'connected',
  readyState: MockWebSocket.OPEN,
  
  // Error handling
  getLastError: jest.fn().mockReturnValue(null),
  clearErrors: jest.fn(),
  
  // Statistics
  getConnectionStats: jest.fn().mockReturnValue({
    totalConnections: 1,
    totalDisconnections: 0,
    totalReconnects: 0,
    uptime: 1000
  }),
  
  // Override any values
  ...overrides
});

// ============================================================================
// MESSAGE FACTORIES FOR WEBSOCKET TESTS
// ============================================================================
export const createWebSocketMessage = (type: string, payload: any = {}) => ({
  type,
  payload,
  timestamp: Date.now(),
  id: `ws-msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
});

export const createAgentMessage = (content: string, status: string = 'running') => 
  createWebSocketMessage('agent_update', {
    content,
    status,
    agent_id: 'test-agent-123',
    timestamp: Date.now()
  });

export const createUserMessage = (content: string) => 
  createWebSocketMessage('user_message', {
    content,
    user_id: 'test-user-123',
    thread_id: 'test-thread-123',
    timestamp: Date.now()
  });

export const createErrorMessage = (error: string, code: string = 'GENERAL_ERROR') =>
  createWebSocketMessage('error', {
    error,
    code,
    timestamp: Date.now()
  });

export const createToolCallMessage = (toolName: string, args: any = {}) =>
  createWebSocketMessage('tool_call', {
    tool_name: toolName,
    server_name: 'test-server',
    arguments: args,
    timestamp: Date.now()
  });

export const createToolResultMessage = (toolName: string, result: any = {}) =>
  createWebSocketMessage('tool_result', {
    tool_name: toolName,
    server_name: 'test-server',
    content: result,
    is_error: false,
    execution_time_ms: 150,
    timestamp: Date.now()
  });

// ============================================================================
// WEBSOCKET ERROR SCENARIOS
// ============================================================================
export const createConnectionError = () => createErrorMessage('Connection failed', 'CONNECTION_ERROR');
export const createAuthError = () => createErrorMessage('Authentication failed', 'AUTH_ERROR');
export const createTimeoutError = () => createErrorMessage('Request timeout', 'TIMEOUT_ERROR');
export const createServerError = () => createErrorMessage('Internal server error', 'SERVER_ERROR');

// ============================================================================
// TEST UTILITIES
// ============================================================================
export const waitForWebSocketConnection = async (mockWs: MockWebSocket, timeout: number = 1000) => {
  const startTime = Date.now();
  
  while (mockWs.readyState !== MockWebSocket.OPEN && Date.now() - startTime < timeout) {
    await new Promise(resolve => setTimeout(resolve, 10));
  }
  
  if (mockWs.readyState !== MockWebSocket.OPEN) {
    throw new Error('WebSocket connection timeout');
  }
};

export const waitForWebSocketMessage = async (mockWs: MockWebSocket, timeout: number = 1000) => {
  const startTime = Date.now();
  const initialCount = mockWs.getMessages().length;
  
  while (mockWs.getMessages().length <= initialCount && Date.now() - startTime < timeout) {
    await new Promise(resolve => setTimeout(resolve, 10));
  }
  
  if (mockWs.getMessages().length <= initialCount) {
    throw new Error('WebSocket message timeout');
  }
  
  return mockWs.getMessages()[mockWs.getMessages().length - 1];
};

export const simulateWebSocketConversation = (mockWs: MockWebSocket) => {
  return {
    userSaysHello: () => mockWs.simulateMessage(createUserMessage('Hello')),
    agentResponds: (content: string) => mockWs.simulateMessage(createAgentMessage(content)),
    toolCalled: (toolName: string, args: any) => mockWs.simulateMessage(createToolCallMessage(toolName, args)),
    toolResult: (toolName: string, result: any) => mockWs.simulateMessage(createToolResultMessage(toolName, result)),
    error: (error: string) => mockWs.simulateError(error),
    close: () => mockWs.simulateClose()
  };
};

// Install WebSocket mock globally
export const installWebSocketMock = () => {
  global.WebSocket = MockWebSocket as any;
  return MockWebSocket;
};