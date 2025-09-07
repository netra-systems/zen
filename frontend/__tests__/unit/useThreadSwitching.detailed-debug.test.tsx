/**
 * Detailed debug test to understand state synchronization issues
 */

import { renderHook, act } from '@testing-library/react';
import { useThreadSwitching } from '@/hooks/useThreadSwitching';

jest.mock('@/store/unified-chat', () => require('../../__mocks__/store/unified-chat'));
jest.mock('@/lib/thread-operation-manager', () => require('../../__mocks__/lib/thread-operation-manager'));

// Mock services
jest.mock('@/services/threadLoadingService', () => ({
  threadLoadingService: { loadThread: jest.fn() }
}));

jest.mock('@/lib/retry-manager', () => ({
  executeWithRetry: jest.fn()
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

jest.mock('@/utils/threadEventHandler', () => ({
  createThreadLoadingEvent: jest.fn(() => ({ type: 'thread_loading' })),
  createThreadLoadedEvent: jest.fn(() => ({ type: 'thread_loaded' }))
}));

jest.mock('@/utils/threadTimeoutManager', () => ({
  createThreadTimeoutManager: () => ({
    startTimeout: jest.fn(),
    clearTimeout: jest.fn()
  })
}));

jest.mock('@/lib/logger', () => ({
  logger: { debug: jest.fn(), info: jest.fn(), warn: jest.fn(), error: jest.fn() }
}));

describe('useThreadSwitching Detailed Debug', () => {
  it('should synchronize hook state and store state', async () => {
    const { result } = renderHook(() => useThreadSwitching());
    const { threadLoadingService } = require('@/services/threadLoadingService');
    const { executeWithRetry } = require('@/lib/retry-manager');
    const { ThreadOperationManager } = require('@/lib/thread-operation-manager');
    const { useUnifiedChatStore, resetMockState } = require('@/store/unified-chat');

    // Reset everything
    resetMockState();
    ThreadOperationManager.reset();
    threadLoadingService.loadThread.mockClear();
    executeWithRetry.mockClear();

    // Set up mocks
    threadLoadingService.loadThread.mockResolvedValue({
      success: true,
      threadId: 'thread-1',
      messages: [{ id: 'msg-1', content: 'Test message' }]
    });

    executeWithRetry.mockImplementation(async (fn) => {
      console.log('executeWithRetry: calling function');
      const result = await fn();
      console.log('executeWithRetry: got result:', result);
      return result;
    });

    console.log('Initial hook state:', result.current.state);
    console.log('Initial store state:', useUnifiedChatStore.getState());

    const success = await act(async () => {
      return await result.current.switchToThread('thread-1');
    });

    console.log('Operation success:', success);
    console.log('Final hook state:', result.current.state);
    console.log('Final store state:', useUnifiedChatStore.getState());

    // The key assertion that's failing
    expect(result.current.state.lastLoadedThreadId).toBe('thread-1');
    expect(result.current.state.isLoading).toBe(false);
    expect(success).toBe(true);

    // Store state should also be updated
    const storeState = useUnifiedChatStore.getState();
    expect(storeState.activeThreadId).toBe('thread-1');
    expect(storeState.messages).toHaveLength(1);
  });
});