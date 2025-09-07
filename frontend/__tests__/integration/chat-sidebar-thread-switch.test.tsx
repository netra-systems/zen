/**
 * ChatSidebar Thread Switching Integration Test
 * 
 * Tests the actual ChatSidebar component to identify glitches
 */

import React from 'react';
import { render, fireEvent, waitFor, screen, within } from '@testing-library/react';
import { act } from 'react';
import { ChatSidebar } from '@/components/chat/ChatSidebar';
import { useUnifiedChatStore, resetMockState } from '@/store/unified-chat';
import * as threadService from '@/services/threadService';
import * as threadLoadingService from '@/services/threadLoadingService';

// Mock dependencies
jest.mock('@/store/unified-chat', () => require('../../__mocks__/store/unified-chat'));
jest.mock('lucide-react', () => ({
  MessageSquare: () => <div data-testid="messagesquare-icon" data-icon="MessageSquare" />,
  Clock: () => <div data-testid="clock-icon" data-icon="Clock" />,
  ChevronRight: () => <div data-testid="chevronright-icon" data-icon="ChevronRight" />,
  Database: () => <div data-testid="database-icon" data-icon="Database" />,
  Sparkles: () => <div data-testid="sparkles-icon" data-icon="Sparkles" />,
  Users: () => <div data-testid="users-icon" data-icon="Users" />,
  Plus: () => <div data-testid="plus-icon" data-icon="Plus" />,
  Search: () => <div data-testid="search-icon" data-icon="Search" />
}));
jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: () => ({
    sendMessage: jest.fn(),
    isConnected: true
  })
}));

jest.mock('@/store/authStore', () => ({
  useAuthStore: () => ({
    isDeveloperOrHigher: () => false,
    isAuthenticated: true
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

jest.mock('@/services/threadLoadingService');
jest.mock('@/services/threadService');
jest.mock('@/lib/retry-manager', () => ({
  executeWithRetry: jest.fn((fn) => fn())
}));

jest.mock('@/lib/operation-cleanup', () => ({
  globalCleanupManager: {
    registerAbortController: jest.fn(),
    cleanupThread: jest.fn()
  }
}));

jest.mock('@/services/urlSyncService', () => ({
  useURLSync: () => ({ updateUrl: jest.fn() }),
  useBrowserHistorySync: () => ({})
}));

jest.mock('@/hooks/useThreadSwitching', () => ({
  useThreadSwitching: () => ({
    state: {
      isLoading: false,
      loadingThreadId: null,
      error: null,
      lastLoadedThreadId: null,
      operationId: null,
      retryCount: 0
    },
    switchToThread: jest.fn().mockResolvedValue(true),
    cancelLoading: jest.fn(),
    retryLastFailed: jest.fn().mockResolvedValue(true)
  })
}));

const mockThreads = [
  {
    id: 'thread-1',
    title: 'First Thread',
    created_at: '2024-01-01T00:00:00.000Z',
    updated_at: '2024-01-01T00:00:00.000Z',
    message_count: 5
  },
  {
    id: 'thread-2',
    title: 'Second Thread',
    created_at: '2024-01-02T00:00:00.000Z', 
    updated_at: '2024-01-02T00:00:00.000Z',
    message_count: 3
  },
  {
    id: 'thread-3',
    title: 'Third Thread',
    created_at: '2024-01-03T00:00:00.000Z',
    updated_at: '2024-01-03T00:00:00.000Z', 
    message_count: 7
  }
];

describe('ChatSidebar Thread Switching Glitch Detection', () => {
  let sendMessageSpy: jest.Mock;
  
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Reset store
    resetMockState();
    useUnifiedChatStore.getState().activeThreadId = 'thread-1';
    useUnifiedChatStore.getState().isProcessing = false;
    
    // Setup WebSocket mock
    sendMessageSpy = jest.fn();
    jest.spyOn(require('@/hooks/useWebSocket'), 'useWebSocket').mockReturnValue({
      sendMessage: sendMessageSpy,
      isConnected: true
    });
    
    // Mock thread service
    (threadService.ThreadService.listThreads as jest.Mock) = jest.fn().mockResolvedValue(mockThreads);
    (threadService.ThreadService.getThreadMessages as jest.Mock) = jest.fn().mockResolvedValue({
      thread_id: 'thread-2',
      messages: []
    });
    
    // Mock thread loading service
    (threadLoadingService.threadLoadingService.loadThread as jest.Mock) = jest.fn()
      .mockResolvedValue({
        success: true,
        messages: [],
        threadId: 'thread-2'
      });
  });
  
  describe('Glitch Scenario 1: Double WebSocket Messages', () => {
    it('should not send duplicate WebSocket messages', async () => {
      const { container } = render(<ChatSidebar />);
      
      await waitFor(() => {
        const threads = container.querySelectorAll('[data-testid^="thread-item-"]');
        expect(threads.length).toBeGreaterThan(0);
      });
      
      const secondThread = container.querySelector('[data-testid="thread-item-thread-2"]');
      
      await act(async () => {
        fireEvent.click(secondThread!);
      });
      
      // Wait a bit for all async operations
      await waitFor(() => {
        expect(sendMessageSpy).toHaveBeenCalledTimes(1);
      });
      
      // Verify only one WebSocket message was sent
      expect(sendMessageSpy).toHaveBeenCalledWith({
        type: 'switch_thread',
        payload: { thread_id: 'thread-2' }
      });
    });
  });
  
  describe('Glitch Scenario 2: Loading State Stuck', () => {
    it('should properly clear loading state after switch', async () => {
      const { container } = render(<ChatSidebar />);
      
      // Set up a delayed response
      (threadLoadingService.threadLoadingService.loadThread as jest.Mock)
        .mockImplementation(() => new Promise(resolve => {
          setTimeout(() => resolve({
            success: true,
            messages: [],
            threadId: 'thread-2'
          }), 100);
        }));
      
      await waitFor(() => {
        const threads = container.querySelectorAll('[data-testid^="thread-item-"]');
        expect(threads.length).toBeGreaterThan(0);
      });
      
      const secondThread = container.querySelector('[data-testid="thread-item-thread-2"]');
      
      // Click to switch
      act(() => {
        fireEvent.click(secondThread!);
      });
      
      // Check loading state is set
      expect(useUnifiedChatStore.getState().threadLoading).toBe(true);
      
      // Wait for completion
      await waitFor(() => {
        expect(useUnifiedChatStore.getState().threadLoading).toBe(false);
      }, { timeout: 3000 });
      
      // Verify final state
      const finalState = useUnifiedChatStore.getState();
      expect(finalState.threadLoading).toBe(false);
      expect(finalState.activeThreadId).toBe('thread-2');
    });
    
    it('should handle loading state when rapidly clicking threads', async () => {
      const { container } = render(<ChatSidebar />);
      
      await waitFor(() => {
        const threads = container.querySelectorAll('[data-testid^="thread-item-"]');
        expect(threads.length).toBeGreaterThan(0);
      });
      
      const thread2 = container.querySelector('[data-testid="thread-item-thread-2"]');
      const thread3 = container.querySelector('[data-testid="thread-item-thread-3"]');
      
      // Rapidly click different threads
      act(() => {
        fireEvent.click(thread2!);
        fireEvent.click(thread3!);
      });
      
      await waitFor(() => {
        const state = useUnifiedChatStore.getState();
        expect(state.threadLoading).toBe(false);
      }, { timeout: 3000 });
      
      // Should end up on the last clicked thread
      expect(useUnifiedChatStore.getState().activeThreadId).toBe('thread-3');
    });
  });
  
  describe('Glitch Scenario 3: Messages Not Clearing', () => {
    it('should clear previous messages when switching threads', async () => {
      // Set initial messages
      useUnifiedChatStore.setState({
        messages: [
          { id: 'old-1', content: 'Old message 1', role: 'user', timestamp: Date.now() },
          { id: 'old-2', content: 'Old message 2', role: 'assistant', timestamp: Date.now() }
        ]
      });
      
      const { container } = render(<ChatSidebar />);
      
      await waitFor(() => {
        const threads = container.querySelectorAll('[data-testid^="thread-item-"]');
        expect(threads.length).toBeGreaterThan(0);
      });
      
      // Mock loading with new messages
      (threadLoadingService.threadLoadingService.loadThread as jest.Mock)
        .mockResolvedValueOnce({
          success: true,
          messages: [
            { id: 'new-1', content: 'New message', role: 'user', timestamp: Date.now() }
          ],
          threadId: 'thread-2'
        });
      
      const secondThread = container.querySelector('[data-testid="thread-item-thread-2"]');
      
      await act(async () => {
        fireEvent.click(secondThread!);
      });
      
      await waitFor(() => {
        const state = useUnifiedChatStore.getState();
        expect(state.messages).toHaveLength(1);
        expect(state.messages[0].id).toBe('new-1');
      });
    });
  });
  
  describe('Glitch Scenario 4: Active Thread Highlighting', () => {
    it('should correctly highlight the active thread', async () => {
      const { container } = render(<ChatSidebar />);
      
      await waitFor(() => {
        const threads = container.querySelectorAll('[data-testid^="thread-item-"]');
        expect(threads.length).toBeGreaterThan(0);
      });
      
      // Initially thread-1 should be active
      const thread1 = container.querySelector('[data-testid="thread-item-thread-1"]');
      expect(thread1?.className).toContain('bg-emerald-50'); // Updated to actual active class
      
      const thread2 = container.querySelector('[data-testid="thread-item-thread-2"]');
      
      await act(async () => {
        fireEvent.click(thread2!);
      });
      
      await waitFor(() => {
        expect(useUnifiedChatStore.getState().activeThreadId).toBe('thread-2');
      });
      
      // Thread 2 should now be active
      expect(thread2?.className).toContain('bg-emerald-50');
      expect(thread1?.className).not.toContain('bg-emerald-50');
    });
  });
  
  describe('Glitch Scenario 5: Processing State Blocking', () => {
    it('should not allow switching when processing', async () => {
      useUnifiedChatStore.setState({ isProcessing: true });
      
      const { container } = render(<ChatSidebar />);
      
      await waitFor(() => {
        const threads = container.querySelectorAll('[data-testid^="thread-item-"]');
        expect(threads.length).toBeGreaterThan(0);
      });
      
      const thread2 = container.querySelector('[data-testid="thread-item-thread-2"]');
      
      await act(async () => {
        fireEvent.click(thread2!);
      });
      
      // Should not switch threads
      expect(sendMessageSpy).not.toHaveBeenCalled();
      expect(useUnifiedChatStore.getState().activeThreadId).toBe('thread-1');
    });
    
    it('should allow switching after processing completes', async () => {
      useUnifiedChatStore.setState({ isProcessing: true });
      
      const { container } = render(<ChatSidebar />);
      
      await waitFor(() => {
        const threads = container.querySelectorAll('[data-testid^="thread-item-"]');
        expect(threads.length).toBeGreaterThan(0);
      });
      
      // Stop processing
      act(() => {
        useUnifiedChatStore.setState({ isProcessing: false });
      });
      
      const thread2 = container.querySelector('[data-testid="thread-item-thread-2"]');
      
      await act(async () => {
        fireEvent.click(thread2!);
      });
      
      // Should now allow switching
      expect(sendMessageSpy).toHaveBeenCalled();
      await waitFor(() => {
        expect(useUnifiedChatStore.getState().activeThreadId).toBe('thread-2');
      });
    });
  });
});