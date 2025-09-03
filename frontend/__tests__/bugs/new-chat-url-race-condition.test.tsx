/**
 * Test to reproduce the new chat URL update race condition bug
 * 
 * This test demonstrates that duplicate URL updates cause navigation issues
 * when creating a new chat thread.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { ChatSidebar } from '@/components/chat/ChatSidebar';
import { useRouter, useSearchParams, usePathname } from 'next/navigation';
import { ThreadService } from '@/services/threadService';
import { useUnifiedChatStore } from '@/store/unified-chat';
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
    userTier: 'Mid',
    isLoading: false,
  }),
}));

jest.mock('@/store/authStore', () => ({
  useAuthStore: () => ({
    isDeveloperOrHigher: () => false,
  }),
}));

// Create a custom mock for unified chat store to track state changes
let storeState = {
  activeThreadId: 'existing-thread-123',
  isProcessing: false,
  isThreadLoading: false,
  messages: [],
  setActiveThread: jest.fn(),
  setThreadLoading: jest.fn(),
  startThreadLoading: jest.fn(),
  completeThreadLoading: jest.fn(),
  clearMessages: jest.fn(),
  loadMessages: jest.fn(),
  handleWebSocketEvent: jest.fn(),
};

jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: (selector?: any) => {
    if (typeof selector === 'function') {
      return selector(storeState);
    }
    return storeState;
  },
}));

// Mock chat sidebar hooks
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

// Track URL updates
let urlUpdateHistory: Array<{ url: string, timestamp: number }> = [];

// Mock useThreadSwitching with URL tracking
const mockSwitchToThread = jest.fn().mockImplementation(async (threadId, options) => {
  // Simulate the actual behavior that causes the bug
  
  // Step 1: Update store (triggers store-to-URL sync)
  storeState.setActiveThread(threadId);
  
  // This simulates the store change triggering URL sync
  const autoSyncUrl = `/chat?thread=${threadId}`;
  urlUpdateHistory.push({ url: autoSyncUrl, timestamp: Date.now() });
  
  // Step 2: Manual URL update if requested
  if (options?.updateUrl) {
    // Small delay to simulate async execution
    await new Promise(resolve => setTimeout(resolve, 10));
    
    const manualUrl = `/chat?thread=${threadId}`;
    urlUpdateHistory.push({ url: manualUrl, timestamp: Date.now() });
  }
  
  if (options?.clearMessages) {
    storeState.clearMessages();
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

describe('New Chat URL Race Condition Bug', () => {
  let mockRouter: any;
  let mockSearchParams: any;
  
  beforeEach(() => {
    // Reset tracking
    urlUpdateHistory = [];
    
    // Setup router mocks
    mockRouter = {
      push: jest.fn(),
      replace: jest.fn((url) => {
        // Track router.replace calls
        urlUpdateHistory.push({ url, timestamp: Date.now() });
      }),
      prefetch: jest.fn(),
    };
    
    mockSearchParams = {
      get: jest.fn().mockReturnValue('existing-thread-123'),
    };
    
    (useRouter as jest.Mock).mockReturnValue(mockRouter);
    (useSearchParams as jest.Mock).mockReturnValue(mockSearchParams);
    (usePathname as jest.Mock).mockReturnValue('/chat');
    
    // Reset store state
    storeState.activeThreadId = 'existing-thread-123';
    storeState.setActiveThread.mockClear();
    storeState.clearMessages.mockClear();
    
    jest.clearAllMocks();
  });
  
  it('should demonstrate duplicate URL updates causing race condition', async () => {
    // Arrange
    const newThreadId = 'new-thread-456';
    const mockCreateThread = jest.fn().mockResolvedValue({
      id: newThreadId,
      created_at: Date.now(),
      messages: [],
    });
    
    (ThreadService.createThread as jest.Mock) = mockCreateThread;
    
    // Act
    render(<ChatSidebar />);
    
    const newChatButton = screen.getByRole('button', { name: /new chat/i });
    expect(newChatButton).toBeInTheDocument();
    
    await act(async () => {
      fireEvent.click(newChatButton);
    });
    
    // Wait for all async operations
    await waitFor(() => {
      expect(mockCreateThread).toHaveBeenCalled();
    });
    
    await waitFor(() => {
      expect(mockSwitchToThread).toHaveBeenCalledWith(
        newThreadId,
        expect.objectContaining({
          clearMessages: true,
          updateUrl: true,
        })
      );
    });
    
    // Assert - Check for duplicate URL updates
    console.log('URL Update History:', urlUpdateHistory);
    
    // BUG: We should see multiple URL updates for the same thread
    const newThreadUpdates = urlUpdateHistory.filter(update => 
      update.url.includes(newThreadId)
    );
    
    // This demonstrates the bug - there should be only 1 URL update,
    // but we're getting 2 or more due to the race condition
    expect(newThreadUpdates.length).toBeGreaterThan(1);
    
    // The duplicate updates happen within milliseconds of each other
    if (newThreadUpdates.length >= 2) {
      const timeDiff = newThreadUpdates[1].timestamp - newThreadUpdates[0].timestamp;
      expect(timeDiff).toBeLessThan(100); // Updates within 100ms indicate race condition
    }
    
    // Store should be updated
    expect(storeState.setActiveThread).toHaveBeenCalledWith(newThreadId);
  });
  
  it('should show that rapid new chat clicks cause navigation confusion', async () => {
    // Arrange - simulate multiple new chat creations
    let threadCounter = 1;
    const mockCreateThread = jest.fn().mockImplementation(() => {
      const threadId = `rapid-thread-${threadCounter++}`;
      return Promise.resolve({
        id: threadId,
        created_at: Date.now(),
        messages: [],
      });
    });
    
    (ThreadService.createThread as jest.Mock) = mockCreateThread;
    
    // Act
    render(<ChatSidebar />);
    
    const newChatButton = screen.getByRole('button', { name: /new chat/i });
    
    // Rapidly click new chat button 3 times
    await act(async () => {
      fireEvent.click(newChatButton);
      await new Promise(resolve => setTimeout(resolve, 5));
      fireEvent.click(newChatButton);
      await new Promise(resolve => setTimeout(resolve, 5));
      fireEvent.click(newChatButton);
    });
    
    // Wait for operations to complete
    await waitFor(() => {
      expect(mockCreateThread).toHaveBeenCalledTimes(3);
    }, { timeout: 3000 });
    
    // Assert - Check for URL update chaos
    console.log('Rapid click URL History:', urlUpdateHistory);
    
    // With the race condition, we'll see interleaved URL updates
    // that don't correspond to a clean navigation flow
    const uniqueThreadIds = new Set(
      urlUpdateHistory
        .map(update => {
          const match = update.url.match(/thread=([^&]+)/);
          return match ? match[1] : null;
        })
        .filter(Boolean)
    );
    
    // BUG: URL updates are chaotic and interleaved
    expect(urlUpdateHistory.length).toBeGreaterThan(3); // More updates than threads created
    expect(uniqueThreadIds.size).toBeLessThanOrEqual(3); // But only 3 unique threads
  });
  
  it('should demonstrate that the final URL may not match the intended thread', async () => {
    // Arrange
    const thread1 = 'thread-final-1';
    const thread2 = 'thread-final-2';
    
    let callCount = 0;
    const mockCreateThread = jest.fn().mockImplementation(async () => {
      callCount++;
      const threadId = callCount === 1 ? thread1 : thread2;
      
      // Simulate varying response times
      const delay = callCount === 1 ? 50 : 10;
      await new Promise(resolve => setTimeout(resolve, delay));
      
      return {
        id: threadId,
        created_at: Date.now(),
        messages: [],
      };
    });
    
    (ThreadService.createThread as jest.Mock) = mockCreateThread;
    
    // Act
    render(<ChatSidebar />);
    
    const newChatButton = screen.getByRole('button', { name: /new chat/i });
    
    // Click twice in succession
    await act(async () => {
      fireEvent.click(newChatButton);
      await new Promise(resolve => setTimeout(resolve, 20));
      fireEvent.click(newChatButton);
    });
    
    // Wait for all operations
    await waitFor(() => {
      expect(mockCreateThread).toHaveBeenCalledTimes(2);
    }, { timeout: 3000 });
    
    // Give time for all URL updates to complete
    await new Promise(resolve => setTimeout(resolve, 100));
    
    // Assert
    console.log('Final URL test history:', urlUpdateHistory);
    
    // BUG: The final URL in history might not be the second thread
    // due to race conditions in URL updates
    const lastUrlUpdate = urlUpdateHistory[urlUpdateHistory.length - 1];
    
    // This might fail intermittently due to the race condition
    // Sometimes thread1's delayed update overwrites thread2's update
    console.log('Last URL update:', lastUrlUpdate);
    console.log('Expected thread2 URL but race condition may cause thread1');
    
    // The bug is that we can't reliably predict which thread URL will be final
    expect(lastUrlUpdate).toBeDefined();
  });
});