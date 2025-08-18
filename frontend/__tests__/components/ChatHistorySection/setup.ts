/**
 * Core test setup for ChatHistorySection component tests
 * Handles Jest mocks and test configuration
 */

// Hoist all mocks to the top for proper Jest handling
const mockUseUnifiedChatStore = jest.fn();
const mockUseLoadingState = jest.fn();
const mockUseThreadNavigation = jest.fn();
const mockRouter = { push: jest.fn() };
const mockPathname = '/chat';

// Mock all stores and hooks BEFORE imports
jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: mockUseUnifiedChatStore
}));

jest.mock('@/hooks/useLoadingState', () => ({
  useLoadingState: mockUseLoadingState
}));

jest.mock('@/hooks/useThreadNavigation', () => ({
  useThreadNavigation: mockUseThreadNavigation
}));

jest.mock('@/services/threadService', () => ({
  ThreadService: {
    listThreads: jest.fn(),
    getThreadMessages: jest.fn(),
    createThread: jest.fn(),
    updateThread: jest.fn(),
    deleteThread: jest.fn(),
  }
}));

jest.mock('next/navigation', () => ({
  useRouter: () => mockRouter,
  usePathname: () => mockPathname,
}));

jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => React.createElement('div', props, children),
  },
  AnimatePresence: ({ children }: any) => children,
}));

// AuthGate mock - always render children
jest.mock('@/components/ui/auth-gate', () => ({
  AuthGate: ({ children }: { children: React.ReactNode }) => children
}));

import React from 'react';
import '@testing-library/jest-dom';
import { mockThreads, createMockThread } from './mockData';

// Store hook imports after mocks
import { ThreadService } from '@/services/threadService';

// Mock store data
const mockStore = {
  isProcessing: false,
  messages: [],
  threads: mockThreads,
  currentThreadId: 'thread-1',
  isThreadLoading: false,
  loadingStates: {
    isLoading: false,
    shouldShowLoading: false,
    shouldShowEmptyState: false,
    shouldShowExamplePrompts: false,
    loadingMessage: ''
  },
  addMessage: jest.fn(),
  setProcessing: jest.fn(),
  clearMessages: jest.fn(),
  updateThreads: jest.fn(),
  setCurrentThreadId: jest.fn(),
};

// Initialize with authenticated state
const initializeAuthenticatedMocks = () => {
  // Set up default mock return values
  mockUseUnifiedChatStore.mockReturnValue(mockStore);
  
  mockUseLoadingState.mockReturnValue({
    shouldShowLoading: false,
    shouldShowEmptyState: false,
    shouldShowExamplePrompts: false,
    loadingMessage: ''
  });
  
  mockUseThreadNavigation.mockReturnValue({
    currentThreadId: 'thread-1',
    isNavigating: false,
    navigateToThread: jest.fn(),
    createNewThread: jest.fn()
  });
};

// Configure mock implementations
const configureMockImplementations = () => {
  // Configure service mocks
  (ThreadService as any).listThreads = jest.fn().mockResolvedValue(mockThreads);
  (ThreadService as any).getThreadMessages = jest.fn().mockResolvedValue({ messages: [] });
  (ThreadService as any).createThread = jest.fn().mockResolvedValue(mockThreads[0]);
  (ThreadService as any).updateThread = jest.fn().mockResolvedValue(mockThreads[0]);
  (ThreadService as any).deleteThread = jest.fn().mockResolvedValue({ success: true });
};

export class ChatHistoryTestSetup {
  public mockThreads = mockThreads;
  
  beforeEach() {
    jest.clearAllMocks();
    mockRouter.push.mockClear();
    
    // Reset mockThreads to original state
    this.mockThreads = [...mockThreads];
    
    // Initialize fresh authenticated mocks
    initializeAuthenticatedMocks();
    configureMockImplementations();
  }

  afterEach() {
    jest.clearAllMocks();
    
    // Reset any modified state
    this.mockThreads = [...mockThreads];
  }

  configureStoreMocks(config: {
    threads?: any[];
    currentThreadId?: string | null;
    isAuthenticated?: boolean;
  }) {
    const updatedStore = { ...mockStore };
    
    if (config.threads !== undefined) {
      updatedStore.threads = config.threads;
      this.mockThreads = [...config.threads];
    }
    
    if (config.currentThreadId !== undefined) {
      updatedStore.currentThreadId = config.currentThreadId;
    }
    
    mockUseUnifiedChatStore.mockReturnValue(updatedStore);
    
    if (config.currentThreadId !== undefined) {
      mockUseThreadNavigation.mockReturnValue({
        currentThreadId: config.currentThreadId,
        isNavigating: false,
        navigateToThread: jest.fn(),
        createNewThread: jest.fn()
      });
    }
  }

  updateMockThreads(newThreads: typeof mockThreads) {
    this.mockThreads = [...newThreads];
    // Update the store mock with new threads
    this.configureStoreMocks({ threads: this.mockThreads });
  }

  mockLoadingState(isLoading: boolean = true) {
    mockUseLoadingState.mockReturnValue({
      shouldShowLoading: isLoading,
      shouldShowEmptyState: false,
      shouldShowExamplePrompts: false,
      loadingMessage: isLoading ? 'Loading...' : ''
    });
    
    const updatedStore = { ...mockStore, isThreadLoading: isLoading };
    mockUseUnifiedChatStore.mockReturnValue(updatedStore);
  }

  mockErrorState(error: string) {
    const updatedStore = { ...mockStore, error };
    mockUseUnifiedChatStore.mockReturnValue(updatedStore);
  }

  getCurrentMockThreads() {
    return this.mockThreads;
  }

  createMockThread(overrides: Partial<typeof mockThreads[0]> = {}) {
    return createMockThread(overrides);
  }
}

export const createTestSetup = () => new ChatHistoryTestSetup();

// Export commonly used items
export { ThreadService };
export { mockRouter, mockPathname, createMockThread };
export { mockUseUnifiedChatStore, mockUseLoadingState, mockUseThreadNavigation };

// Initialize mocks at module level
initializeAuthenticatedMocks();
configureMockImplementations();