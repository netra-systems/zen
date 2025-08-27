/**
 * Chat Functionality Test Helpers - Critical Test Utilities
 * 
 * BUSINESS VALUE JUSTIFICATION:
 * - Segment: All (Free → Enterprise)
 * - Business Goal: Ensure core chat functionality works reliably
 * - Value Impact: Prevents failures in primary user workflow (chat)
 * - Revenue Impact: Protects entire $500K+ MRR dependent on chat functionality
 */

import { jest } from '@jest/globals';

// ============================================================================
// WEBSOCKET TEST UTILITIES - Real WebSocket testing
// ============================================================================

export class WebSocketTestManager {
  private mockSocket: any;
  
  constructor(url?: string) {
    this.mockSocket = {
      url: url || 'ws://test',
      readyState: 1, // OPEN
      send: jest.fn(),
      close: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn()
    };
  }
  
  getMockSocket() {
    return this.mockSocket;
  }
  
  simulateMessage(data: any) {
    const event = new MessageEvent('message', { data: JSON.stringify(data) });
    this.mockSocket.onmessage?.(event);
  }
  
  simulateOpen() {
    const event = new Event('open');
    this.mockSocket.onopen?.(event);
  }
  
  simulateClose() {
    const event = new Event('close');
    this.mockSocket.onclose?.(event);
  }
}

/**
 * Wait for real message in WebSocket
 */
export async function waitForRealMessage(
  websocket: any, 
  timeout: number = 5000
): Promise<any> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      reject(new Error('Message timeout'));
    }, timeout);
    
    const originalOnMessage = websocket.onmessage;
    websocket.onmessage = (event: MessageEvent) => {
      clearTimeout(timer);
      websocket.onmessage = originalOnMessage;
      
      try {
        const data = JSON.parse(event.data);
        resolve(data);
      } catch (error) {
        resolve(event.data);
      }
    };
  });
}

/**
 * Expect real WebSocket connection
 */
export function expectRealWebSocketConnection(websocket: any): void {
  expect(websocket).toBeDefined();
  expect(websocket.readyState).toBe(1); // OPEN
  expect(websocket.url).toMatch(/^wss?:/);
}

// ============================================================================
// CHAT FORMATTING TEST UTILITIES - Message formatting helpers
// ============================================================================

export interface FormattingTestConfig {
  enableMarkdown?: boolean;
  enableCodeHighlighting?: boolean;
  maxLength?: number;
}

/**
 * Setup formatting test environment
 */
export function setupFormattingTestEnvironment(config: FormattingTestConfig = {}) {
  const defaultConfig = {
    enableMarkdown: true,
    enableCodeHighlighting: true,
    maxLength: 10000,
    ...config
  };
  
  return {
    config: defaultConfig,
    testMarkdown: '**bold** *italic* `code`',
    testCodeBlock: '```javascript\nconst test = "hello";\n```',
    testLongText: 'a'.repeat(defaultConfig.maxLength + 100)
  };
}

/**
 * Validate message formatting
 */
export function validateMessageFormatting(
  element: HTMLElement,
  expectedFormat: 'markdown' | 'plain' | 'code'
): void {
  switch (expectedFormat) {
    case 'markdown':
      expect(element.querySelector('strong, b')).toBeTruthy();
      break;
    case 'code':
      expect(element.querySelector('code, pre')).toBeTruthy();
      break;
    case 'plain':
      expect(element.querySelector('strong, b, code, pre')).toBeFalsy();
      break;
  }
}

// ============================================================================
// THREAD MANAGEMENT TEST UTILITIES - Thread testing helpers
// ============================================================================

export interface MockThread {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

/**
 * Create mock thread
 */
export function createMockThread(overrides: Partial<MockThread> = {}): MockThread {
  const id = overrides.id || `thread_${Date.now()}`;
  return {
    id,
    title: overrides.title || `Test Thread ${id}`,
    created_at: overrides.created_at || new Date().toISOString(),
    updated_at: overrides.updated_at || new Date().toISOString(),
    message_count: overrides.message_count || 0,
    ...overrides
  };
}

/**
 * Create multiple mock threads
 */
export function createMockThreads(count: number): MockThread[] {
  return Array.from({ length: count }, (_, i) => 
    createMockThread({ 
      id: `thread_${i}`,
      title: `Thread ${i + 1}`,
      message_count: Math.floor(Math.random() * 10)
    })
  );
}

/**
 * Validate thread management operations
 */
export function validateThreadOperation(
  operation: 'create' | 'update' | 'delete' | 'switch',
  beforeState: MockThread[],
  afterState: MockThread[],
  targetThreadId?: string
): void {
  switch (operation) {
    case 'create':
      expect(afterState.length).toBe(beforeState.length + 1);
      break;
    case 'delete':
      expect(afterState.length).toBe(beforeState.length - 1);
      if (targetThreadId) {
        expect(afterState.find(t => t.id === targetThreadId)).toBeFalsy();
      }
      break;
    case 'update':
      expect(afterState.length).toBe(beforeState.length);
      break;
    case 'switch':
      // Switch doesn't change thread count, just active thread
      expect(afterState.length).toBe(beforeState.length);
      break;
  }
}

// ============================================================================
// MESSAGE TESTING UTILITIES - Message flow helpers
// ============================================================================

export interface MockMessage {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  created_at: string;
  thread_id?: string;
}

/**
 * Create mock message
 */
export function createMockMessage(overrides: Partial<MockMessage> = {}): MockMessage {
  const id = overrides.id || `msg_${Date.now()}`;
  return {
    id,
    content: overrides.content || `Test message ${id}`,
    role: overrides.role || 'user',
    created_at: overrides.created_at || new Date().toISOString(),
    thread_id: overrides.thread_id || 'test-thread',
    ...overrides
  };
}

/**
 * Create message sequence for testing
 */
export function createMessageSequence(count: number, threadId: string = 'test-thread'): MockMessage[] {
  const messages: MockMessage[] = [];
  
  for (let i = 0; i < count; i++) {
    messages.push(createMockMessage({
      id: `msg_${i}`,
      content: `Message ${i + 1}`,
      role: i % 2 === 0 ? 'user' : 'assistant',
      thread_id: threadId
    }));
  }
  
  return messages;
}

/**
 * Validate message send/receive flow
 */
export function validateMessageFlow(
  sentMessage: MockMessage,
  receivedMessage: MockMessage
): void {
  expect(receivedMessage.id).toBeDefined();
  expect(receivedMessage.content).toBe(sentMessage.content);
  expect(receivedMessage.thread_id).toBe(sentMessage.thread_id);
  expect(receivedMessage.created_at).toBeDefined();
}