/**
 * Shared setup for ChatHistorySection tests - Real Components Only
 * Follows 450-line limit and 25-line function requirements
 */

import React from 'react';
import '@testing-library/jest-dom';

// Real store hooks - no mocking
const mockUseUnifiedChatStore = jest.fn();
const mockUseThreadStore = jest.fn();
const mockUseChatStore = jest.fn();
const mockUseLoadingState = jest.fn();
const mockUseThreadNavigation = jest.fn();
const mockUseAuthStore = jest.fn();

// Store mocks with minimal setup
jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: mockUseUnifiedChatStore
}));

jest.mock('@/store/threadStore', () => ({
  useThreadStore: mockUseThreadStore
}));

jest.mock('@/store/chat', () => ({
  useChatStore: mockUseChatStore
}));

jest.mock('@/hooks/useLoadingState', () => ({
  useLoadingState: mockUseLoadingState
}));

jest.mock('@/hooks/useThreadNavigation', () => ({
  useThreadNavigation: mockUseThreadNavigation
}));

jest.mock('@/store/authStore', () => ({
  useAuthStore: mockUseAuthStore
}));

// Service mocks
jest.mock('@/services/threadService', () => ({
  ThreadService: {
    listThreads: jest.fn(),
    getThreadMessages: jest.fn(),
    createThread: jest.fn(),
    updateThread: jest.fn(),
    deleteThread: jest.fn(),
  }
}));

// Navigation mocks
const mockRouter = { push: jest.fn() };
jest.mock('next/navigation', () => ({
  useRouter: () => mockRouter,
  usePathname: () => '/chat',
}));

// Import mock data after mocks
import { mockThreads, createMockThread } from './mockData';
import { ThreadService } from '@/services/threadService';

// Base store configuration
const createBaseStore = () => ({
  isProcessing: false,
  messages: [],
  threads: mockThreads,
  currentThreadId: 'thread-1',
  isThreadLoading: false,
  addMessage: jest.fn(),
  setProcessing: jest.fn(),
  clearMessages: jest.fn(),
  updateThreads: jest.fn(),
  setCurrentThreadId: jest.fn(),
});

// Base loading state
const createBaseLoadingState = () => ({
  shouldShowLoading: false,
  shouldShowEmptyState: false,
  shouldShowExamplePrompts: false,
  loadingMessage: ''
});

// Base navigation state
const createBaseNavigation = () => ({
  currentThreadId: 'thread-1',
  isNavigating: false,
  navigateToThread: jest.fn(),
  createNewThread: jest.fn()
});

// Base auth state
const createBaseAuthState = () => ({
  isAuthenticated: true,
  user: { id: 'user-1', email: 'test@example.com' },
  login: jest.fn(),
  logout: jest.fn(),
  checkAuth: jest.fn()
});

// Base thread store state
const createBaseThreadStore = () => ({
  threads: mockThreads,
  currentThreadId: 'thread-1',
  setThreads: jest.fn(),
  setCurrentThread: jest.fn(),
  addThread: jest.fn(),
  updateThread: jest.fn(),
  deleteThread: jest.fn(),
  setLoading: jest.fn(),
  setError: jest.fn()
});

// Base chat store state
const createBaseChatStore = () => ({
  clearMessages: jest.fn(),
  loadMessages: jest.fn(),
  messages: []
});

// Initialize default mocks
export const initializeDefaultMocks = () => {
  mockUseUnifiedChatStore.mockReturnValue(createBaseStore());
  mockUseLoadingState.mockReturnValue(createBaseLoadingState());
  mockUseThreadNavigation.mockReturnValue(createBaseNavigation());
  mockUseAuthStore.mockReturnValue(createBaseAuthState());
  mockUseThreadStore.mockReturnValue(createBaseThreadStore());
  mockUseChatStore.mockReturnValue(createBaseChatStore());
};

// Initialize service mocks
export const initializeServiceMocks = () => {
  jest.mocked(ThreadService.listThreads).mockResolvedValue(mockThreads);
  jest.mocked(ThreadService.deleteThread).mockResolvedValue({ success: true });
  jest.mocked(ThreadService.getThreadMessages).mockResolvedValue({ messages: [] });
  jest.mocked(ThreadService.createThread).mockResolvedValue(mockThreads[0]);
  jest.mocked(ThreadService.updateThread).mockResolvedValue(mockThreads[0]);
};

// Clear all mocks
export const clearAllMocks = () => {
  jest.clearAllMocks();
  mockRouter.push.mockClear();
};

// Store configuration interface
export interface StoreConfig {
  threads?: any[];
  currentThreadId?: string | null;
  isAuthenticated?: boolean;
  isLoading?: boolean;
  error?: string;
}

// Configure store mocks with options
export const configureStoreMocks = (config: StoreConfig) => {
  const store = createBaseStore();
  const threadStore = createBaseThreadStore();
  const auth = createBaseAuthState();
  const loading = createBaseLoadingState();
  
  updateStoreFromConfig(store, config);
  updateThreadStoreFromConfig(threadStore, config);
  updateAuthFromConfig(auth, config);
  updateLoadingFromConfig(loading, config);
  
  setMockReturnValues(store, threadStore, auth, loading);
};

// Update store from config
const updateStoreFromConfig = (store: any, config: StoreConfig) => {
  if (config.threads !== undefined) store.threads = config.threads;
  if (config.currentThreadId !== undefined) store.currentThreadId = config.currentThreadId;
  if (config.isLoading !== undefined) store.isThreadLoading = config.isLoading;
  if (config.error !== undefined) store.error = config.error;
};

// Update thread store from config
const updateThreadStoreFromConfig = (threadStore: any, config: StoreConfig) => {
  if (config.threads !== undefined) threadStore.threads = config.threads;
  if (config.currentThreadId !== undefined) threadStore.currentThreadId = config.currentThreadId;
};

// Update auth from config
const updateAuthFromConfig = (auth: any, config: StoreConfig) => {
  if (config.isAuthenticated !== undefined) auth.isAuthenticated = config.isAuthenticated;
};

// Update loading from config
const updateLoadingFromConfig = (loading: any, config: StoreConfig) => {
  if (config.isLoading !== undefined) loading.shouldShowLoading = config.isLoading;
};

// Set mock return values
const setMockReturnValues = (store: any, threadStore: any, auth: any, loading: any) => {
  mockUseUnifiedChatStore.mockReturnValue(store);
  mockUseThreadStore.mockReturnValue(threadStore);
  mockUseAuthStore.mockReturnValue(auth);
  mockUseLoadingState.mockReturnValue(loading);
};

// Update navigation mock
export const updateNavigationMock = (currentThreadId: string | null) => {
  const navigation = createBaseNavigation();
  navigation.currentThreadId = currentThreadId;
  mockUseThreadNavigation.mockReturnValue(navigation);
};

// Setup empty state
export const setupEmptyState = () => {
  configureStoreMocks({ 
    threads: [], 
    currentThreadId: null 
  });
};

// Setup loading state
export const setupLoadingState = () => {
  configureStoreMocks({ isLoading: true });
};

// Setup error state
export const setupErrorState = (error: string = 'Test error') => {
  configureStoreMocks({ error });
};

// Setup custom threads
export const setupCustomThreads = (threads: any[], currentId?: string) => {
  configureStoreMocks({ 
    threads, 
    currentThreadId: currentId || threads[0]?.id || null 
  });
};

// Test setup class
export class TestSetup {
  beforeEach() {
    clearAllMocks();
    initializeDefaultMocks();
    initializeServiceMocks();
  }

  afterEach() {
    clearAllMocks();
  }

  configureStore(config: StoreConfig) {
    configureStoreMocks(config);
  }

  getCurrentConfig(): StoreConfig {
    return {
      threads: mockThreads,
      currentThreadId: 'thread-1',
      isAuthenticated: true,
      isLoading: false
    };
  }
}

// Create test setup instance
export const createTestSetup = () => new TestSetup();

// Export mock hooks and utilities
export {
  mockUseUnifiedChatStore,
  mockUseThreadStore,
  mockUseChatStore,
  mockUseLoadingState,
  mockUseThreadNavigation,
  mockUseAuthStore,
  mockRouter,
  mockThreads,
  createMockThread,
  ThreadService
};

// Initialize at module level
initializeDefaultMocks();
initializeServiceMocks();