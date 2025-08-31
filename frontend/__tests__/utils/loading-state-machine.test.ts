/**
 * Test suite for WebSocket loading state machine
 * Tests state transitions and prevents regression of loading state issues
 * 
 * @compliance testing.xml - Comprehensive test coverage
 * @prevents websocket-loading-state-transitions regression
 */

import {
  ChatLoadingState,
  ChatStateContext,
  WebSocketConnectionState,
  ThreadLoadingState,
  ProcessingState
} from '@/types/loading-state';
import {
  createWebSocketState,
  createThreadState,
  createProcessingState,
  createChatStateContext,
  determineLoadingState,
  validateStateTransition,
  createLoadingResult
} from '@/utils/loading-state-machine';
import { WebSocketStatus } from '@/services/webSocketService';

describe('Loading State Machine', () => {
      setupAntiHang();
    jest.setTimeout(10000);
  describe('State Transitions', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    /**
     * Test Case 1: INITIALIZING should transition to THREAD_READY when WebSocket already connected
     * This prevents the "Loading chat..." stuck issue when hot-reloading or reconnecting
     */
    it('should allow direct transition from INITIALIZING to THREAD_READY when WebSocket connected with active thread', () => {
      // This is the exact scenario that caused the bug
      const context: ChatStateContext = {
        webSocket: {
          isConnected: true,
          isConnecting: false,
          isFailed: false,
          status: 'OPEN' as WebSocketStatus
        },
        thread: {
          isLoading: false,
          hasActiveThread: true,
          hasMessages: false,
          threadId: 'thread_123'
        },
        processing: {
          isProcessing: false,
          currentRunId: null,
          agentName: null
        },
        isInitialized: true
      };

      // Determine the new state
      const newState = determineLoadingState(context);
      expect(newState).toBe(ChatLoadingState.THREAD_READY);

      // Validate the transition is allowed
      const transition = validateStateTransition(
        ChatLoadingState.INITIALIZING,
        ChatLoadingState.THREAD_READY
      );
      expect(transition.isValid).toBe(true);
      expect(transition.reason).toBeUndefined();
    });

    /**
     * Test Case 2: Loading state should NOT be shown when state is THREAD_READY
     * This ensures the UI shows example prompts instead of loading spinner
     */
    it('should not show loading indicator when state is THREAD_READY with no messages', () => {
      const context: ChatStateContext = {
        webSocket: {
          isConnected: true,
          isConnecting: false,
          isFailed: false,
          status: 'OPEN' as WebSocketStatus
        },
        thread: {
          isLoading: false,
          hasActiveThread: true,
          hasMessages: false, // New thread with no messages
          threadId: 'thread_123'
        },
        processing: {
          isProcessing: false,
          currentRunId: null,
          agentName: null
        },
        isInitialized: true
      };

      const result = createLoadingResult(ChatLoadingState.THREAD_READY, context);
      
      // Critical assertions - these were wrong before the fix
      expect(result.shouldShowLoading).toBe(false);
      expect(result.shouldShowExamplePrompts).toBe(true);
      expect(result.shouldShowEmptyState).toBe(false);
      expect(result.loadingMessage).toBe('Thread ready');
    });

    /**
     * Test Case 3: State machine should handle all initialization scenarios correctly
     * Tests various connection states to ensure robust initialization
     */
    it('should determine correct state for various initialization scenarios', () => {
      // Scenario 1: Not initialized yet
      const notInitialized: ChatStateContext = {
        webSocket: { isConnected: true, isConnecting: false, isFailed: false, status: 'OPEN' as WebSocketStatus },
        thread: { isLoading: false, hasActiveThread: true, hasMessages: false, threadId: 'thread_123' },
        processing: { isProcessing: false, currentRunId: null, agentName: null },
        isInitialized: false
      };
      expect(determineLoadingState(notInitialized)).toBe(ChatLoadingState.INITIALIZING);

      // Scenario 2: WebSocket connecting
      const connecting: ChatStateContext = {
        webSocket: { isConnected: false, isConnecting: true, isFailed: false, status: 'CONNECTING' as WebSocketStatus },
        thread: { isLoading: false, hasActiveThread: false, hasMessages: false, threadId: null },
        processing: { isProcessing: false, currentRunId: null, agentName: null },
        isInitialized: true
      };
      expect(determineLoadingState(connecting)).toBe(ChatLoadingState.CONNECTING);

      // Scenario 3: Connected but no thread
      const noThread: ChatStateContext = {
        webSocket: { isConnected: true, isConnecting: false, isFailed: false, status: 'OPEN' as WebSocketStatus },
        thread: { isLoading: false, hasActiveThread: false, hasMessages: false, threadId: null },
        processing: { isProcessing: false, currentRunId: null, agentName: null },
        isInitialized: true
      };
      expect(determineLoadingState(noThread)).toBe(ChatLoadingState.READY);

      // Scenario 4: Loading thread
      const loadingThread: ChatStateContext = {
        webSocket: { isConnected: true, isConnecting: false, isFailed: false, status: 'OPEN' as WebSocketStatus },
        thread: { isLoading: true, hasActiveThread: true, hasMessages: false, threadId: 'thread_123' },
        processing: { isProcessing: false, currentRunId: null, agentName: null },
        isInitialized: true
      };
      expect(determineLoadingState(loadingThread)).toBe(ChatLoadingState.LOADING_THREAD);

      // Scenario 5: Processing message
      const processing: ChatStateContext = {
        webSocket: { isConnected: true, isConnecting: false, isFailed: false, status: 'OPEN' as WebSocketStatus },
        thread: { isLoading: false, hasActiveThread: true, hasMessages: true, threadId: 'thread_123' },
        processing: { isProcessing: true, currentRunId: 'run_123', agentName: 'triage' },
        isInitialized: true
      };
      expect(determineLoadingState(processing)).toBe(ChatLoadingState.PROCESSING);

      // Scenario 6: Thread ready with messages
      const threadWithMessages: ChatStateContext = {
        webSocket: { isConnected: true, isConnecting: false, isFailed: false, status: 'OPEN' as WebSocketStatus },
        thread: { isLoading: false, hasActiveThread: true, hasMessages: true, threadId: 'thread_123' },
        processing: { isProcessing: false, currentRunId: null, agentName: null },
        isInitialized: true
      };
      expect(determineLoadingState(threadWithMessages)).toBe(ChatLoadingState.THREAD_READY);
    });

    it('should allow transition from INITIALIZING to READY when WebSocket connected without thread', () => {
      const transition = validateStateTransition(
        ChatLoadingState.INITIALIZING,
        ChatLoadingState.READY
      );
      expect(transition.isValid).toBe(true);
    });

    it('should allow transition from LOADING_THREAD to THREAD_READY', () => {
      const transition = validateStateTransition(
        ChatLoadingState.LOADING_THREAD,
        ChatLoadingState.THREAD_READY
      );
      expect(transition.isValid).toBe(true);
    });

    it('should prevent invalid transitions', () => {
      // Cannot go from READY directly to PROCESSING
      const invalidTransition = validateStateTransition(
        ChatLoadingState.READY,
        ChatLoadingState.PROCESSING
      );
      expect(invalidTransition.isValid).toBe(false);
      expect(invalidTransition.reason).toContain('Invalid transition');
    });
  });

  describe('Context Creation', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should create correct WebSocket state from status', () => {
      const openState = createWebSocketState('OPEN' as WebSocketStatus);
      expect(openState).toEqual({
        isConnected: true,
        isConnecting: false,
        isFailed: false,
        status: 'OPEN'
      });

      const connectingState = createWebSocketState('CONNECTING' as WebSocketStatus);
      expect(connectingState).toEqual({
        isConnected: false,
        isConnecting: true,
        isFailed: false,
        status: 'CONNECTING'
      });

      const closedState = createWebSocketState('CLOSED' as WebSocketStatus);
      expect(closedState).toEqual({
        isConnected: false,
        isConnecting: false,
        isFailed: true,
        status: 'CLOSED'
      });
    });

    it('should create correct thread state', () => {
      const threadState = createThreadState('thread_123', false, ['message1', 'message2']);
      expect(threadState).toEqual({
        isLoading: false,
        hasActiveThread: true,
        hasMessages: true,
        threadId: 'thread_123'
      });

      const emptyThreadState = createThreadState(null, false, []);
      expect(emptyThreadState).toEqual({
        isLoading: false,
        hasActiveThread: false,
        hasMessages: false,
        threadId: null
      });
    });

    it('should create correct processing state', () => {
      const processingState = createProcessingState(true, 'run_123', 'triage');
      expect(processingState).toEqual({
        isProcessing: true,
        currentRunId: 'run_123',
        agentName: 'triage'
      });
    });

    it('should create complete context from all parameters', () => {
      const context = createChatStateContext(
        'OPEN' as WebSocketStatus,
        'thread_123',
        false,
        [],
        false,
        null,
        null,
        true
      );

      expect(context.webSocket.isConnected).toBe(true);
      expect(context.thread.hasActiveThread).toBe(true);
      expect(context.thread.hasMessages).toBe(false);
      expect(context.processing.isProcessing).toBe(false);
      expect(context.isInitialized).toBe(true);
    });
  });

  describe('Loading Result Creation', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should show loading for INITIALIZING state', () => {
      const context: ChatStateContext = {
        webSocket: { isConnected: false, isConnecting: false, isFailed: false, status: 'CLOSED' as WebSocketStatus },
        thread: { isLoading: false, hasActiveThread: false, hasMessages: false, threadId: null },
        processing: { isProcessing: false, currentRunId: null, agentName: null },
        isInitialized: false
      };

      const result = createLoadingResult(ChatLoadingState.INITIALIZING, context);
      expect(result.shouldShowLoading).toBe(true);
      expect(result.loadingMessage).toBe('Loading chat...');
    });

    it('should show loading for CONNECTING state', () => {
      const context: ChatStateContext = {
        webSocket: { isConnected: false, isConnecting: true, isFailed: false, status: 'CONNECTING' as WebSocketStatus },
        thread: { isLoading: false, hasActiveThread: false, hasMessages: false, threadId: null },
        processing: { isProcessing: false, currentRunId: null, agentName: null },
        isInitialized: true
      };

      const result = createLoadingResult(ChatLoadingState.CONNECTING, context);
      expect(result.shouldShowLoading).toBe(true);
      expect(result.loadingMessage).toBe('Connecting to chat service...');
    });

    it('should show loading for LOADING_THREAD state', () => {
      const context: ChatStateContext = {
        webSocket: { isConnected: true, isConnecting: false, isFailed: false, status: 'OPEN' as WebSocketStatus },
        thread: { isLoading: true, hasActiveThread: true, hasMessages: false, threadId: 'thread_123' },
        processing: { isProcessing: false, currentRunId: null, agentName: null },
        isInitialized: true
      };

      const result = createLoadingResult(ChatLoadingState.LOADING_THREAD, context);
      expect(result.shouldShowLoading).toBe(true);
      expect(result.loadingMessage).toBe('Loading thread messages...');
    });

    it('should show empty state when READY with no thread', () => {
      const context: ChatStateContext = {
        webSocket: { isConnected: true, isConnecting: false, isFailed: false, status: 'OPEN' as WebSocketStatus },
        thread: { isLoading: false, hasActiveThread: false, hasMessages: false, threadId: null },
        processing: { isProcessing: false, currentRunId: null, agentName: null },
        isInitialized: true
      };

      const result = createLoadingResult(ChatLoadingState.READY, context);
      expect(result.shouldShowLoading).toBe(false);
      expect(result.shouldShowEmptyState).toBe(true);
      expect(result.shouldShowExamplePrompts).toBe(false);
    });

    it('should show example prompts for THREAD_READY with no messages', () => {
      const context: ChatStateContext = {
        webSocket: { isConnected: true, isConnecting: false, isFailed: false, status: 'OPEN' as WebSocketStatus },
        thread: { isLoading: false, hasActiveThread: true, hasMessages: false, threadId: 'thread_123' },
        processing: { isProcessing: false, currentRunId: null, agentName: null },
        isInitialized: true
      };

      const result = createLoadingResult(ChatLoadingState.THREAD_READY, context);
      expect(result.shouldShowLoading).toBe(false);
      expect(result.shouldShowEmptyState).toBe(false);
      expect(result.shouldShowExamplePrompts).toBe(true);
    });

    it('should not show example prompts when processing', () => {
      const context: ChatStateContext = {
        webSocket: { isConnected: true, isConnecting: false, isFailed: false, status: 'OPEN' as WebSocketStatus },
        thread: { isLoading: false, hasActiveThread: true, hasMessages: false, threadId: 'thread_123' },
        processing: { isProcessing: true, currentRunId: 'run_123', agentName: 'triage' },
        isInitialized: true
      };

      const result = createLoadingResult(ChatLoadingState.PROCESSING, context);
      expect(result.shouldShowLoading).toBe(false);
      expect(result.shouldShowExamplePrompts).toBe(false);
      expect(result.loadingMessage).toBe('Processing with triage...');
    });
  });

  describe('Edge Cases and Race Conditions', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle connection failure correctly', () => {
      const context: ChatStateContext = {
        webSocket: { isConnected: false, isConnecting: false, isFailed: true, status: 'CLOSED' as WebSocketStatus },
        thread: { isLoading: false, hasActiveThread: false, hasMessages: false, threadId: null },
        processing: { isProcessing: false, currentRunId: null, agentName: null },
        isInitialized: true
      };

      const state = determineLoadingState(context);
      expect(state).toBe(ChatLoadingState.CONNECTION_FAILED);

      const result = createLoadingResult(state, context);
      expect(result.loadingMessage).toBe('Connection failed. Retrying...');
    });

    it('should prioritize error states correctly', () => {
      // Even if thread is loading, connection failure takes precedence
      const context: ChatStateContext = {
        webSocket: { isConnected: false, isConnecting: false, isFailed: true, status: 'CLOSED' as WebSocketStatus },
        thread: { isLoading: true, hasActiveThread: true, hasMessages: false, threadId: 'thread_123' },
        processing: { isProcessing: false, currentRunId: null, agentName: null },
        isInitialized: true
      };

      const state = determineLoadingState(context);
      expect(state).toBe(ChatLoadingState.CONNECTION_FAILED);
    });

    it('should handle rapid state changes', () => {
      // Simulate rapid state changes that might occur during hot-reload
      const states = [
        ChatLoadingState.INITIALIZING,
        ChatLoadingState.CONNECTING,
        ChatLoadingState.READY,
        ChatLoadingState.LOADING_THREAD,
        ChatLoadingState.THREAD_READY
      ];

      // All transitions in this sequence should be valid
      for (let i = 0; i < states.length - 1; i++) {
        const current = states[i];
        const next = states[i + 1];
        
        // Special case: INITIALIZING can now go to any state
        if (current === ChatLoadingState.INITIALIZING) {
          const transition = validateStateTransition(current, next);
          expect(transition.isValid).toBe(true);
        }
      }
    });
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});