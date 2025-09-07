/**
 * Thread Switching End-to-End Integration Test
 * 
 * Tests the complete flow of clicking a thread in the sidebar 
 * and verifying all state updates and WebSocket events
 */

import React from 'react';
import { render, fireEvent, waitFor, screen } from '@testing-library/react';
import { act } from 'react';
import { ChatSidebar } from '@/components/chat/ChatSidebar';
import { useThreadSwitching } from '@/hooks/useThreadSwitching';
import * as threadService from '@/services/threadService';

// Mock the unified chat store
jest.mock('@/store/unified-chat', () => require('../../__mocks__/store/unified-chat'));

// Import the mocked store
import { useUnifiedChatStore, resetMockState } from '@/store/unified-chat';

// Mock modules
jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: () => ({
    sendMessage: jest.fn(),
    isConnected: true
  })
}));

jest.mock('@/store/authStore', () => ({
  useAuthStore: () => ({
    isDeveloperOrHigher: () => false
  })
}));

jest.mock('@/hooks/useAuthState', () => ({
  useAuthState: () => ({
    isAuthenticated: true,
    userTier: 'Free'
  })
}));

jest.mock('@/components/auth/AuthGate', () => ({
  AuthGate: ({ children }: any) => <>{children}</>
}));

// Mock threadLoadingService
jest.mock('@/services/threadLoadingService', () => ({
  threadLoadingService: {
    loadThread: jest.fn().mockResolvedValue({
      success: true,
      messages: [],
      threadId: 'thread-2'
    })
  }
}));

// Mock thread data
const mockThreads = [
  {
    id: 'thread-1',
    title: 'First Thread',
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
    message_count: 5
  },
  {
    id: 'thread-2', 
    title: 'Second Thread',
    created_at: '2025-01-02T00:00:00Z',
    updated_at: '2025-01-02T00:00:00Z',
    message_count: 3
  }
];

const mockMessages = [
  {
    id: 'msg-1',
    role: 'user',
    content: 'Hello',
    timestamp: Date.now(),
    threadId: 'thread-2'
  },
  {
    id: 'msg-2',
    role: 'assistant',
    content: 'Hi there!',
    timestamp: Date.now(),
    threadId: 'thread-2'
  }
];

describe('Thread Switching E2E Integration', () => {
  let sendMessageSpy: jest.Mock;
  
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Reset the mock store to initial state
    if (typeof resetMockState === 'function') {
      resetMockState();
    }
    
    // Set initial state
    useUnifiedChatStore.setState({
      activeThreadId: 'thread-1',
      messages: [],
      isProcessing: false,
      isThreadLoading: false
    });
    
    // Setup spies
    sendMessageSpy = jest.fn();
    jest.spyOn(require('@/hooks/useWebSocket'), 'useWebSocket').mockReturnValue({
      sendMessage: sendMessageSpy,
      isConnected: true
    });
    
    // Mock thread service - use the actual methods that exist
    jest.spyOn(threadService.ThreadService, 'listThreads').mockResolvedValue(mockThreads);
    
    jest.spyOn(threadService.ThreadService, 'getThread').mockResolvedValue({
      id: 'thread-2',
      title: 'Second Thread',
      messages: mockMessages.map(msg => ({
        id: msg.id,
        role: msg.role,
        content: msg.content,
        created_at: new Date(msg.timestamp).toISOString(),
        metadata: {}
      })),
      created_at: '2025-01-02T00:00:00Z',
      updated_at: '2025-01-02T00:00:00Z'
    });
    
    // Reset the loadThread mock for each test
    const { threadLoadingService } = require('@/services/threadLoadingService');
    threadLoadingService.loadThread.mockClear();
    threadLoadingService.loadThread.mockResolvedValue({
      success: true,
      messages: mockMessages,
      threadId: 'thread-2'
    });
  });
  
  afterEach(() => {
    jest.clearAllMocks();
  });
  
  it('should use useThreadSwitching hook when clicking a thread', async () => {
    const { container } = render(<ChatSidebar />);
    
    // Wait for threads to load
    await waitFor(() => {
      const threadItems = container.querySelectorAll('[data-testid^="thread-item-"]');
      expect(threadItems.length).toBeGreaterThan(0);
    });
    
    // Find and click the second thread
    const secondThread = container.querySelector('[data-testid="thread-item-thread-2"]');
    expect(secondThread).toBeTruthy();
    
    await act(async () => {
      fireEvent.click(secondThread!);
    });
    
    // Verify WebSocket message was sent
    await waitFor(() => {
      expect(sendMessageSpy).toHaveBeenCalledWith({
        type: 'switch_thread',
        payload: { thread_id: 'thread-2' }
      });
    });
    
    // Verify thread loading service was called (via the hook)
    const { threadLoadingService } = require('@/services/threadLoadingService');
    await waitFor(() => {
      expect(threadLoadingService.loadThread).toHaveBeenCalledWith('thread-2', expect.objectContaining({
        clearMessages: true,
        showLoadingIndicator: true,
        updateUrl: true
      }));
    });
    
    // Verify store state was updated
    await waitFor(() => {
      const state = useUnifiedChatStore.getState();
      expect(state.activeThreadId).toBe('thread-2');
      expect(state.messages).toHaveLength(2);
    });
  });
  
  it('should not switch if clicking the active thread', async () => {
    // Set thread-1 as active
    useUnifiedChatStore.setState({ activeThreadId: 'thread-1' });
    
    const { container } = render(<ChatSidebar />);
    
    await waitFor(() => {
      const threadItems = container.querySelectorAll('[data-testid^="thread-item-"]');
      expect(threadItems.length).toBeGreaterThan(0);
    });
    
    // Click the already active thread
    const firstThread = container.querySelector('[data-testid="thread-item-thread-1"]');
    
    await act(async () => {
      fireEvent.click(firstThread!);
    });
    
    // Verify no WebSocket message was sent
    expect(sendMessageSpy).not.toHaveBeenCalled();
    
    // Verify thread loading was not called
    const { threadLoadingService } = require('@/services/threadLoadingService');
    expect(threadLoadingService.loadThread).not.toHaveBeenCalled();
  });
  
  it('should not switch while processing', async () => {
    // Set processing state
    useUnifiedChatStore.setState({ isProcessing: true });
    
    const { container } = render(<ChatSidebar />);
    
    await waitFor(() => {
      const threadItems = container.querySelectorAll('[data-testid^="thread-item-"]');
      expect(threadItems.length).toBeGreaterThan(0);
    });
    
    const secondThread = container.querySelector('[data-testid="thread-item-thread-2"]');
    
    await act(async () => {
      fireEvent.click(secondThread!);
    });
    
    // Verify no actions were taken
    expect(sendMessageSpy).not.toHaveBeenCalled();
    const { threadLoadingService } = require('@/services/threadLoadingService');
    expect(threadLoadingService.loadThread).not.toHaveBeenCalled();
  });
  
  it('should handle loading errors gracefully', async () => {
    // Mock loading failure
    const { threadLoadingService } = require('@/services/threadLoadingService');
    threadLoadingService.loadThread.mockRejectedValueOnce(new Error('Network error'));
    
    const { container } = render(<ChatSidebar />);
    
    await waitFor(() => {
      const threadItems = container.querySelectorAll('[data-testid^="thread-item-"]');
      expect(threadItems.length).toBeGreaterThan(0);
    });
    
    const secondThread = container.querySelector('[data-testid="thread-item-thread-2"]');
    
    await act(async () => {
      fireEvent.click(secondThread!);
    });
    
    // Verify WebSocket message was still sent
    await waitFor(() => {
      expect(sendMessageSpy).toHaveBeenCalledWith({
        type: 'switch_thread',
        payload: { thread_id: 'thread-2' }
      });
    });
    
    // Verify loading was attempted
    expect(threadLoadingService.loadThread).toHaveBeenCalled();
    
    // Verify thread did not switch on error
    const state = useUnifiedChatStore.getState();
    expect(state.activeThreadId).toBe('thread-1'); // Should remain on original thread
  });
});