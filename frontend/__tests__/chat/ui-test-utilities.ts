/**
 * Shared UI Test Utilities for Chat Components
 * ==========================================
 * Common mocks, helpers, and test setup for modular UI tests
 * Enforces DRY principle and maintains test consistency
 */

import { jest } from '@jest/globals';

// ============================================
// Store Mock Factories (≤8 lines per function)
// ============================================

export const createAuthStoreMock = (overrides = {}) => ({
  user: { id: 'test-user', email: 'test@example.com', name: 'Test User' },
  token: 'test-token',
  isAuthenticated: true,
  setUser: jest.fn(),
  setToken: jest.fn(),
  logout: jest.fn(),
  checkAuth: jest.fn(),
  ...overrides
});

export const createChatStoreMock = (overrides = {}) => ({
  messages: [],
  addMessage: jest.fn(),
  clearMessages: jest.fn(),
  sendMessage: jest.fn(),
  sendMessageOptimistic: jest.fn(),
  updateMessage: jest.fn(),
  deleteMessage: jest.fn(),
  setMessages: jest.fn(),
  isLoading: false,
  setLoading: jest.fn(),
  error: null,
  ...overrides
});

export const createThreadStoreMock = (overrides = {}) => ({
  threads: [],
  currentThreadId: null,
  currentThread: null,
  setThreads: jest.fn(),
  setCurrentThread: jest.fn(),
  setCurrentThreadId: jest.fn(),
  addThread: jest.fn(),
  deleteThread: jest.fn(),
  updateThread: jest.fn(),
  loadThreads: jest.fn(),
  setError: jest.fn(),
  setLoading: jest.fn(),
  loading: false,
  error: null,
  ...overrides
});

export const createWebSocketMock = (overrides = {}) => ({
  connectionState: 'connected',
  sendMessage: jest.fn(),
  subscribe: jest.fn(),
  unsubscribe: jest.fn(),
  reconnect: jest.fn(),
  disconnect: jest.fn(),
  ...overrides
});

export const createUnifiedChatStoreMock = (overrides = {}) => ({
  isProcessing: false,
  messages: [],
  fastLayerData: null,
  mediumLayerData: null,
  slowLayerData: null,
  currentRunId: null,
  sendMessage: jest.fn(),
  clearMessages: jest.fn(),
  setProcessing: jest.fn(),
  ...overrides
});

// ============================================
// Mock Setup Functions (≤8 lines per function)
// ============================================

export const setupDefaultMocks = () => {
  global.fetch = jest.fn().mockResolvedValue({
    json: jest.fn().mockResolvedValue({
      ws_url: 'ws://localhost:8000/ws'
    })
  });
  
  setupClipboardMock();
  jest.clearAllMocks();
};

export const setupClipboardMock = () => {
  const mockClipboard = { writeText: jest.fn() };
  Object.defineProperty(navigator, 'clipboard', {
    value: mockClipboard,
    writable: true
  });
  
  return mockClipboard;
};

export const createThreadServiceMock = () => ({
  listThreads: jest.fn().mockResolvedValue([]),
  createThread: jest.fn().mockResolvedValue({ 
    id: 'new-thread', 
    title: 'New Conversation' 
  }),
  getThreadMessages: jest.fn().mockResolvedValue({ messages: [] }),
  updateThread: jest.fn().mockResolvedValue({ id: 'thread-1', title: 'Updated' }),
  deleteThread: jest.fn().mockResolvedValue(true)
});

export const cleanupMocks = () => {
  jest.restoreAllMocks();
};

// ============================================
// Test Data Factories (≤8 lines per function)
// ============================================

export const createTestMessage = (overrides = {}) => ({
  id: 'test-msg-1',
  content: 'Test message',
  role: 'user',
  timestamp: '2025-01-01T10:00:00Z',
  ...overrides
});

export const createTestThread = (overrides = {}) => ({
  id: 'test-thread-1',
  title: 'Test Thread',
  created_at: '2025-01-01',
  message_count: 5,
  ...overrides
});

export const createTestUser = (overrides = {}) => ({
  id: 'test-user-1',
  email: 'test@example.com',
  name: 'Test User',
  ...overrides
});

// ============================================
// Test Helper Functions (≤8 lines per function)
// ============================================

export const expectElementByTestId = (testId: string) => {
  return expect(screen.getByTestId(testId));
};

export const expectElementByText = (text: string | RegExp) => {
  return expect(screen.getByText(text));
};

export const expectElementByRole = (role: string, options?: any) => {
  return expect(screen.getByRole(role, options));
};

export const waitForElementByTestId = async (testId: string) => {
  return await screen.findByTestId(testId);
};

export const waitForElementByText = async (text: string | RegExp) => {
  return await screen.findByText(text);
};

// ============================================
// Mock Module Configurations
// ============================================

export const mockModuleConfigs = {
  authStore: () => jest.mock('../../store/authStore', () => ({
    useAuthStore: jest.fn(() => createAuthStoreMock())
  })),
  
  chatStore: () => jest.mock('../../store/chatStore', () => ({
    useChatStore: jest.fn(() => createChatStoreMock())
  })),
  
  threadStore: () => jest.mock('../../store/threadStore', () => ({
    useThreadStore: jest.fn(() => createThreadStoreMock())
  })),
  
  unifiedChatStore: () => jest.mock('../../store/unified-chat', () => ({
    useUnifiedChatStore: jest.fn(() => createUnifiedChatStoreMock())
  })),
  
  webSocket: () => jest.mock('../../hooks/useWebSocket', () => ({
    useWebSocket: jest.fn(() => createWebSocketMock())
  })),
  
  chatWebSocket: () => jest.mock('../../hooks/useChatWebSocket', () => ({
    useChatWebSocket: jest.fn(() => createWebSocketMock())
  }))
};

// ============================================
// Bulk Mock Setup (≤8 lines per function)
// ============================================

export const setupAllStoreMocks = () => {
  mockModuleConfigs.authStore();
  mockModuleConfigs.chatStore();
  mockModuleConfigs.threadStore();
  mockModuleConfigs.unifiedChatStore();
  mockModuleConfigs.webSocket();
  mockModuleConfigs.chatWebSocket();
};

// Export screen and other commonly used testing utilities
export { screen, fireEvent, waitFor, within } from '@testing-library/react';
export { default as userEvent } from '@testing-library/user-event';
export { act } from 'react-dom/test-utils';