/**
 * ChatHistorySection Test Setup and Utilities
 * Shared setup, mocks, and utilities for ChatHistorySection component tests
 */

import React from 'react';
import '@testing-library/jest-dom';

import { 
  createMockThreadStore,
  createMockChatStore,
  createMockAuthStore
} from '../../utils/storeMocks.helper';

// Create mock instances at module level
export let mockThreadStore: ReturnType<typeof createMockThreadStore>;
export let mockChatStore: ReturnType<typeof createMockChatStore>;
export let mockAuthStore: ReturnType<typeof createMockAuthStore>;

// Initialize mocks at module level
mockThreadStore = createMockThreadStore({
  threads: mockThreads,
  currentThread: mockThreads[0],
  currentThreadId: 'thread-1'
});

mockChatStore = createMockChatStore();

mockAuthStore = createMockAuthStore({
  isAuthenticated: true
});

// Mock next/navigation
export const mockRouter = {
  push: jest.fn(),
};
export let mockPathname = '/chat';

jest.mock('next/navigation', () => ({
  useRouter: () => mockRouter,
  usePathname: () => mockPathname,
}));

// Mock stores with pre-initialized values
jest.mock('@/store/threadStore', () => ({
  useThreadStore: jest.fn(() => mockThreadStore),
}));

jest.mock('@/store/chat', () => ({
  useChatStore: jest.fn(() => mockChatStore),
}));

jest.mock('@/store/authStore', () => ({
  useAuthStore: jest.fn(() => mockAuthStore),
}));

jest.mock('@/services/threadService', () => ({
  ThreadService: {
    listThreads: jest.fn(),
    getThreadMessages: jest.fn(),
    createThread: jest.fn(),
    updateThread: jest.fn(),
    deleteThread: jest.fn(),
  },
}));

jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
  AnimatePresence: ({ children }: any) => children,
}));

// Import store and service mocks
import { useThreadStore } from '@/store/threadStore';
import { useChatStore } from '@/store/chat';
import { useAuthStore } from '@/store/authStore';
import { ThreadService } from '@/services/threadService';

// Sample mock data
export const mockThreads = [
  {
    id: 'thread-1',
    title: 'First Conversation',
    created_at: Math.floor(Date.now() / 1000),
    updated_at: Math.floor(Date.now() / 1000),
    user_id: 'user-1',
    message_count: 5,
    status: 'active' as const,
  },
  {
    id: 'thread-2',
    title: 'Second Conversation',
    created_at: Math.floor((Date.now() - 86400000) / 1000), // Yesterday
    updated_at: Math.floor((Date.now() - 86400000) / 1000),
    user_id: 'user-1',
    message_count: 3,
    status: 'active' as const,
  },
  {
    id: 'thread-3',
    title: 'Third Conversation',
    created_at: Math.floor((Date.now() - 604800000) / 1000), // Week ago
    updated_at: Math.floor((Date.now() - 604800000) / 1000),
    user_id: 'user-1',
    message_count: 10,
    status: 'active' as const,
  },
];

export class ChatHistoryTestSetup {
  public mockThreads = mockThreads;
  
  beforeEach() {
    jest.clearAllMocks();
    
    // Reset router mocks
    mockRouter.push.mockClear();
    mockPathname = '/chat';
    
    // Create fresh mock instances
    mockThreadStore = createMockThreadStore({
      threads: mockThreads,
      currentThread: mockThreads[0],
      currentThreadId: 'thread-1'
    });
    
    mockChatStore = createMockChatStore();
    
    mockAuthStore = createMockAuthStore({
      isAuthenticated: true
    });
    
    // Configure store mocks with explicit implementation
    (useThreadStore as unknown as jest.Mock).mockImplementation(() => mockThreadStore);
    (useChatStore as unknown as jest.Mock).mockImplementation(() => mockChatStore);
    (useAuthStore as unknown as jest.Mock).mockImplementation(() => mockAuthStore);

    // Configure service mocks
    (ThreadService.listThreads as jest.Mock).mockResolvedValue(mockThreads);
    (ThreadService.getThreadMessages as jest.Mock).mockResolvedValue({ messages: [] });
    (ThreadService.createThread as jest.Mock).mockResolvedValue(mockThreads[0]);
    (ThreadService.updateThread as jest.Mock).mockResolvedValue(mockThreads[0]);
    (ThreadService.deleteThread as jest.Mock).mockResolvedValue({ success: true });
  }

  afterEach() {
    jest.restoreAllMocks();
  }

  // Helper method to configure store mocks with custom data
  configureStoreMocks(config: {
    threads?: any[];
    currentThreadId?: string | null;
    isAuthenticated?: boolean;
  }) {
    // Update mockThreadStore reference if needed
    if (config.threads !== undefined || config.currentThreadId !== undefined) {
      mockThreadStore = {
        ...mockThreadStore,
        ...(config.threads !== undefined && { threads: config.threads }),
        ...(config.currentThreadId !== undefined && { currentThreadId: config.currentThreadId }),
      };
      (useThreadStore as unknown as jest.Mock).mockImplementation(() => mockThreadStore);
    }

    // Update mockAuthStore reference if needed
    if (config.isAuthenticated !== undefined) {
      mockAuthStore = {
        ...mockAuthStore,
        isAuthenticated: config.isAuthenticated,
      };
      (useAuthStore as unknown as jest.Mock).mockImplementation(() => mockAuthStore);
    }
  }

  // Helper to create threads with specific properties
  createMockThread(overrides: Partial<typeof mockThreads[0]> = {}) {
    return {
      id: `thread-${Math.random().toString(36).substr(2, 9)}`,
      title: 'Test Conversation',
      created_at: Math.floor(Date.now() / 1000),
      updated_at: Math.floor(Date.now() / 1000),
      user_id: 'user-1',
      message_count: 0,
      status: 'active' as const,
      ...overrides,
    };
  }

  // Helper to get current mock threads
  getCurrentMockThreads() {
    return this.mockThreads;
  }

  // Helper to update the mock threads reference
  updateMockThreads(newThreads: typeof mockThreads) {
    this.mockThreads = newThreads;
  }

  // Helper to simulate loading states
  mockLoadingState(isLoading: boolean = true) {
    (useThreadStore as unknown as jest.Mock).mockReturnValue({
      ...mockThreadStore,
      loading: isLoading,
    });
  }

  // Helper to simulate error states
  mockErrorState(error: string) {
    (useThreadStore as unknown as jest.Mock).mockReturnValue({
      ...mockThreadStore,
      error,
    });
  }
}

export const createTestSetup = () => new ChatHistoryTestSetup();

// Export commonly used utilities
export { useThreadStore, useChatStore, useAuthStore, ThreadService };

// Utility for finding elements in tests
export const findThreadElement = (container: HTMLElement, title: string) => {
  const threadElement = Array.from(container.querySelectorAll('[data-testid*="thread"]')).find(
    el => el.textContent?.includes(title)
  );
  return threadElement as HTMLElement;
};

// Utility for mocking user interactions
export const mockUserEvent = {
  click: (element: HTMLElement) => {
    element.click();
  },
  
  hover: (element: HTMLElement) => {
    // Simulate hover by adding hover classes if needed
    element.classList.add('hover');
  }
};

// Utility for date formatting tests
export const getExpectedDateFormat = (timestamp: number) => {
  const date = new Date(timestamp * 1000);
  const now = new Date();
  const diffInMs = now.getTime() - date.getTime();
  const diffInHours = diffInMs / (1000 * 60 * 60);

  if (diffInHours < 24) {
    return 'Today';
  } else if (diffInHours < 48) {
    return 'Yesterday';
  } else {
    return date.toLocaleDateString();
  }
};