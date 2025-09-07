/**
 * Integration test for new chat URL update fix
 * 
 * Verifies that creating a new chat properly updates the URL
 * using the thread switching hook with updateUrl option.
 */

import { renderHook, act } from '@testing-library/react';
import { useThreadSwitching } from '@/hooks/useThreadSwitching';
import { ThreadService } from '@/services/threadService';

// Mock the thread service
jest.mock('@/services/threadService');

// Mock Next.js router
const mockRouter = {
  push: jest.fn(),
  replace: jest.fn(),
  prefetch: jest.fn(),
};

jest.mock('next/navigation', () => ({
  useRouter: () => mockRouter,
  useSearchParams: () => ({
    get: jest.fn().mockReturnValue(null),
  }),
  usePathname: () => '/chat',
  __mockRouter: mockRouter, // Expose mock router for jest.setup.js
}));

// Use the global mock for unified chat store to ensure API compatibility
// The global mock has proper getState support which is needed by ThreadOperationManager

// Mock URL sync service to avoid hook calls outside components
jest.mock('@/services/urlSyncService', () => ({
  useURLSync: () => ({ updateUrl: jest.fn() }),
  useBrowserHistorySync: () => ({})
}));

// Mock thread loading service - will be configured per test
jest.mock('@/services/threadLoadingService', () => ({
  threadLoadingService: {
    loadThread: jest.fn(), // Will be configured in each test
  },
}));

describe('New Chat URL Update Integration', () => {
  beforeEach(() => {
    // Don't use jest.clearAllMocks() as it clears mock implementations
    // Reset only specific mocks that need resetting
    mockRouter.push.mockClear();
    mockRouter.replace.mockClear();
    mockRouter.prefetch.mockClear();
    
    // Reset mock store state to ensure clean test isolation
    const { resetMockState } = require('@/store/unified-chat');
    if (resetMockState) {
      resetMockState();
    }
    
    // Reset thread loading service
    const { threadLoadingService } = require('@/services/threadLoadingService');
    threadLoadingService.loadThread.mockClear();
  });
  
  it('should update URL when creating and switching to new thread', async () => {
    // Arrange
    const newThreadId = 'new-thread-123';
    const mockCreateThread = jest.fn().mockResolvedValue({
      id: newThreadId,
      created_at: Date.now(),
      messages: [],
    });
    
    // Configure the thread loading service to return the correct threadId
    const { threadLoadingService } = require('@/services/threadLoadingService');
    threadLoadingService.loadThread.mockResolvedValue({
      success: true,
      messages: [],
      threadId: newThreadId, // Return the expected threadId
    });
    
    (ThreadService.createThread as jest.Mock) = mockCreateThread;
    
    // Get the thread switching hook
    const { result } = renderHook(() => useThreadSwitching());
    
    // Act - Simulate new chat creation flow
    await act(async () => {
      // Step 1: Create new thread (what ChatSidebar does)
      const newThread = await ThreadService.createThread();
      
      // Step 2: Switch to thread with URL update option (the fix)
      await result.current.switchToThread(newThread.id, {
        clearMessages: true,
        showLoadingIndicator: false,
        updateUrl: true, // This is the critical fix
      });
    });
    
    // Assert - wait for React state to be updated
    expect(mockCreateThread).toHaveBeenCalled();
    
    // Wait for hook state to be properly updated (React setState is async)
    await act(async () => {
      // Wait a bit for all state updates to complete
      await new Promise(resolve => setTimeout(resolve, 10));
    });
    
    expect(result.current.state.lastLoadedThreadId).toBe(newThreadId);
    
    // Verify URL was updated through router
    expect(mockRouter.replace).toHaveBeenCalledWith(
      expect.stringContaining(newThreadId),
      expect.objectContaining({ scroll: false })
    );
  });
  
  it('should not update URL if updateUrl option is false', async () => {
    // Arrange
    const newThreadId = 'new-thread-456';
    
    // Configure the thread loading service
    const { threadLoadingService } = require('@/services/threadLoadingService');
    threadLoadingService.loadThread.mockResolvedValue({
      success: true,
      messages: [],
      threadId: newThreadId,
    });
    
    (ThreadService.createThread as jest.Mock).mockResolvedValue({
      id: newThreadId,
      created_at: Date.now(),
      messages: [],
    });
    
    const { result } = renderHook(() => useThreadSwitching());
    
    // Act
    await act(async () => {
      const newThread = await ThreadService.createThread();
      await result.current.switchToThread(newThread.id, {
        clearMessages: true,
        updateUrl: false, // Explicitly disable URL update
      });
    });
    
    // Assert
    expect(mockRouter.replace).not.toHaveBeenCalled();
  });
  
  it('should handle errors gracefully when creating new chat', async () => {
    // Arrange
    const newThreadId = 'new-thread-456';
    const error = new Error('Failed to create thread');
    
    // Configure the thread loading service to fail
    const { threadLoadingService } = require('@/services/threadLoadingService');
    threadLoadingService.loadThread.mockRejectedValue(error);
    
    (ThreadService.createThread as jest.Mock).mockResolvedValue({
      id: newThreadId,
      created_at: Date.now(),
      messages: [],
    });
    
    const { result } = renderHook(() => useThreadSwitching());
    
    // Act - This WILL trigger the hook because the test simulates the actual flow
    await act(async () => {
      const newThread = await ThreadService.createThread();
      // The switchToThread will fail due to the loadThread mock rejection
      await result.current.switchToThread(newThread.id, {
        clearMessages: true,
        updateUrl: true,
      });
    });
    
    // URL should not be updated on error
    expect(mockRouter.replace).not.toHaveBeenCalled();
    // The hook SHOULD have an error because the operation failed
    expect(result.current.state.error).not.toBeNull();
    expect(result.current.state.error?.message).toContain('Thread loading failed');
  });
});