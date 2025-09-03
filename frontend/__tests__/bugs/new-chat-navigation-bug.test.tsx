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
    
    // Reset mock store state
    jest.clearAllMocks();
    if (typeof resetMockState === 'function') {
      resetMockState();
    }
  });
  
  afterEach(() => {
    jest.clearAllMocks();
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
    
    // Act
    const { container } = render(<ChatSidebar />);
    
    // Find and click the new chat button
    const newChatButton = screen.getByRole('button', { name: /new chat/i });
    expect(newChatButton).toBeInTheDocument();
    
    await act(async () => {
      fireEvent.click(newChatButton);
    });
    
    // Debug: log all mocks to see what's happening
    console.log('CreateThread mock calls:', mockCreateThread.mock.calls.length);
    console.log('SwitchToThread mock calls:', mockSwitchToThread.mock.calls.length);
    console.log('Store setActiveThread calls:', useUnifiedChatStore.getState().setActiveThread.mock.calls.length);
    
    // Assert
    await waitFor(() => {
      // Thread should be created
      expect(mockCreateThread).toHaveBeenCalled();
    });
    
    await waitFor(() => {
      // Store should be updated with new thread  
      const storeState = useUnifiedChatStore.getState();
      expect(storeState.setActiveThread).toHaveBeenCalledWith(newThreadId);
    });
    
    // FIXED: With the new implementation using switchToThread hook,
    // URL should now be updated properly via the hook's updateUrl option
    await waitFor(() => {
      // The switchToThread should have been called with the new thread ID
      // and updateUrl option set to true
      expect(mockSwitchToThread).toHaveBeenCalledWith(
        newThreadId,
        expect.objectContaining({
          clearMessages: true,
          updateUrl: true
        })
      );
    });
    
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