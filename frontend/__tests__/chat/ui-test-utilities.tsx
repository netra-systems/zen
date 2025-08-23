/**
 * UI Test Utilities - Chat Testing Support Functions
 * 
 * BUSINESS VALUE JUSTIFICATION:
 * - Segment: All (Free → Enterprise)
 * - Business Goal: Ensure reliable chat UI/UX testing
 * - Value Impact: Prevents UI regression affecting 90% of user interactions
 * - Revenue Impact: Protects entire $500K+ MRR dependent on chat interface
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

// Re-export from shared utilities
export * from './chatUIUX-shared-utilities';

// Re-export testing library functions
export { screen, fireEvent, waitFor, userEvent };

// ============================================================================
// ADDITIONAL MOCK FACTORIES
// ============================================================================

/**
 * Create auth store mock
 */
export function createAuthStoreMock(overrides: any = {}) {
  return {
    user: { id: 'test-user', email: 'test@example.com', name: 'Test User' },
    token: 'test-token',
    isAuthenticated: true,
    isLoading: false,
    error: null,
    setUser: jest.fn(),
    setToken: jest.fn(),
    logout: jest.fn(),
    checkAuth: jest.fn(),
    login: jest.fn(),
    refreshToken: jest.fn(),
    ...overrides
  };
}

/**
 * Create chat store mock
 */
export function createChatStoreMock(overrides: any = {}) {
  return {
    messages: [],
    isLoading: false,
    isProcessing: false,
    error: null,
    sendMessage: jest.fn(),
    clearMessages: jest.fn(),
    addMessage: jest.fn(),
    updateMessage: jest.fn(),
    setMessages: jest.fn(),
    ...overrides
  };
}

/**
 * Create unified chat store mock
 */
export function createUnifiedChatStoreMock(overrides: any = {}) {
  return {
    messages: [],
    threads: [],
    currentThreadId: null,
    activeThreadId: null,
    isLoading: false,
    isProcessing: false,
    error: null,
    sendMessage: jest.fn(),
    loadMessages: jest.fn(),
    createThread: jest.fn(),
    setCurrentThread: jest.fn(),
    setActiveThread: jest.fn(),
    deleteThread: jest.fn(),
    addMessage: jest.fn(),
    setProcessing: jest.fn(),
    addOptimisticMessage: jest.fn(),
    updateOptimisticMessage: jest.fn(),
    removeOptimisticMessage: jest.fn(),
    clearOptimisticMessages: jest.fn(),
    resetLayers: jest.fn(),
    setConnectionStatus: jest.fn(),
    setThreadLoading: jest.fn(),
    startThreadLoading: jest.fn(),
    completeThreadLoading: jest.fn(),
    clearMessages: jest.fn(),
    ...overrides
  };
}

/**
 * Create thread store mock
 */
export function createThreadStoreMock(overrides: any = {}) {
  return {
    threads: [],
    currentThread: null,
    currentThreadId: null,
    loading: false,
    error: null,
    setThreads: jest.fn(),
    setCurrentThread: jest.fn(),
    setCurrentThreadId: jest.fn(),
    addThread: jest.fn(),
    deleteThread: jest.fn(),
    updateThread: jest.fn(),
    loadThreads: jest.fn(),
    setError: jest.fn(),
    autoRenameThread: jest.fn(),
    ...overrides
  };
}

/**
 * Create WebSocket mock
 */
export function createWebSocketMock() {
  return {
    connectionState: 'connected',
    sendMessage: jest.fn(),
    subscribe: jest.fn(),
    unsubscribe: jest.fn(),
    reconnect: jest.fn(),
    disconnect: jest.fn(),
    isConnected: true,
    error: null
  };
}

/**
 * Create thread service mock
 */
export function createThreadServiceMock() {
  return {
    listThreads: jest.fn().mockResolvedValue([]),
    loadThreads: jest.fn().mockResolvedValue([]),
    createThread: jest.fn().mockResolvedValue({ id: 'new-thread', title: 'New Thread' }),
    deleteThread: jest.fn().mockResolvedValue(true),
    updateThread: jest.fn().mockResolvedValue(true),
    getThread: jest.fn().mockResolvedValue(null),
    getThreadMessages: jest.fn().mockResolvedValue([])
  };
}

/**
 * Create test message
 */
export function createTestMessage(role: 'user' | 'assistant' | 'system' = 'user', content: string = 'Test message') {
  return {
    id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    thread_id: 'test-thread',
    role,
    content,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    is_streaming: false
  };
}

/**
 * Create test thread
 */
export function createTestThread(overrides: any = {}) {
  const id = overrides.id || `thread_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  return {
    id,
    title: overrides.title || `Test Thread ${id.slice(-8)}`,
    name: overrides.name || overrides.title || `Test Thread ${id.slice(-8)}`,
    user_id: overrides.user_id || `user_${Date.now()}`,
    created_at: overrides.created_at || new Date().toISOString(),
    updated_at: overrides.updated_at || new Date().toISOString(),
    message_count: overrides.message_count || 0,
    is_active: overrides.is_active !== false,
    status: overrides.status || 'active',
    ...overrides
  };
}

// ============================================================================
// SETUP AND CLEANUP FUNCTIONS
// ============================================================================

/**
 * Setup default mocks for all tests
 */
export function setupDefaultMocks(): void {
  // Mock console methods to reduce noise
  global.console.warn = jest.fn();
  global.console.error = jest.fn();
  
  // Mock window.confirm for delete confirmations
  global.confirm = jest.fn(() => true);
  
  // Mock ResizeObserver
  global.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  };

  // Mock clipboard API
  Object.defineProperty(navigator, 'clipboard', {
    writable: true,
    value: {
      writeText: jest.fn().mockResolvedValue(undefined),
      readText: jest.fn().mockResolvedValue('')
    }
  });

  // Mock window.matchMedia
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: jest.fn().mockImplementation(query => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: jest.fn(),
      removeListener: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      dispatchEvent: jest.fn(),
    })),
  });
}

/**
 * Setup clipboard mock
 */
export function setupClipboardMock(): void {
  Object.defineProperty(navigator, 'clipboard', {
    writable: true,
    value: {
      writeText: jest.fn().mockResolvedValue(undefined),
      readText: jest.fn().mockResolvedValue('')
    }
  });
}

/**
 * Cleanup mocks after tests
 */
export function cleanupMocks(): void {
  jest.clearAllMocks();
  jest.restoreAllMocks();
}

// ============================================================================
// EXPECTATION HELPERS
// ============================================================================

/**
 * Expect element by text
 */
export function expectElementByText(text: string | RegExp): void {
  expect(screen.getByText(text)).toBeInTheDocument();
}

/**
 * Find element by text (returns element for interactions)
 */
export function findElementByText(text: string | RegExp) {
  return screen.getByText(text);
}

/**
 * Expect element by test ID
 */
export function expectElementByTestId(testId: string): void {
  expect(screen.getByTestId(testId)).toBeInTheDocument();
}

/**
 * Find element by test ID (returns element for interactions)
 */
export function findElementByTestId(testId: string) {
  return screen.getByTestId(testId);
}

/**
 * Expect element by role
 */
export function expectElementByRole(role: string, options?: any): void {
  expect(screen.getByRole(role, options)).toBeInTheDocument();
}

/**
 * Find element by role (returns element for interactions)
 */
export function findElementByRole(role: string, options?: any) {
  return screen.getByRole(role, options);
}

/**
 * Wait for element by text
 */
export async function waitForElementByText(text: string | RegExp): Promise<void> {
  await waitFor(() => {
    expect(screen.getByText(text)).toBeInTheDocument();
  });
}

/**
 * Wait for element by role
 */
export async function waitForElementByRole(role: string, options?: any): Promise<void> {
  await waitFor(() => {
    expect(screen.getByRole(role, options)).toBeInTheDocument();
  });
}

// ============================================================================
// MODULE MOCK CONFIGURATIONS
// ============================================================================

/**
 * Pre-configured mock module setups
 */
export const mockModuleConfigs = {
  authStore: () => jest.mock('@/store/authStore', () => ({
    useAuthStore: jest.fn(() => createAuthStoreMock())
  })),
  
  chatStore: () => jest.mock('@/store/chatStore', () => ({
    useChatStore: jest.fn(() => createChatStoreMock())
  })),
  
  threadStore: () => jest.mock('@/store/threadStore', () => ({
    useThreadStore: jest.fn(() => createThreadStoreMock())
  })),
  
  webSocket: () => jest.mock('@/hooks/useWebSocket', () => ({
    useWebSocket: jest.fn(() => createWebSocketMock())
  })),
  
  unifiedChat: () => jest.mock('@/store/unified-chat', () => ({
    useUnifiedChatStore: jest.fn(() => createUnifiedChatStoreMock())
  }))
};