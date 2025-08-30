/**
 * Minimal MessageInput Test Setup
 * Only mocks external APIs, allows real component behavior
 * BVJ: Reduces test maintenance while ensuring real functionality is tested
 */

import { jest } from '@jest/globals';

// Mock only external WebSocket API
export const mockSendMessage = jest.fn();
export const mockUseWebSocket = jest.fn(() => ({
  sendMessage: mockSendMessage,
}));

// Mock textarea resize hook
export const mockUseTextareaResize = jest.fn();

// Mock only external stores (these would make HTTP calls)
export const mockChatStore = {
  activeThreadId: 'thread-1',
  isProcessing: false,
  setProcessing: jest.fn(),
  addMessage: jest.fn(),
  addOptimisticMessage: jest.fn(),
  updateOptimisticMessage: jest.fn(),
};

export const mockThreadStore = {
  currentThreadId: 'thread-1',
  setCurrentThread: jest.fn(),
  addThread: jest.fn(),
};

export const mockAuthStore = {
  isAuthenticated: true,
};

// Apply minimal mocks using jest.mock for proper hoisting
export const setupMinimalMocks = () => {
  // Mock the stores first
  jest.mock('@/store/unified-chat', () => ({
    useUnifiedChatStore: jest.fn(() => mockChatStore)
  }));
  
  jest.mock('@/store/threadStore', () => ({
    useThreadStore: jest.fn(() => mockThreadStore)
  }));
  
  jest.mock('@/store/authStore', () => ({
    useAuthStore: jest.fn(() => mockAuthStore)
  }));

  // Mock websocket hook
  jest.mock('@/hooks/useWebSocket', () => ({
    useWebSocket: mockUseWebSocket
  }));

  // Mock the message sending hook
  jest.mock('@/components/chat/hooks/useMessageSending', () => ({
    useMessageSending: () => ({
      isSending: false,
      error: null,
      isTimeout: false,
      retryCount: 0,
      isCircuitOpen: false,
      handleSend: jest.fn().mockResolvedValue(undefined),
      retry: jest.fn(),
      reset: jest.fn()
    })
  }));

  // Mock other hooks with minimal implementation
  jest.mock('@/components/chat/hooks/useMessageHistory', () => ({
    useMessageHistory: () => ({
      messageHistory: [],
      addToHistory: jest.fn(),
      navigateHistory: jest.fn(() => '')
    })
  }));

  jest.mock('@/components/chat/hooks/useTextareaResize', () => ({
    useTextareaResize: mockUseTextareaResize
  }));
  
  // Setup default mock behavior with dynamic response
  mockUseTextareaResize.mockImplementation((textareaRef: any, message: string) => {
    const lineCount = message ? message.split('\n').length : 1;
    const rows = Math.min(Math.max(lineCount, 1), 5);
    console.log(`[MOCK] useTextareaResize called with message: "${message}", returning rows: ${rows}`);
    return { rows };
  });
};

// Reset function
export const resetMocks = () => {
  jest.clearAllMocks();
  mockChatStore.isProcessing = false;
  mockAuthStore.isAuthenticated = true;
  // Setup default textarea behavior with dynamic response
  mockUseTextareaResize.mockImplementation((textareaRef: any, message: string) => {
    const lineCount = message ? message.split('\n').length : 1;
    const rows = Math.min(Math.max(lineCount, 1), 5);
    console.log(`[MOCK] useTextareaResize called with message: "${message}", returning rows: ${rows}`);
    return { rows };
  });
};

// Quick overrides for test scenarios
export const setProcessing = (processing: boolean) => {
  mockChatStore.isProcessing = processing;
};

export const setAuthenticated = (auth: boolean) => {
  mockAuthStore.isAuthenticated = auth;
};

export const setThreadId = (id: string) => {
  mockChatStore.activeThreadId = id;
  mockThreadStore.currentThreadId = id;
};

