import React from 'react';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useLoadingState } from '@/hooks/useLoadingState';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useWebSocket } from '@/hooks/useWebSocket';
import { ChatLoadingState } from '@/types/loading-state';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
 { useLoadingState } from '@/hooks/useLoadingState';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useWebSocket } from '@/hooks/useWebSocket';
import { ChatLoadingState } from '@/types/loading-state';

// Mock the dependencies
jest.mock('@/store/unified-chat');
jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: jest.fn()
}));

describe('useLoadingState Hook', () => {
    jest.setTimeout(10000);
  const mockUseUnifiedChatStore = useUnifiedChatStore as jest.MockedFunction<typeof useUnifiedChatStore>;
  const mockUseWebSocket = useWebSocket as jest.MockedFunction<typeof useWebSocket>;

  beforeEach(() => {
    jest.clearAllMocks();
  });

  /**
   * Test Case 1: Hook should handle pre-connected WebSocket with active thread
   * This is the scenario that caused the "Loading chat..." stuck issue
   */
  it('should show example prompts when WebSocket already connected with empty thread', async () => {
    // Setup: WebSocket already connected, thread exists but no messages
    mockUseWebSocket.mockReturnValue({
      status: 'OPEN',
      messages: [],
      sendMessage: jest.fn()
    });

    // Mock individual store selectors to avoid infinite loops
    const mockStoreState = {
      activeThreadId: 'thread_123',
      isThreadLoading: false,
      messages: [],
      isProcessing: false,
      currentRunId: null,
      fastLayerData: null
    };

    // Mock each selector call individually
    mockUseUnifiedChatStore
      .mockImplementation((selector) => {
        if (typeof selector === 'function') {
          const state = {
            ...mockStoreState,
            fastLayerData: { agentName: null }
          };
          return selector(state);
        }
        return mockStoreState;
      });

    const { result } = renderHook(() => useLoadingState());

    // Wait for initialization
    await waitFor(() => {
      expect(result.current.isInitialized).toBe(true);
    });

    // Critical assertions - these should pass after the fix
    expect(result.current.shouldShowLoading).toBe(false);
    expect(result.current.shouldShowExamplePrompts).toBe(true);
    expect(result.current.shouldShowEmptyState).toBe(false);
    expect(result.current.loadingState).toBe(ChatLoadingState.THREAD_READY);
  });

  /**
   * Test Case 2: Hook should show loading state during WebSocket connection
   */
  it('should show loading state when WebSocket is connecting', async () => {
    mockUseWebSocket.mockReturnValue({
      status: 'CONNECTING',
      messages: [],
      sendMessage: jest.fn()
    });

    const mockStoreState = {
      activeThreadId: null,
      isThreadLoading: false,
      messages: [],
      isProcessing: false,
      currentRunId: null,
      fastLayerData: null
    };

    mockUseUnifiedChatStore
      .mockImplementation((selector) => {
        if (typeof selector === 'function') {
          return selector(mockStoreState);
        }
        return mockStoreState;
      });

    const { result } = renderHook(() => useLoadingState());

    await waitFor(() => {
      expect(result.current.isInitialized).toBe(false);
    });

    expect(result.current.shouldShowLoading).toBe(true);
    expect(result.current.loadingMessage).toBe('Loading chat...');
    expect(result.current.loadingState).toBe(ChatLoadingState.INITIALIZING);
  });

  /**
   * Test Case 3: Hook should handle thread loading correctly
   */
  it('should show loading when thread is being loaded', async () => {
    mockUseWebSocket.mockReturnValue({
      status: 'OPEN',
      messages: [],
      sendMessage: jest.fn()
    });

    const mockStoreState = {
      activeThreadId: 'thread_123',
      isThreadLoading: true, // Thread is loading
      messages: [],
      isProcessing: false,
      currentRunId: null,
      fastLayerData: null
    };

    mockUseUnifiedChatStore
      .mockImplementation((selector) => {
        if (typeof selector === 'function') {
          return selector(mockStoreState);
        }
        return mockStoreState;
      });

    const { result } = renderHook(() => useLoadingState());

    await waitFor(() => {
      expect(result.current.isInitialized).toBe(true);
    });

    expect(result.current.shouldShowLoading).toBe(true);
    expect(result.current.loadingMessage).toBe('Loading chat...');
    expect(result.current.loadingState).toBe(ChatLoadingState.INITIALIZING);
  });

  /**
   * Test Case 4: Hook should show empty state when no thread selected
   */
  it('should show empty state when connected but no thread selected', async () => {
    mockUseWebSocket.mockReturnValue({
      status: 'OPEN',
      messages: [],
      sendMessage: jest.fn()
    });

    const mockStoreState = {
      activeThreadId: null, // No thread selected
      isThreadLoading: false,
      messages: [],
      isProcessing: false,
      currentRunId: null,
      fastLayerData: null
    };

    mockUseUnifiedChatStore
      .mockImplementation((selector) => {
        if (typeof selector === 'function') {
          return selector(mockStoreState);
        }
        return mockStoreState;
      });

    const { result } = renderHook(() => useLoadingState());

    await waitFor(() => {
      expect(result.current.isInitialized).toBe(true);
    });

    expect(result.current.shouldShowLoading).toBe(false);
    expect(result.current.shouldShowEmptyState).toBe(true);
    expect(result.current.shouldShowExamplePrompts).toBe(false);
    expect(result.current.loadingState).toBe(ChatLoadingState.READY);
  });

  /**
   * Test Case 5: Hook should not show example prompts when messages exist
   */
  it('should not show example prompts when thread has messages', async () => {
    mockUseWebSocket.mockReturnValue({
      status: 'OPEN',
      messages: [],
      sendMessage: jest.fn()
    });

    const mockStoreState = {
      activeThreadId: 'thread_123',
      isThreadLoading: false,
      messages: [{ id: '1', content: 'Hello' }], // Thread has messages
      isProcessing: false,
      currentRunId: null,
      fastLayerData: null
    };

    mockUseUnifiedChatStore
      .mockImplementation((selector) => {
        if (typeof selector === 'function') {
          return selector(mockStoreState);
        }
        return mockStoreState;
      });

    const { result } = renderHook(() => useLoadingState());

    await waitFor(() => {
      expect(result.current.isInitialized).toBe(true);
    });

    expect(result.current.shouldShowLoading).toBe(false);
    expect(result.current.shouldShowExamplePrompts).toBe(false);
    expect(result.current.shouldShowEmptyState).toBe(false);
    expect(result.current.loadingState).toBe(ChatLoadingState.THREAD_READY);
  });

  /**
   * Test Case 6: Hook should handle processing state correctly
   */
  it('should show processing state when agent is running', async () => {
    mockUseWebSocket.mockReturnValue({
      status: 'OPEN',
      messages: [],
      sendMessage: jest.fn()
    });

    const mockStoreState = {
      activeThreadId: 'thread_123',
      isThreadLoading: false,
      messages: [{ id: '1', content: 'Hello' }],
      isProcessing: true, // Agent is processing
      currentRunId: 'run_123',
      fastLayerData: { agentName: 'triage' }
    };

    mockUseUnifiedChatStore
      .mockImplementation((selector) => {
        if (typeof selector === 'function') {
          return selector(mockStoreState);
        }
        return mockStoreState;
      });

    const { result } = renderHook(() => useLoadingState());

    await waitFor(() => {
      expect(result.current.isInitialized).toBe(true);
    });

    expect(result.current.shouldShowLoading).toBe(true);
    expect(result.current.shouldShowExamplePrompts).toBe(false);
    expect(result.current.loadingMessage).toBe('Loading chat...');
    expect(result.current.loadingState).toBe(ChatLoadingState.INITIALIZING);
  });

  /**
   * Test Case 7: Hook should handle WebSocket reconnection
   */
  it('should handle WebSocket reconnection gracefully', async () => {
    const { result, rerender } = renderHook(() => useLoadingState());

    // Start with disconnected state
    mockUseWebSocket.mockReturnValue({
      status: 'CLOSED',
      messages: [],
      sendMessage: jest.fn()
    });

    const disconnectedState = {
      activeThreadId: 'thread_123',
      isThreadLoading: false,
      messages: [],
      isProcessing: false,
      currentRunId: null,
      fastLayerData: null
    };

    mockUseUnifiedChatStore
      .mockImplementation((selector) => {
        if (typeof selector === 'function') {
          return selector(disconnectedState);
        }
        return disconnectedState;
      });

    rerender();

    // Should show initializing state when not initialized  
    await waitFor(() => {
      expect(result.current.loadingState).toBe(ChatLoadingState.INITIALIZING);
    });

    // Simulate reconnection
    mockUseWebSocket.mockReturnValue({
      status: 'CONNECTING',
      messages: [],
      sendMessage: jest.fn()
    });

    rerender();

    await waitFor(() => {
      expect(result.current.loadingState).toBe(ChatLoadingState.INITIALIZING);
    });

    // Complete reconnection
    mockUseWebSocket.mockReturnValue({
      status: 'OPEN',
      messages: [],
      sendMessage: jest.fn()
    });

    rerender();

    await waitFor(() => {
      expect(result.current.loadingState).toBe(ChatLoadingState.THREAD_READY);
    });

    expect(result.current.shouldShowLoading).toBe(false);
    expect(result.current.shouldShowExamplePrompts).toBe(true);
  });

  /**
   * Test Case 8: Hook should handle rapid state changes without errors
   */
  it('should handle rapid state changes without throwing errors', async () => {
    const { result, rerender } = renderHook(() => useLoadingState());

    const stateSequence = [
      { status: 'CONNECTING', activeThreadId: null, isThreadLoading: false },
      { status: 'OPEN', activeThreadId: null, isThreadLoading: false },
      { status: 'OPEN', activeThreadId: 'thread_123', isThreadLoading: true },
      { status: 'OPEN', activeThreadId: 'thread_123', isThreadLoading: false }
    ];

    for (const state of stateSequence) {
      mockUseWebSocket.mockReturnValue({
        status: state.status as any,
        messages: [],
        sendMessage: jest.fn()
      });

      const mockStoreState = {
        activeThreadId: state.activeThreadId,
        isThreadLoading: state.isThreadLoading,
        messages: [],
        isProcessing: false,
        currentRunId: null,
        fastLayerData: null
      };

      mockUseUnifiedChatStore
        .mockImplementation((selector) => {
          if (typeof selector === 'function') {
            return selector(mockStoreState);
          }
          return mockStoreState;
        });

      // Should not throw during rapid changes
      expect(() => rerender()).not.toThrow();
    }

    // Final state should be correct
    await waitFor(() => {
      expect(result.current.loadingState).toBe(ChatLoadingState.THREAD_READY);
    });
  });
});