/**
 * Message Test Helpers - Comprehensive Message Testing Utilities
 * 
 * BUSINESS VALUE JUSTIFICATION:
 * - Segment: All (Free → Enterprise)
 * - Business Goal: Ensure reliable chat functionality critical to platform
 * - Value Impact: Prevents message delivery failures and UX issues
 * - Revenue Impact: Protects $200K+ MRR dependent on chat reliability
 * 
 * ARCHITECTURAL COMPLIANCE:
 * - File size: ≤300 lines (MANDATORY)
 * - Functions: ≤8 lines each (MANDATORY)
 * - TypeScript with full type safety
 * - Composable and reusable utilities
 */

import { jest } from '@jest/globals';

// Define types locally to avoid import issues during testing
export type MessageRole = 'user' | 'assistant' | 'system';

export interface MessageMetadata {
  sub_agent?: string;
  tool_name?: string;
  execution_time_ms?: number;
  agent_name?: string;
  token_count?: number;
  model_used?: string;
  confidence_score?: number;
  source?: string;
  references?: string[];
  [key: string]: unknown;
}

// ============================================================================
// MESSAGE MOCK FACTORIES - Message generation utilities
// ============================================================================

export interface MockMessage {
  id: string;
  content: string;
  role: MessageRole;
  thread_id?: string;
  created_at: string;
  metadata?: MessageMetadata;
  timestamp?: number;
}

/**
 * Create mock message with minimal data
 */
export function createMockMessage(overrides: Partial<MockMessage> = {}): MockMessage {
  const id = overrides.id || `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  
  return {
    id,
    content: overrides.content || `Test message content ${id.slice(-8)}`,
    role: overrides.role || 'user',
    thread_id: overrides.thread_id || `thread_${Date.now()}`,
    created_at: overrides.created_at || new Date().toISOString(),
    timestamp: overrides.timestamp || Date.now(),
    ...overrides
  };
}

/**
 * Create user message with realistic content
 */
export function createUserMessage(content: string = 'Hello, how can you help me?'): MockMessage {
  return createMockMessage({
    role: 'user',
    content,
    metadata: { token_count: content.length / 4 }
  });
}

/**
 * Create assistant message with metadata
 */
export function createAssistantMessage(content: string = 'I can help you with that!'): MockMessage {
  return createMockMessage({
    role: 'assistant',
    content,
    metadata: {
      model_used: 'gemini-2.5-flash',
      token_count: content.length / 4,
      execution_time_ms: 1200
    }
  });
}

/**
 * Create system message for notifications
 */
export function createSystemMessage(content: string = 'System notification'): MockMessage {
  return createMockMessage({
    role: 'system',
    content,
    metadata: { source: 'system' }
  });
}

/**
 * Create message thread conversation
 */
export function createMessageThread(length: number = 3, threadId?: string): MockMessage[] {
  const id = threadId || `thread_${Date.now()}`;
  const messages: MockMessage[] = [];
  
  for (let i = 0; i < length; i++) {
    const role: MessageRole = i % 2 === 0 ? 'user' : 'assistant';
    messages.push(createMockMessage({
      role,
      thread_id: id,
      content: `${role} message ${i + 1} in thread`,
      created_at: new Date(Date.now() + i * 1000).toISOString()
    }));
  }
  
  return messages;
}

// ============================================================================
// WEBSOCKET MESSAGE HELPERS - WebSocket event simulation
// ============================================================================

export interface MockWebSocketMessage {
  type: string;
  payload: Record<string, any>;
  timestamp: string;
  id?: string;
}

/**
 * Create WebSocket message event
 */
export function createWebSocketMessage(
  type: string,
  payload: Record<string, any> = {}
): MockWebSocketMessage {
  return {
    type,
    payload,
    timestamp: new Date().toISOString(),
    id: `ws_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`
  };
}

/**
 * Create message received WebSocket event
 */
export function createMessageReceivedEvent(message: MockMessage): MockWebSocketMessage {
  return createWebSocketMessage('message_received', { message });
}

/**
 * Create typing indicator WebSocket event
 */
export function createTypingEvent(isTyping: boolean = true): MockWebSocketMessage {
  return createWebSocketMessage('typing', { is_typing: isTyping });
}

/**
 * Create agent response WebSocket event
 */
export function createAgentResponseEvent(content: string): MockWebSocketMessage {
  return createWebSocketMessage('agent_response', {
    message: createAssistantMessage(content)
  });
}

/**
 * Create error WebSocket event
 */
export function createWebSocketError(error: string): MockWebSocketMessage {
  return createWebSocketMessage('error', { error, code: 'TEST_ERROR' });
}

// ============================================================================
// MESSAGE VALIDATION HELPERS - Testing utilities
// ============================================================================

/**
 * Assert message has required fields
 */
export function expectValidMessage(message: any): void {
  expect(message).toBeDefined();
  expect(typeof message.id).toBe('string');
  expect(typeof message.content).toBe('string');
  expect(['user', 'assistant', 'system']).toContain(message.role);
}

/**
 * Assert message content matches expected
 */
export function expectMessageContent(message: MockMessage, expectedContent: string): void {
  expect(message.content).toBe(expectedContent);
  expect(message.content.length).toBeGreaterThan(0);
}

/**
 * Assert message has metadata
 */
export function expectMessageMetadata(message: MockMessage): void {
  expect(message.metadata).toBeDefined();
  expect(typeof message.metadata).toBe('object');
}

/**
 * Assert message belongs to thread
 */
export function expectMessageInThread(message: MockMessage, threadId: string): void {
  expect(message.thread_id).toBe(threadId);
}

// ============================================================================
// MESSAGE LIST HELPERS - Array operations
// ============================================================================

/**
 * Filter messages by role
 */
export function filterMessagesByRole(messages: MockMessage[], role: MessageRole): MockMessage[] {
  return messages.filter(msg => msg.role === role);
}

/**
 * Get latest message from list
 */
export function getLatestMessage(messages: MockMessage[]): MockMessage | null {
  if (messages.length === 0) return null;
  return messages.reduce((latest, current) => 
    new Date(current.created_at) > new Date(latest.created_at) ? current : latest
  );
}

/**
 * Sort messages chronologically
 */
export function sortMessagesByTime(messages: MockMessage[]): MockMessage[] {
  return [...messages].sort((a, b) => 
    new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
  );
}

/**
 * Count messages by role
 */
export function countMessagesByRole(messages: MockMessage[]): Record<MessageRole, number> {
  return messages.reduce((counts, msg) => {
    counts[msg.role] = (counts[msg.role] || 0) + 1;
    return counts;
  }, {} as Record<MessageRole, number>);
}

// ============================================================================
// MESSAGE MOCK SETUP - Test environment helpers
// ============================================================================

/**
 * Setup message service mocks
 */
export function setupMessageMocks() {
  return {
    sendMessage: jest.fn(() => Promise.resolve({ success: true })),
    loadMessages: jest.fn(() => Promise.resolve([])),
    deleteMessage: jest.fn(() => Promise.resolve({ success: true }))
  };
}

/**
 * Mock WebSocket for message testing
 */
export function createMockWebSocket() {
  const listeners: Record<string, Function[]> = {};
  
  return {
    send: jest.fn(),
    close: jest.fn(),
    addEventListener: jest.fn((event: string, callback: Function) => {
      if (!listeners[event]) listeners[event] = [];
      listeners[event].push(callback);
    }),
    removeEventListener: jest.fn(),
    simulateMessage: (message: MockWebSocketMessage) => {
      const messageEvent = new MessageEvent('message', {
        data: JSON.stringify(message)
      });
      listeners.message?.forEach(callback => callback(messageEvent));
    }
  };
}

// All functions are already exported above - no need for re-export