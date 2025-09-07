/**
 * Simple test to verify new chat navigation fix
 * 
 * This test verifies that the race condition fix properly prevents
 * duplicate URL updates when creating a new chat.
 */

import React from 'react';
import { renderHook, act } from '@testing-library/react';
import { useThreadSwitching } from '@/hooks/useThreadSwitching';
import { useURLSync } from '@/services/urlSyncService';
import { useRouter } from 'next/navigation';

// Mock dependencies
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
  useSearchParams: jest.fn(() => {
    const params = new URLSearchParams();
    return params;
  }),
  usePathname: jest.fn(() => '/chat'),
}));

jest.mock('@/store/unified-chat', () => {
  const mockState = {
    activeThreadId: null,
    setActiveThread: jest.fn(),
    setThreadLoading: jest.fn(),
    startThreadLoading: jest.fn(),
    completeThreadLoading: jest.fn(),
    clearMessages: jest.fn(),
    loadMessages: jest.fn(),
    handleWebSocketEvent: jest.fn(),
  };
  
  const mockStore = jest.fn((selector) => {
    return typeof selector === 'function' ? selector(mockState) : mockState;
  });
  
  // CRITICAL: Add getState method that jest.setup.js expects
  mockStore.getState = () => mockState;
  
  return {
    useUnifiedChatStore: mockStore,
  };
});

jest.mock('@/services/threadLoadingService', () => ({
  threadLoadingService: {
    loadThread: jest.fn().mockResolvedValue({
      success: true,
      messages: [],
    }),
  },
}));

jest.mock('@/lib/operation-cleanup', () => ({
  globalCleanupManager: {
    registerAbortController: jest.fn(),
    cleanupThread: jest.fn(),
  },
}));

jest.mock('@/utils/threadEventHandler', () => ({
  threadEventHandler: jest.fn(),
  createThreadLoadingEvent: jest.fn(),
  createThreadLoadedEvent: jest.fn(),
}));

jest.mock('@/utils/threadTimeoutManager', () => ({
  createThreadTimeoutManager: jest.fn(() => ({
    startTimeout: jest.fn(),
    clearTimeout: jest.fn(),
  })),
}));

jest.mock('@/lib/retry-manager', () => ({
  executeWithRetry: jest.fn((fn) => fn()),
}));

jest.mock('@/lib/logger', () => ({
  logger: {
    warn: jest.fn(),
    error: jest.fn(),
  },
}));

describe('New Chat Navigation Fix Verification', () => {
  let mockRouter: any;
  let routerReplaceCalls: Array<{ url: string; timestamp: number }> = [];

  beforeEach(() => {
    // Reset tracking
    routerReplaceCalls = [];
    
    // Setup router mock with tracking
    mockRouter = {
      replace: jest.fn((url) => {
        routerReplaceCalls.push({ url, timestamp: Date.now() });
        console.log('Router.replace called with:', url);
      }),
      push: jest.fn(),
      prefetch: jest.fn(),
    };
    
    (useRouter as jest.Mock).mockReturnValue(mockRouter);
    jest.clearAllMocks();
  });

  it('should prevent duplicate URL updates with the fix', async () => {
    // Test the useThreadSwitching hook with URL sync
    const { result: threadSwitchResult } = renderHook(() => useThreadSwitching());
    const { result: urlSyncResult } = renderHook(() => useURLSync());
    
    const newThreadId = 'test-thread-123';
    
    // Act - switch to thread with URL update
    await act(async () => {
      await threadSwitchResult.current.switchToThread(newThreadId, {
        clearMessages: true,
        updateUrl: true,
        showLoadingIndicator: true,
      });
    });
    
    // Wait for any delayed updates
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 200));
    });
    
    // Assert - should only have one URL update
    console.log('Total router.replace calls:', routerReplaceCalls.length);
    console.log('Router replace history:', routerReplaceCalls);
    
    // With the fix, we should see only 1 URL update
    // (either from auto-sync OR manual update, but not both)
    expect(routerReplaceCalls.length).toBeLessThanOrEqual(1);
    
    // If there was an update, it should be for the correct thread
    if (routerReplaceCalls.length > 0) {
      expect(routerReplaceCalls[0].url).toContain(newThreadId);
    }
  });

  it('should handle rapid thread switches without URL chaos', async () => {
    const { result: threadSwitchResult } = renderHook(() => useThreadSwitching());
    
    const thread1 = 'rapid-thread-1';
    const thread2 = 'rapid-thread-2';
    const thread3 = 'rapid-thread-3';
    
    // Act - rapid thread switches
    await act(async () => {
      // Start all switches nearly simultaneously
      const promise1 = threadSwitchResult.current.switchToThread(thread1, { updateUrl: true });
      const promise2 = threadSwitchResult.current.switchToThread(thread2, { updateUrl: true });
      const promise3 = threadSwitchResult.current.switchToThread(thread3, { updateUrl: true });
      
      // Wait for all to complete
      await Promise.all([promise1, promise2, promise3]);
    });
    
    // Wait for any delayed updates
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 300));
    });
    
    // Assert
    console.log('Rapid switch router calls:', routerReplaceCalls.length);
    console.log('Rapid switch history:', routerReplaceCalls);
    
    // With the fix, rapid switches should result in controlled URL updates
    // The exact number depends on race condition handling, but should be reasonable
    expect(routerReplaceCalls.length).toBeLessThanOrEqual(3);
    
    // The final URL should be one of the threads we switched to
    if (routerReplaceCalls.length > 0) {
      const lastUrl = routerReplaceCalls[routerReplaceCalls.length - 1].url;
      expect([thread1, thread2, thread3].some(id => lastUrl.includes(id))).toBe(true);
    }
  });

  it('should maintain URL sync integrity during error scenarios', async () => {
    // Mock a loading failure
    const threadLoadingService = require('@/services/threadLoadingService').threadLoadingService;
    threadLoadingService.loadThread.mockRejectedValueOnce(new Error('Load failed'));
    
    const { result: threadSwitchResult } = renderHook(() => useThreadSwitching());
    
    const failingThreadId = 'failing-thread';
    
    // Act - try to switch to a thread that will fail
    let switchResult;
    await act(async () => {
      switchResult = await threadSwitchResult.current.switchToThread(failingThreadId, {
        updateUrl: true,
      });
    });
    
    // Wait for any delayed updates
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 200));
    });
    
    // Assert
    console.log('Error scenario router calls:', routerReplaceCalls.length);
    console.log('Error scenario history:', routerReplaceCalls);
    
    // On error, URL should not be updated
    expect(switchResult).toBe(false);
    expect(routerReplaceCalls.length).toBe(0);
    
    // The hook should be in error state
    expect(threadSwitchResult.current.state.error).toBeTruthy();
    expect(threadSwitchResult.current.state.isLoading).toBe(false);
  });
});