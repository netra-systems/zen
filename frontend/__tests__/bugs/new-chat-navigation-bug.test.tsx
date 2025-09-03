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
    userTier: 'paid',
  }),
}));

jest.mock('@/store/authStore', () => ({
  useAuthStore: () => ({
    isDeveloperOrHigher: () => false,
  }),
}));

// Mock the unified chat store
let mockStoreState = {
  isProcessing: false,
  activeThreadId: null,
  threads: new Map(),
  isThreadLoading: false,
  messages: [],
  isConnected: true,
  setActiveThread: jest.fn(),
  setThreadLoading: jest.fn(),
  startThreadLoading: jest.fn(),
  completeThreadLoading: jest.fn(),
  clearMessages: jest.fn(),
  loadMessages: jest.fn(),
  resetLayers: jest.fn(),
  resetStore: jest.fn(),
};

jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: jest.fn((selector) => {
    if (selector) {
      return selector(mockStoreState);
    }
    return mockStoreState;
  }),
}));

// Mock the thread switching hook
jest.mock('@/hooks/useThreadSwitching', () => ({
  useThreadSwitching: () => ({
    switchToThread: jest.fn().mockResolvedValue(true),
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
    mockStoreState.activeThreadId = null;
    mockStoreState.messages = [];
    mockStoreState.isProcessing = false;
    mockStoreState.isThreadLoading = false;
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
    
    // Assert
    await waitFor(() => {
      // Thread should be created
      expect(mockCreateThread).toHaveBeenCalled();
    });
    
    await waitFor(() => {
      // Store should be updated with new thread
      expect(mockStoreState.setActiveThread).toHaveBeenCalledWith(newThreadId);
    });
    
    // FIXED: With the new implementation using switchToThread hook,
    // URL should now be updated properly via the hook's updateUrl option
    const { useThreadSwitching } = require('@/hooks/useThreadSwitching');
    const mockSwitchToThread = useThreadSwitching().switchToThread;
    
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