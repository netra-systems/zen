/**
 * Debug test to understand the call flow in useThreadSwitching
 */

import { renderHook, act } from '@testing-library/react';
import { useThreadSwitching } from '@/hooks/useThreadSwitching';

// Mock the store first
jest.mock('@/store/unified-chat', () => require('../../__mocks__/store/unified-chat'));
jest.mock('@/lib/thread-operation-manager', () => require('../../__mocks__/lib/thread-operation-manager'));

// Mock the services 
jest.mock('@/services/threadLoadingService', () => ({
  threadLoadingService: { loadThread: jest.fn() }
}));

jest.mock('@/lib/retry-manager', () => ({
  executeWithRetry: jest.fn()
}));

// Mock other dependencies
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

describe('useThreadSwitching Debug', () => {
  let mockLoadThread: jest.Mock;
  let mockExecuteWithRetry: jest.Mock;

  beforeEach(() => {
    // Get the mocked functions
    const { threadLoadingService } = require('@/services/threadLoadingService');
    const { executeWithRetry } = require('@/lib/retry-manager');
    
    mockLoadThread = threadLoadingService.loadThread as jest.Mock;
    mockExecuteWithRetry = executeWithRetry as jest.Mock;
    
    // Reset all mocks
    mockLoadThread.mockClear();
    mockExecuteWithRetry.mockClear();
    
    // Set up return values
    mockLoadThread.mockResolvedValue({
      success: true,
      threadId: 'test-123',
      messages: [{ id: 'msg-1', content: 'Test message' }]
    });
    
    // Make executeWithRetry actually call the function passed to it
    mockExecuteWithRetry.mockImplementation(async (fn) => {
      console.log('DEBUG: executeWithRetry called, about to call fn');
      const result = await fn();
      console.log('DEBUG: fn returned:', result);
      return result;
    });
  });

  it('should call the complete chain', async () => {
    const { result } = renderHook(() => useThreadSwitching());
    
    console.log('DEBUG: Starting thread switch');
    
    const success = await act(async () => {
      return await result.current.switchToThread('test-123');
    });
    
    console.log('DEBUG: Thread switch complete, success:', success);
    console.log('DEBUG: mockExecuteWithRetry called:', mockExecuteWithRetry.mock.calls.length, 'times');
    console.log('DEBUG: mockLoadThread called:', mockLoadThread.mock.calls.length, 'times');
    
    if (mockExecuteWithRetry.mock.calls.length > 0) {
      console.log('DEBUG: executeWithRetry args:', mockExecuteWithRetry.mock.calls[0]);
    }
    
    expect(mockExecuteWithRetry).toHaveBeenCalled();
    expect(mockLoadThread).toHaveBeenCalledWith('test-123');
    expect(success).toBe(true);
  });
});