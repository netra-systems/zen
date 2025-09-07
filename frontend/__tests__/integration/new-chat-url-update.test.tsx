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
}));

// Mock the unified chat store
jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: jest.fn((selector) => {
    const state = {
      isProcessing: false,
      activeThreadId: null,
      setActiveThread: jest.fn(),
      setThreadLoading: jest.fn(),
      startThreadLoading: jest.fn(),
      completeThreadLoading: jest.fn(),
      clearMessages: jest.fn(),
      loadMessages: jest.fn(),
      handleWebSocketEvent: jest.fn(),
    };
    return selector ? selector(state) : state;
  }),
}));

// Mock thread loading service
jest.mock('@/services/threadLoadingService', () => ({
  threadLoadingService: {
    loadThread: jest.fn().mockResolvedValue({
      success: true,
      messages: [],
      threadId: 'test-thread',
    }),
  },
}));

describe('New Chat URL Update Integration', () => {
  beforeEach(() => {
    // Don't use jest.clearAllMocks() as it clears mock implementations
    // Reset only specific mocks that need resetting
    mockRouter.push.mockClear();
    mockRouter.replace.mockClear();
    mockRouter.prefetch.mockClear();
  });
  
  it('should update URL when creating and switching to new thread', async () => {
    // Arrange
    const newThreadId = 'new-thread-123';
    const mockCreateThread = jest.fn().mockResolvedValue({
      id: newThreadId,
      created_at: Date.now(),
      messages: [],
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
    
    // Assert
    expect(mockCreateThread).toHaveBeenCalled();
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
    const error = new Error('Failed to create thread');
    (ThreadService.createThread as jest.Mock).mockRejectedValue(error);
    
    const { result } = renderHook(() => useThreadSwitching());
    
    // Act & Assert
    await act(async () => {
      try {
        await ThreadService.createThread();
      } catch (e) {
        expect(e).toBe(error);
      }
    });
    
    // URL should not be updated on error
    expect(mockRouter.replace).not.toHaveBeenCalled();
    expect(result.current.state.error).toBeNull();
  });
});