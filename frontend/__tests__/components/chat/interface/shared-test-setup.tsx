/**
 * Shared Test Setup for Chat Interface Tests
 * ==========================================
 * 
 * Provides consistent mocks, utilities, and test helpers
 * for comprehensive chat interface testing
 * 
 * Architecture: Modular, reusable test infrastructure
 * Compliance: Each function ≤ 8 lines, focused responsibilities
 */

import React, { ReactNode } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { User } from '../../../../types/unified/auth.types';
import { Message } from '../../../../types/domains/messages';

// Types

interface Thread {
  id: string;
  title: string;
  createdAt: string;
  updatedAt?: string;
}

// User interface now imported from @/types/unified/auth.types

interface WebSocketEvent {
  type: string;
  payload: any;
  timestamp?: number;
}

// Mock WebSocket Provider
export const mockWebSocketProvider = () => ({
  connect: jest.fn(),
  disconnect: jest.fn(), 
  send: jest.fn(),
  simulateMessage: jest.fn(),
  simulateDisconnect: jest.fn(),
  simulateReconnect: jest.fn(),
  simulateError: jest.fn(),
  simulateRawMessage: jest.fn()
});

// Mock Unified Chat Store - returns the global mock store so components and tests use same data
export const mockUnifiedChatStore = () => {
  // Make sure global mockStore exists
  if (!(global as any).mockStore) {
    (global as any).mockStore = {
      messages: [],
      threads: [],
      activeThreadId: 'thread1',
      activeThread: null,
      isProcessing: false,
      isAuthenticated: true,
      sendMessage: jest.fn(),
      addMessage: jest.fn(),
      updateMessage: jest.fn(),
      deleteMessage: jest.fn(),
      createThread: jest.fn(),
      addThread: jest.fn(),
      setActiveThread: jest.fn(),
      deleteThread: jest.fn(),
      queueMessage: jest.fn(),
      exportConversation: jest.fn()
    };
  }
  
  // Return the same global mock store object
  return (global as any).mockStore;
};

// Mock Auth Store
export const mockAuthStore = () => ({
  user: { 
    id: 'test-user', 
    email: 'test@example.com', 
    full_name: 'Test User' 
  } as User,
  token: 'test-token',
  isAuthenticated: true,
  setUser: jest.fn(),
  setToken: jest.fn(),
  logout: jest.fn(),
  checkAuth: jest.fn()
});

// Mock Thread Store
export const mockThreadStore = () => ({
  threads: [],
  currentThreadId: 'thread1',
  currentThread: null,
  setThreads: jest.fn(),
  setCurrentThread: jest.fn(),
  addThread: jest.fn(),
  updateThread: jest.fn(),
  deleteThread: jest.fn()
});

// Create Mock Message Helper
export const createMockMessage = (
  content: string, 
  role: 'user' | 'assistant' | 'system' = 'user',
  overrides: Partial<Message> = {}
): Message => ({
  id: `msg-${Math.random().toString(36).substr(2, 9)}`,
  content,
  role,
  timestamp: Date.now(),
  created_at: new Date().toISOString(),
  threadId: 'thread1',
  ...overrides
});

// Create Mock Thread Helper  
export const createMockThread = (
  title: string,
  overrides: Partial<Thread> = {}
): Thread => ({
  id: `thread-${Math.random().toString(36).substr(2, 9)}`,
  title,
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
  ...overrides
});

// Simple Test Wrapper Component
interface TestProvidersProps {
  children: ReactNode;
  mockStore?: any;
  mockAuth?: any;
  mockWebSocket?: any;
}

export const TestProviders: React.FC<TestProvidersProps> = ({
  children,
  mockStore = mockUnifiedChatStore(),
  mockAuth = mockAuthStore(),
  mockWebSocket = mockWebSocketProvider()
}) => {
  // Simple wrapper without complex providers for testing
  return <div data-testid="test-provider">{children}</div>;
};

// Custom Render with Providers
export const renderWithProviders = (
  ui: ReactNode,
  options?: Omit<RenderOptions, 'wrapper'> & {
    mockStore?: any;
    mockAuth?: any;
    mockWebSocket?: any;
  }
) => {
  const { mockStore, mockAuth, mockWebSocket, ...renderOptions } = options || {};
  
  const Wrapper = ({ children }: { children: ReactNode }) => (
    <TestProviders 
      mockStore={mockStore}
      mockAuth={mockAuth} 
      mockWebSocket={mockWebSocket}
    >
      {children}
    </TestProviders>
  );

  return render(ui, { wrapper: Wrapper, ...renderOptions });
};

// WebSocket Event Creators
export const createWebSocketEvent = (
  type: string,
  payload: any
): WebSocketEvent => ({
  type,
  payload,
  timestamp: Date.now()
});

export const createMessageEvent = (message: Message): WebSocketEvent =>
  createWebSocketEvent('message', message);

export const createStreamStartEvent = (messageId: string): WebSocketEvent =>
  createWebSocketEvent('stream_start', { messageId });

export const createStreamChunkEvent = (
  messageId: string,
  content: string,
  isComplete = false
): WebSocketEvent => createWebSocketEvent('stream_chunk', {
  messageId,
  content,
  isComplete
});

export const createAgentStatusEvent = (
  agentId: string,
  status: string,
  task?: string
): WebSocketEvent => createWebSocketEvent('agent_status_update', {
  agentId,
  status,
  task
});

// Mock Setup Helpers
export const setupMessageInputMocks = () => {
  // Mock clipboard API
  Object.assign(navigator, {
    clipboard: {
      writeText: jest.fn().mockResolvedValue(undefined),
      readText: jest.fn().mockResolvedValue('')
    }
  });

  // Mock file API
  Object.defineProperty(window, 'File', {
    value: class MockFile {
      constructor(public name: string, public size = 1024) {}
    }
  });
};

export const setupLocalStorageMocks = () => {
  const mockStorage: { [key: string]: string } = {};
  
  Object.defineProperty(window, 'localStorage', {
    value: {
      getItem: jest.fn((key: string) => mockStorage[key] || null),
      setItem: jest.fn((key: string, value: string) => {
        mockStorage[key] = value;
      }),
      removeItem: jest.fn((key: string) => {
        delete mockStorage[key];
      }),
      clear: jest.fn(() => {
        Object.keys(mockStorage).forEach(key => delete mockStorage[key]);
      })
    }
  });

  return mockStorage;
};

export const setupNetworkMocks = () => {
  Object.defineProperty(navigator, 'onLine', {
    writable: true,
    value: true
  });

  const originalAddEventListener = window.addEventListener;
  const originalRemoveEventListener = window.removeEventListener;
  
  window.addEventListener = jest.fn();
  window.removeEventListener = jest.fn();
  
  return { originalAddEventListener, originalRemoveEventListener };
};

// Cleanup Helpers
export const cleanupMocks = () => {
  jest.clearAllMocks();
  jest.restoreAllMocks();
};

export const waitForWebSocketConnection = async () => {
  await new Promise(resolve => setTimeout(resolve, 100));
};

export const simulateNetworkError = () => {
  Object.defineProperty(navigator, 'onLine', {
    writable: true,
    value: false
  });
  window.dispatchEvent(new Event('offline'));
};

export const simulateNetworkRecovery = () => {
  Object.defineProperty(navigator, 'onLine', {
    writable: true,
    value: true
  });
  window.dispatchEvent(new Event('online'));
};

// Default Exports for Common Use
export default {
  TestProviders,
  renderWithProviders,
  mockUnifiedChatStore,
  mockAuthStore,
  mockWebSocketProvider,
  createMockMessage,
  createMockThread,
  setupMessageInputMocks,
  setupLocalStorageMocks,
  cleanupMocks
};