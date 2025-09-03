/**
 * Simple verification test for new chat URL fix
 * 
 * This test verifies that the fix properly uses the thread switching hook
 * instead of direct store manipulation.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ChatSidebar } from '@/components/chat/ChatSidebar';
import '@testing-library/jest-dom';

// Track if switchToThread was called with correct options
let switchToThreadCalls: any[] = [];

// Mock dependencies
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn(), replace: jest.fn() }),
  useSearchParams: () => ({ get: () => null }),
  usePathname: () => '/chat',
}));

jest.mock('@/services/threadService', () => ({
  ThreadService: {
    createThread: jest.fn().mockResolvedValue({
      id: 'new-thread-123',
      created_at: Date.now(),
    }),
    getThreads: jest.fn().mockResolvedValue([]),
    getThreadMessages: jest.fn().mockResolvedValue({ messages: [] }),
  },
}));

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

jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: (selector?: any) => {
    const state = {
      isProcessing: false,
      activeThreadId: null,
      threads: new Map(),
      messages: [],
      setActiveThread: jest.fn(),
      clearMessages: jest.fn(),
      resetLayers: jest.fn(),
    };
    return selector ? selector(state) : state;
  },
}));

// This is the KEY mock - track calls to switchToThread
jest.mock('@/hooks/useThreadSwitching', () => ({
  useThreadSwitching: () => ({
    switchToThread: jest.fn((threadId, options) => {
      switchToThreadCalls.push({ threadId, options });
      return Promise.resolve(true);
    }),
    state: {
      isLoading: false,
      loadingThreadId: null,
      error: null,
    },
    cancelLoading: jest.fn(),
    retryLastFailed: jest.fn(),
  }),
}));

// Mock other hooks
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
    loadThreads: jest.fn(),
  }),
  useThreadFiltering: () => ({
    sortedThreads: [],
    paginatedThreads: [],
    totalPages: 1,
  }),
}));

describe('New Chat Fix Verification', () => {
  beforeEach(() => {
    switchToThreadCalls = [];
  });
  
  it('should use switchToThread hook with updateUrl option when creating new chat', async () => {
    // Render the ChatSidebar
    render(<ChatSidebar />);
    
    // Find and click the new chat button
    const newChatButton = await screen.findByRole('button', { name: /new chat/i });
    fireEvent.click(newChatButton);
    
    // Wait for async operations
    await waitFor(() => {
      expect(switchToThreadCalls.length).toBeGreaterThan(0);
    }, { timeout: 3000 });
    
    // Verify the fix: switchToThread should be called with updateUrl: true
    const call = switchToThreadCalls[0];
    expect(call).toBeDefined();
    expect(call.threadId).toBe('new-thread-123');
    expect(call.options).toMatchObject({
      clearMessages: true,
      updateUrl: true, // This is the critical fix
    });
    
    console.log('✅ Fix verified: New chat uses switchToThread with updateUrl: true');
  });
});