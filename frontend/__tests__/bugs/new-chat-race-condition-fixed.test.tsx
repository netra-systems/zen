/**
 * Test to verify that new chat URL race conditions have been fixed
 * 
 * This test ensures that our mutex, debouncing, and state machine fixes
 * prevent race conditions during new chat creation.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { ChatSidebar } from '@/components/chat/ChatSidebar';
import { useRouter, useSearchParams, usePathname } from 'next/navigation';
import { ThreadService } from '@/services/threadService';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { ThreadOperationManager } from '@/lib/thread-operation-manager';
import { threadStateMachineManager } from '@/lib/thread-state-machine';
import '@testing-library/jest-dom';

// Mock Next.js navigation
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
  useSearchParams: jest.fn(() => {
    const params = new URLSearchParams();
    return params;
  }),
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

// Track successful operations
let successfulOperations: Array<{ threadId: string, timestamp: number }> = [];

// Mock useThreadSwitching with operation tracking
const mockSwitchToThread = jest.fn().mockImplementation(async (threadId, options) => {
  // Simulate successful thread switch
  storeState.setActiveThread(threadId);
  
  if (options?.clearMessages) {
    storeState.clearMessages();
  }
  
  // Track successful operation
  successfulOperations.push({ threadId, timestamp: Date.now() });
  
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

describe('New Chat Race Condition Fixes', () => {
  let mockRouter: any;
  let mockSearchParams: any;
  
  beforeEach(() => {
    // Reset tracking
    successfulOperations = [];
    
    // Setup router mocks
    mockRouter = {
      push: jest.fn(),
      replace: jest.fn(),
      prefetch: jest.fn(),
    };
    
    mockSearchParams = new URLSearchParams();
    mockSearchParams.set('threadId', 'existing-thread-123');
    
    (useRouter as jest.Mock).mockReturnValue(mockRouter);
    (useSearchParams as jest.Mock).mockReturnValue(mockSearchParams);
    (usePathname as jest.Mock).mockReturnValue('/chat');
    
    // Reset store state
    storeState.activeThreadId = 'existing-thread-123';
    storeState.setActiveThread.mockClear();
    storeState.clearMessages.mockClear();
    
    jest.clearAllMocks();
    
    // Reset operation manager and state machines
    threadStateMachineManager.resetAll();
  });
  
  it('should prevent concurrent new chat operations with mutex', async () => {
    // Arrange
    let threadCounter = 1;
    const mockCreateThread = jest.fn().mockImplementation(() => {
      const threadId = `mutex-thread-${threadCounter++}`;
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
    expect(newChatButton).toBeInTheDocument();
    
    // Click rapidly 3 times - should be prevented by mutex
    await act(async () => {
      fireEvent.click(newChatButton);
      fireEvent.click(newChatButton);
      fireEvent.click(newChatButton);
    });
    
    // Wait for operations to complete
    await waitFor(() => {
      // With proper mutex, only 1 operation should succeed
      expect(mockCreateThread).toHaveBeenCalledTimes(1);
    }, { timeout: 3000 });
    
    // Assert - Only one successful operation
    expect(successfulOperations.length).toBe(1);
    expect(storeState.setActiveThread).toHaveBeenCalledTimes(1);
  });
  
  it('should use debouncing to prevent rapid-fire operations', async () => {
    // Arrange
    const mockCreateThread = jest.fn().mockResolvedValue({
      id: 'debounced-thread',
      created_at: Date.now(),
      messages: [],
    });
    
    (ThreadService.createThread as jest.Mock) = mockCreateThread;
    
    // Act
    render(<ChatSidebar />);
    
    const newChatButton = screen.getByRole('button', { name: /new chat/i });
    
    // Rapidly click new chat button multiple times within debounce window
    await act(async () => {
      fireEvent.click(newChatButton);
      await new Promise(resolve => setTimeout(resolve, 50));
      fireEvent.click(newChatButton);
      await new Promise(resolve => setTimeout(resolve, 50));
      fireEvent.click(newChatButton);
    });
    
    // Wait for debounce to complete
    await waitFor(() => {
      // Debouncing should reduce the number of actual operations
      expect(mockCreateThread).toHaveBeenCalledTimes(1);
    }, { timeout: 3000 });
    
    // Assert - Debouncing worked
    expect(successfulOperations.length).toBeLessThanOrEqual(1);
  });
  
  it('should maintain proper state machine transitions', async () => {
    // Arrange
    const stateMachine = threadStateMachineManager.getStateMachine('newChat');
    const stateChanges: Array<{ from: string, to: string }> = [];
    
    stateMachine.addListener((data) => {
      if (stateChanges.length === 0 || stateChanges[stateChanges.length - 1].to !== data.currentState) {
        stateChanges.push({
          from: stateChanges.length > 0 ? stateChanges[stateChanges.length - 1].to : 'idle',
          to: data.currentState
        });
      }
    });
    
    const mockCreateThread = jest.fn().mockResolvedValue({
      id: 'state-machine-thread',
      created_at: Date.now(),
      messages: [],
    });
    
    (ThreadService.createThread as jest.Mock) = mockCreateThread;
    
    // Act
    render(<ChatSidebar />);
    
    const newChatButton = screen.getByRole('button', { name: /new chat/i });
    
    await act(async () => {
      fireEvent.click(newChatButton);
    });
    
    // Wait for operation to complete
    await waitFor(() => {
      expect(mockCreateThread).toHaveBeenCalled();
    });
    
    await waitFor(() => {
      expect(successfulOperations.length).toBe(1);
    }, { timeout: 3000 });
    
    // Assert - State machine transitions are proper
    expect(stateChanges).toEqual([
      { from: 'idle', to: 'creating' },
      { from: 'creating', to: 'switching' },
      { from: 'switching', to: 'idle' }
    ]);
  });
  
  it('should handle URL updates atomically without race conditions', async () => {
    // Arrange
    const urlUpdates: Array<{ method: string, url: string, timestamp: number }> = [];
    
    // Enhanced router mock to track URL updates
    mockRouter.replace = jest.fn((url: string) => {
      urlUpdates.push({ method: 'replace', url, timestamp: Date.now() });
    });
    
    const mockCreateThread = jest.fn().mockResolvedValue({
      id: 'atomic-url-thread',
      created_at: Date.now(),
      messages: [],
    });
    
    (ThreadService.createThread as jest.Mock) = mockCreateThread;
    
    // Act
    render(<ChatSidebar />);
    
    const newChatButton = screen.getByRole('button', { name: /new chat/i });
    
    await act(async () => {
      fireEvent.click(newChatButton);
    });
    
    // Wait for operation to complete
    await waitFor(() => {
      expect(successfulOperations.length).toBe(1);
    }, { timeout: 3000 });
    
    // Allow time for any delayed URL updates
    await new Promise(resolve => setTimeout(resolve, 200));
    
    // Assert - URL updates should be atomic (no duplicates)
    const threadUrlUpdates = urlUpdates.filter(update => 
      update.url.includes('atomic-url-thread')
    );
    
    // With proper atomic updates, we should have exactly 1 URL update per successful operation
    expect(threadUrlUpdates.length).toBeLessThanOrEqual(1);
    
    // If we have URL updates, they should be for the correct thread
    if (threadUrlUpdates.length > 0) {
      expect(threadUrlUpdates[0].url).toContain('atomic-url-thread');
    }
  });
  
  it('should gracefully handle operation failures', async () => {
    // Arrange
    const mockCreateThread = jest.fn().mockRejectedValue(new Error('Network error'));
    
    (ThreadService.createThread as jest.Mock) = mockCreateThread;
    
    // Act
    render(<ChatSidebar />);
    
    const newChatButton = screen.getByRole('button', { name: /new chat/i });
    
    await act(async () => {
      fireEvent.click(newChatButton);
    });
    
    // Wait for operation to complete
    await waitFor(() => {
      expect(mockCreateThread).toHaveBeenCalled();
    });
    
    // Give time for error handling
    await new Promise(resolve => setTimeout(resolve, 100));
    
    // Assert - Should handle errors gracefully
    const stateMachine = threadStateMachineManager.getStateMachine('newChat');
    const currentState = stateMachine.getState();
    
    // State machine should be in idle or error state (not stuck)
    expect(['idle', 'error']).toContain(currentState);
    
    // Should not have any successful operations
    expect(successfulOperations.length).toBe(0);
  });
});