/**
 * Shared utilities for Chat UI/UX tests
 * Module-based architecture: Common mocks and setup utilities ≤300 lines
 */

import { TestProviders } from '../test-utils/providers';

// Mock implementations for stores (≤8 lines each)
export const createMockAuthStore = () => ({
  isAuthenticated: false,
  user: null,
  token: null,
  login: jest.fn(),
  logout: jest.fn(),
  setLoading: jest.fn(),
  setError: jest.fn(),
  updateUser: jest.fn()
});

export const createMockChatStore = () => ({
  messages: [],
  loading: false,
  error: null,
  isProcessing: false,
  clearMessages: jest.fn(),
  loadMessages: jest.fn(),
  addMessage: jest.fn(),
  updateMessage: jest.fn()
});

export const createMockThreadStore = () => ({
  threads: [],
  currentThreadId: null,
  loading: false,
  error: null,
  setThreads: jest.fn(),
  setCurrentThread: jest.fn(),
  addThread: jest.fn(),
  updateThread: jest.fn()
});

export const createMockUnifiedChatStore = () => ({
  isProcessing: false,
  messages: [],
  fastLayerData: null,
  mediumLayerData: null,
  slowLayerData: null,
  currentRunId: null,
  sendMessage: jest.fn(),
  clearMessages: jest.fn()
});

// Mock data factories (≤8 lines each)
export const createMockUser = () => ({
  id: 'user-123',
  email: 'test@example.com',
  name: 'Test User'
});

export const createMockMessage = (type = 'user', content = 'Test message') => ({
  id: '1',
  content,
  type,
  created_at: new Date().toISOString(),
  displayed_to_user: true
});

export const createMockThread = (id = 'thread-1', title = 'Test Thread') => ({
  id,
  title,
  created_at: '2025-01-01',
  message_count: 5
});

// Store setup helpers (≤8 lines each)
export const setupAuthenticatedStore = (mockAuthStore: any) => {
  return {
    ...mockAuthStore,
    isAuthenticated: true,
    user: createMockUser(),
    token: 'mock-jwt-token'
  };
};

export const setupUnauthenticatedStore = (mockAuthStore: any) => {
  return {
    ...mockAuthStore,
    isAuthenticated: false,
    user: null,
    token: null
  };
};

export const setupStoreWithMessages = (mockChatStore: any, messages: any[]) => {
  return {
    ...mockChatStore,
    messages,
    isProcessing: false
  };
};

export const setupStoreWithThreads = (mockThreadStore: any, threads: any[]) => {
  return {
    ...mockThreadStore,
    threads
  };
};

// Mock setup functions (≤8 lines each)
export const setupBasicMocks = () => {
  jest.mock('../../store/authStore');
  jest.mock('../../store/chatStore');
  jest.mock('../../store/threadStore');
  jest.mock('../../store/unified-chat');
  jest.mock('../../hooks/useChatWebSocket');
  jest.mock('../../services/threadService');
};

export const setupThreadServiceMocks = () => {
  const { ThreadService } = require('../../services/threadService');
  (ThreadService as any).listThreads = jest.fn().mockResolvedValue([]);
  (ThreadService as any).createThread = jest.fn().mockResolvedValue({ 
    id: 'new-thread', 
    title: 'New Conversation' 
  });
  (ThreadService as any).getThreadMessages = jest.fn().mockResolvedValue({ 
    messages: [] 
  });
};

export const setupConfirmMock = () => {
  global.confirm = jest.fn(() => true);
};

export const cleanupMocks = () => {
  jest.clearAllMocks();
  jest.restoreAllMocks();
};

// Test wrapper helpers (≤8 lines each)
export const renderWithProviders = (component: React.ReactElement) => {
  return (
    <TestProviders>
      {component}
    </TestProviders>
  );
};

export const createStreamingMessage = () => ({
  id: 'streaming-1',
  content: 'Hello world, how are you?',
  type: 'agent',
  isStreaming: true,
  created_at: new Date().toISOString(),
  displayed_to_user: true
});

// Assertion helpers (≤8 lines each)
export const expectChatStructure = () => {
  const container = document.querySelector('.flex.h-full');
  expect(container).toBeInTheDocument();
};

export const expectAuthenticatedStructure = () => {
  const container = document.querySelector('.flex.h-full.bg-gradient-to-br');
  expect(container).toBeInTheDocument();
};

export const expectMessageOrWelcome = (screen: any, messageText?: string) => {
  const message = messageText ? screen.queryByText(messageText) : null;
  const welcome = screen.queryByText(/Welcome to Netra AI/i);
  expect(message || welcome).toBeTruthy();
};

// Mock hook return values
export const mockUseChatWebSocket = () => ({});

export const mockUseAuthStore = () => createMockAuthStore();

export const mockUseChatStore = () => createMockChatStore();

export const mockUseThreadStore = () => createMockThreadStore();

export const mockUseUnifiedChatStore = () => createMockUnifiedChatStore();