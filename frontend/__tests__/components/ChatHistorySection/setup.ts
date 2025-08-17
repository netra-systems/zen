/**
 * Core test setup for ChatHistorySection component tests
 * Handles Jest mocks and test configuration
 */

import { mockRouter, mockPathname, mockThreads, createMockThread } from './mockData';

// CRITICAL: Jest mocks must be hoisted before imports
jest.mock('@/store/threadStore');
jest.mock('@/store/chat');
jest.mock('@/store/authStore');
jest.mock('@/services/threadService');
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

import React from 'react';
import '@testing-library/jest-dom';
import { 
  createMockThreadStore,
  createMockChatStore,
  createMockAuthStore
} from '../../utils/storeMocks.helper';

// Store hook imports after mocks
import { useThreadStore } from '@/store/threadStore';
import { useChatStore } from '@/store/chat';
import { useAuthStore } from '@/store/authStore';
import { ThreadService } from '@/services/threadService';

// Create authenticated mock instances
export let mockThreadStore: ReturnType<typeof createMockThreadStore>;
export let mockChatStore: ReturnType<typeof createMockChatStore>;
export let mockAuthStore: ReturnType<typeof createMockAuthStore>;

// Initialize with authenticated state
const initializeAuthenticatedMocks = () => {
  mockThreadStore = createMockThreadStore({
    threads: mockThreads,
    currentThread: mockThreads[0],
    currentThreadId: 'thread-1'
  });

  mockChatStore = createMockChatStore();

  // CRITICAL: Set isAuthenticated to true for tests
  mockAuthStore = createMockAuthStore({
    isAuthenticated: true,
    user: { id: 'user-1', email: 'test@example.com' },
    token: 'mock-token'
  });
  
  // Ensure the mocks return the authenticated state immediately
  (useAuthStore as jest.Mock).mockReturnValue(mockAuthStore);
  (useThreadStore as jest.Mock).mockReturnValue(mockThreadStore);
  (useChatStore as jest.Mock).mockReturnValue(mockChatStore);
};

// Configure mock implementations
const configureMockImplementations = () => {
  (useThreadStore as jest.Mock).mockReturnValue(mockThreadStore);
  (useChatStore as jest.Mock).mockReturnValue(mockChatStore);
  (useAuthStore as jest.Mock).mockReturnValue(mockAuthStore);

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
    jest.restoreAllMocks();
    
    // Reset any modified state
    this.mockThreads = [...mockThreads];
    
    // Clear any timers or pending async operations
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  }

  configureStoreMocks(config: {
    threads?: any[];
    currentThreadId?: string | null;
    isAuthenticated?: boolean;
  }) {
    if (config.threads !== undefined || config.currentThreadId !== undefined) {
      mockThreadStore = {
        ...mockThreadStore,
        ...(config.threads !== undefined && { threads: config.threads }),
        ...(config.currentThreadId !== undefined && { currentThreadId: config.currentThreadId }),
      };
      (useThreadStore as jest.Mock).mockReturnValue(mockThreadStore);
    }

    if (config.isAuthenticated !== undefined) {
      mockAuthStore = {
        ...mockAuthStore,
        isAuthenticated: config.isAuthenticated,
        ...(config.isAuthenticated && { 
          user: { id: 'user-1', email: 'test@example.com' },
          token: 'mock-token' 
        }),
        ...(!config.isAuthenticated && { 
          user: null,
          token: null 
        }),
      };
      (useAuthStore as jest.Mock).mockReturnValue(mockAuthStore);
    }
  }

  updateMockThreads(newThreads: typeof mockThreads) {
    this.mockThreads = [...newThreads];
    // Update the store mock with new threads
    this.configureStoreMocks({ threads: this.mockThreads });
  }

  mockLoadingState(isLoading: boolean = true) {
    (useThreadStore as jest.Mock).mockReturnValue({
      ...mockThreadStore,
      loading: isLoading,
    });
  }

  mockErrorState(error: string) {
    (useThreadStore as jest.Mock).mockReturnValue({
      ...mockThreadStore,
      error,
    });
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
export { useThreadStore, useChatStore, useAuthStore, ThreadService };
export { mockRouter, mockPathname, createMockThread };

// Initialize mocks at module level
initializeAuthenticatedMocks();
configureMockImplementations();