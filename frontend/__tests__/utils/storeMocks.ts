/**
 * Centralized store mock factory for consistent test mocking
 */

import { generateUniqueId } from '@/lib/utils';

// Types for stores
interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant' | 'system';
  timestamp?: number;
  metadata?: any;
}

interface Thread {
  id: string;
  title: string;
  created_at: number;
  updated_at: number;
  user_id: string;
  message_count: number;
  status: 'active' | 'archived' | 'deleted';
}

// Mock implementations for each store
export const createMockChatStore = (overrides?: Partial<any>) => ({
  messages: [],
  subAgentName: 'Netra Agent',
  currentSubAgent: null,
  subAgentStatus: null,
  subAgentTools: [],
  subAgentProgress: null,
  subAgentError: null,
  subAgentDescription: null,
  subAgentExecutionTime: null,
  queuedSubAgents: [],
  isProcessing: false,
  activeThreadId: null,
  currentRunId: null,
  agentStatus: 'IDLE',
  agentProgress: 0,
  
  // Actions
  addMessage: jest.fn((message: Message) => {
    const store = (useChatStore as any).getState();
    store.messages.push(message);
  }),
  updateMessage: jest.fn(),
  setSubAgentName: jest.fn(),
  setSubAgentStatus: jest.fn(),
  setSubAgent: jest.fn(),
  setProcessing: jest.fn(),
  clearMessages: jest.fn(),
  clearSubAgent: jest.fn(),
  setActiveThread: jest.fn(),
  loadThreadMessages: jest.fn(),
  loadMessages: jest.fn(),
  addError: jest.fn(),
  addErrorMessage: jest.fn(),
  updateAgentStatus: jest.fn(),
  setCurrentRunId: jest.fn(),
  setCurrentSubAgent: jest.fn(),
  reset: jest.fn(() => {
    const store = (useChatStore as any).getState();
    store.messages = [];
    store.isProcessing = false;
    store.currentSubAgent = null;
    store.subAgentStatus = null;
  }),
  ...overrides
});

export const createMockUnifiedChatStore = (overrides?: Partial<any>) => ({
  messages: [],
  threads: [],
  currentThread: null,
  sessionId: generateUniqueId('session'),
  wsConnected: false,
  wsError: null,
  isTyping: false,
  streamingMessage: null,
  performanceMetrics: {
    messageLatency: [],
    renderTime: [],
    memoryUsage: []
  },
  
  // Actions
  addMessage: jest.fn(),
  updateMessage: jest.fn(),
  deleteMessage: jest.fn(),
  setCurrentThread: jest.fn(),
  setWsConnected: jest.fn(),
  setWsError: jest.fn(),
  setIsTyping: jest.fn(),
  setStreamingMessage: jest.fn(),
  updatePerformanceMetrics: jest.fn(),
  clearMessages: jest.fn(),
  reset: jest.fn(() => {
    const store = (useUnifiedChatStore as any).getState();
    store.messages = [];
    store.threads = [];
    store.currentThread = null;
    store.wsConnected = false;
  }),
  ...overrides
});

export const createMockThreadStore = (overrides?: Partial<any>) => ({
  threads: [],
  currentThread: null,
  loading: false,
  error: null,
  
  // Actions
  setThreads: jest.fn(),
  setCurrentThread: jest.fn(),
  addThread: jest.fn(),
  updateThread: jest.fn(),
  deleteThread: jest.fn(),
  setLoading: jest.fn(),
  setError: jest.fn(),
  loadThreads: jest.fn(),
  clearThreads: jest.fn(),
  reset: jest.fn(() => {
    const store = (useThreadStore as any).getState();
    store.threads = [];
    store.currentThread = null;
    store.loading = false;
    store.error = null;
  }),
  ...overrides
});

export const createMockAuthStore = (overrides?: Partial<any>) => ({
  user: null,
  token: null,
  isAuthenticated: false,
  loading: false,
  error: null,
  
  // Actions
  setUser: jest.fn(),
  setToken: jest.fn(),
  setLoading: jest.fn(),
  setError: jest.fn(),
  login: jest.fn(),
  logout: jest.fn(),
  checkAuth: jest.fn(),
  reset: jest.fn(() => {
    const store = (useAuthStore as any).getState();
    store.user = null;
    store.token = null;
    store.isAuthenticated = false;
    store.loading = false;
    store.error = null;
  }),
  ...overrides
});

export const createMockAppStore = (overrides?: Partial<any>) => ({
  isSidebarOpen: true,
  theme: 'light',
  notifications: [],
  
  // Actions
  toggleSidebar: jest.fn(),
  setSidebarOpen: jest.fn(),
  setTheme: jest.fn(),
  addNotification: jest.fn(),
  removeNotification: jest.fn(),
  clearNotifications: jest.fn(),
  reset: jest.fn(),
  ...overrides
});

// Global mock setup helpers
export const setupStoreMocks = () => {
  // Mock chat store from @/store/chat
  jest.mock('@/store/chat', () => ({
    useChatStore: jest.fn(() => createMockChatStore())
  }));
  
  // Mock chat store from @/store/chatStore
  jest.mock('@/store/chatStore', () => ({
    useChatStore: jest.fn(() => createMockChatStore())
  }));
  
  // Mock unified chat store
  jest.mock('@/store/unified-chat', () => ({
    useUnifiedChatStore: jest.fn(() => createMockUnifiedChatStore())
  }));
  
  // Mock thread store
  jest.mock('@/store/threadStore', () => ({
    useThreadStore: jest.fn(() => createMockThreadStore())
  }));
  
  // Mock auth store
  jest.mock('@/store/authStore', () => ({
    useAuthStore: jest.fn(() => createMockAuthStore())
  }));
  
  // Mock app store
  jest.mock('@/store', () => ({
    useAppStore: jest.fn(() => createMockAppStore()),
    useChatStore: jest.fn(() => createMockChatStore())
  }));
  
  // Mock app store from @/store/app
  jest.mock('@/store/app', () => ({
    useAppStore: jest.fn(() => createMockAppStore())
  }));
};

// Helper to reset all store mocks
export const resetAllStoreMocks = () => {
  jest.clearAllMocks();
};

// Helper to get mock store instance
export const getMockStore = (storeName: string) => {
  switch (storeName) {
    case 'chat':
      return createMockChatStore();
    case 'unifiedChat':
      return createMockUnifiedChatStore();
    case 'thread':
      return createMockThreadStore();
    case 'auth':
      return createMockAuthStore();
    case 'app':
      return createMockAppStore();
    default:
      throw new Error(`Unknown store: ${storeName}`);
  }
};

// Export references for direct import mocking
export const useChatStore = jest.fn(() => createMockChatStore());
export const useUnifiedChatStore = jest.fn(() => createMockUnifiedChatStore());
export const useThreadStore = jest.fn(() => createMockThreadStore());
export const useAuthStore = jest.fn(() => createMockAuthStore());
export const useAppStore = jest.fn(() => createMockAppStore());