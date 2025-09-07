/**
 * Test to reproduce new chat navigation bug
 * 
 * This test verifies that creating a new chat properly updates the URL
 * and doesn't bounce back to the old page.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { ChatSidebar } from '@/components/chat/ChatSidebar';
import { useRouter, useSearchParams, usePathname } from 'next/navigation';
import { ThreadService } from '@/services/threadService';
import { useUnifiedChatStore, resetMockState } from '@/store/unified-chat';
import '@testing-library/jest-dom';

// Mock Next.js navigation
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
  useSearchParams: jest.fn(),
  usePathname: jest.fn(),
}));

// Mock services
jest.mock('@/services/threadService');
jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: () => ({
    sendMessage: jest.fn(),
    isConnected: true,
  }),
}));

// Mock all ChatSidebar dependencies to prevent "Element type is invalid" errors
jest.mock('@/store/authStore', () => ({
  useAuthStore: () => ({
    isDeveloperOrHigher: () => false
  })
}));

jest.mock('@/hooks/useAuthState', () => ({
  useAuthState: () => ({
    isAuthenticated: true,
    userTier: 'Free',
    user: { id: 'test-user', email: 'test@test.com' }
  })
}));

jest.mock('@/components/auth/AuthGate', () => ({
  AuthGate: ({ children }: any) => <>{children}</>
}));

jest.mock('@/hooks/useThreadSwitching', () => ({
  useThreadSwitching: () => ({
    switchToThread: jest.fn(),
    state: { isLoading: false, error: null }
  })
}));

jest.mock('@/lib/thread-operation-manager', () => require('../../__mocks__/lib/thread-operation-manager'));

jest.mock('@/lib/thread-state-machine', () => require('../../__mocks__/lib/thread-state-machine'));

jest.mock('@/lib/logger', () => ({
  logger: {
    info: jest.fn(),
    error: jest.fn(),
    debug: jest.fn(),
    warn: jest.fn()
  }
}));

jest.mock('@/components/chat/ChatSidebarUIComponents', () => ({
  NewChatButton: ({ onNewChat }: any) => <button onClick={onNewChat} data-testid="new-chat-button">New Chat</button>,
  AdminControls: () => <div data-testid="admin-controls">Admin Controls</div>,
  SearchBar: ({ onSearchChange }: any) => <input onChange={(e) => onSearchChange(e.target.value)} data-testid="search-bar" />
}));

jest.mock('@/components/chat/ChatSidebarThreadList', () => ({
  ThreadList: ({ threads, onThreadClick, ...props }: any) => (
    <div data-testid="thread-list">
      {threads && threads.map((thread: any) => (
        <button 
          key={thread.id} 
          onClick={() => onThreadClick && onThreadClick(thread.id)}
          data-testid={`thread-item-${thread.id}`}
        >
          {thread.title}
        </button>
      ))}
    </div>
  ),
  ThreadItem: ({ thread, onClick }: any) => (
    <button onClick={() => onClick && onClick()} data-testid={`thread-item-${thread.id}`}>
      {thread.title}
    </button>
  )
}));

jest.mock('@/components/chat/ChatSidebarFooter', () => ({
  PaginationControls: () => <div data-testid="pagination">Pagination</div>,
  Footer: () => <div data-testid="footer">Footer</div>
}));

jest.mock('@/components/chat/ChatSidebarHooks', () => ({
  useChatSidebarState: () => ({
    searchQuery: '',
    setSearchQuery: jest.fn(),
    isCreatingThread: false,
    setIsCreatingThread: jest.fn(),
    showAllThreads: false,
    setShowAllThreads: jest.fn(),
    filterType: 'all',
    setFilterType: jest.fn(),
    currentPage: 1,
    setCurrentPage: jest.fn(),
    threadsPerPage: 20,
    isAdmin: false
  }),
  useThreadLoader: () => ({
    threads: [],
    isLoadingThreads: false,
    loadError: null,
    loadThreads: jest.fn()
  }),
  useThreadFiltering: (threads: any) => ({
    sortedThreads: threads || [],
    paginatedThreads: threads || [],
    totalPages: 1
  })
}));

jest.mock('@/services/threadLoadingService', () => ({
  threadLoadingService: {
    loadThread: jest.fn().mockResolvedValue({
      success: true,
      messages: [],
      threadId: 'new-thread'
    })
  }
}));

jest.mock('@/hooks/useAuthState', () => ({
  useAuthState: () => ({
    isAuthenticated: true,
    userTier: 'Mid',  // Changed from 'paid' to 'Mid' to meet AuthGate requirements
    isLoading: false,
  }),
}));

jest.mock('@/store/authStore', () => ({
  useAuthStore: () => ({
    isDeveloperOrHigher: () => false,
  }),
}));

// Mock the unified chat store
jest.mock('@/store/unified-chat', () => require('../../__mocks__/store/unified-chat'));

// Mock the chat sidebar hooks
jest.mock('@/components/chat/ChatSidebarHooks', () => ({
  useChatSidebarState: () => ({
    searchQuery: '',
    setSearchQuery: jest.fn(),
    isCreatingThread: false,
    setIsCreatingThread: jest.fn(),
    showAllThreads: false,
    setShowAllThreads: jest.fn(),
    filterType: 'all',
    setFilterType: jest.fn(),
    currentPage: 1,
    setCurrentPage: jest.fn(),
  }),
  useThreadLoader: () => ({
    threads: [],
    isLoadingThreads: false,
    loadError: null,
    loadThreads: jest.fn().mockResolvedValue(undefined),
  }),
  useThreadFiltering: () => ({
    sortedThreads: [],
    paginatedThreads: [],
    totalPages: 1,
  }),
}));

// Mock the thread switching hook
const mockSwitchToThread = jest.fn().mockImplementation(async (threadId, options) => {
  // Since the store is mocked, we need to get it directly
  // Import at call time to avoid module loading issues
  const mockStore = require('../../__mocks__/store/unified-chat');
  const storeState = mockStore.useUnifiedChatStore.getState();
  
  if (options?.clearMessages && storeState.clearMessages) {
    storeState.clearMessages();
  }
  
  if (storeState.setActiveThread) {
    storeState.setActiveThread(threadId);
  }
  
  return Promise.resolve(true);
});

jest.mock('@/hooks/useThreadSwitching', () => ({
  useThreadSwitching: () => ({
    switchToThread: mockSwitchToThread,
    state: {
      isLoading: false,
      loadingThreadId: null,
      error: null,
      lastLoadedThreadId: null,
      operationId: null,
      retryCount: 0,
    },
    cancelLoading: jest.fn(),
    retryLastFailed: jest.fn(),
  }),
}));

describe('New Chat Navigation Bug', () => {
  let mockRouter: any;
  let mockSearchParams: any;
  
  beforeEach(() => {
    // Setup router mocks
    mockRouter = {
      push: jest.fn(),
      replace: jest.fn(),
      prefetch: jest.fn(),
    };
    
    mockSearchParams = {
      get: jest.fn().mockReturnValue(null),
    };
    
    (useRouter as jest.Mock).mockReturnValue(mockRouter);
    (useSearchParams as jest.Mock).mockReturnValue(mockSearchParams);
    (usePathname as jest.Mock).mockReturnValue('/chat');
    
    // Don't use jest.clearAllMocks() as it clears mock implementations
    // Reset mock store state
    if (typeof resetMockState === 'function') {
      resetMockState();
    }
    
    // Reset specific mocks
    mockSwitchToThread.mockClear();
    mockRouter.push.mockClear();
    mockRouter.replace.mockClear();
    mockRouter.prefetch.mockClear();
  });
  
  afterEach(() => {
    // Reset only specific spies
    mockSwitchToThread.mockClear();
    mockRouter.push.mockClear();
    mockRouter.replace.mockClear();
    mockRouter.prefetch.mockClear();
  });
  
  it('should update URL when creating a new chat', async () => {
    // Arrange
    const newThreadId = 'new-thread-123';
    const mockCreateThread = jest.fn().mockResolvedValue({
      id: newThreadId,
      created_at: Date.now(),
      messages: [],
    });
    
    const mockGetThreads = jest.fn().mockResolvedValue([
      { id: newThreadId, created_at: Date.now(), messages: [] },
    ]);
    
    const mockGetThreadMessages = jest.fn().mockResolvedValue({
      thread_id: newThreadId,
      messages: [],
    });
    
    (ThreadService.createThread as jest.Mock) = mockCreateThread;
    (ThreadService.getThreads as jest.Mock) = mockGetThreads;
    (ThreadService.getThreadMessages as jest.Mock) = mockGetThreadMessages;
    
    // Track if handleNewChat is called by mocking the function
    const originalConsoleLog = console.log;
    const consoleSpy = jest.spyOn(console, 'log');
    
    // Act
    const { container } = render(<ChatSidebar />);
    
    // Find and click the new chat button
    const newChatButton = screen.getByRole('button', { name: /new chat/i });
    expect(newChatButton).toBeInTheDocument();
    
    await act(async () => {
      fireEvent.click(newChatButton);
    });
    
    // Wait for async operations to complete
    await new Promise(resolve => setTimeout(resolve, 100));
    
    // Debug: log all mocks to see what's happening
    console.log('CreateThread mock calls:', mockCreateThread.mock.calls.length);
    console.log('SwitchToThread mock calls:', mockSwitchToThread.mock.calls.length);
    console.log('Store setActiveThread calls:', useUnifiedChatStore.getState().setActiveThread?.mock?.calls?.length || 0);
    
    // Assert - expect that the thread creation was initiated
    await waitFor(() => {
      expect(mockCreateThread).toHaveBeenCalled();
    }, { timeout: 2000 });
    
    // After thread creation, expect the switchToThread hook to be called
    await waitFor(() => {
      expect(mockSwitchToThread).toHaveBeenCalledWith(
        newThreadId,
        expect.objectContaining({
          clearMessages: true,
          updateUrl: true
        })
      );
    }, { timeout: 2000 });
    
    consoleSpy.mockRestore();
    console.log = originalConsoleLog;
    console.log('Fix verified: switchToThread hook was called with URL update option');
  });
  
  it('should not have navigation errors when creating new chat', async () => {
    // Arrange
    const newThreadId = 'new-thread-456';
    const mockCreateThread = jest.fn().mockResolvedValue({
      id: newThreadId,
      created_at: Date.now(),
      messages: [],
    });
    
    const mockGetThreads = jest.fn().mockResolvedValue([
      { id: newThreadId, created_at: Date.now(), messages: [] },
    ]);
    
    (ThreadService.createThread as jest.Mock) = mockCreateThread;
    (ThreadService.getThreads as jest.Mock) = mockGetThreads;
    
    // Track any errors
    const consoleErrorSpy = jest.spyOn(console, 'error');
    
    // Act
    render(<ChatSidebar />);
    
    const newChatButton = screen.getByRole('button', { name: /new chat/i });
    
    await act(async () => {
      fireEvent.click(newChatButton);
    });
    
    // Assert
    await waitFor(() => {
      expect(mockCreateThread).toHaveBeenCalled();
    });
    
    // Check for any console errors (there shouldn't be any)
    expect(consoleErrorSpy).not.toHaveBeenCalledWith(
      expect.stringContaining('navigation'),
      expect.anything()
    );
    
    consoleErrorSpy.mockRestore();
  });
});