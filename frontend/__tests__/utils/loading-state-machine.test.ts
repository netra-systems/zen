/**
 * Loading State Machine Comprehensive Unit Tests
 * 
 * Business Value Justification (BVJ):
 * - Segment: Platform/Internal + All User Segments (Free, Early, Mid, Enterprise)
 * - Business Goal: Ensure predictable loading states prevent user confusion and abandonment
 * - Value Impact: Proper loading states guide users through chat initialization, preventing dropoff
 * - Strategic Impact: Core UX for chat functionality - prevents "broken UI" perception
 * 
 * CRITICAL: These tests validate the loading state machine logic that determines
 * when to show loading indicators, empty states, example prompts, and error states.
 * This directly impacts user experience and perceived platform reliability.
 * 
 * Test Difficulty: HIGH (60% expected failure rate on edge cases)
 * - Complex state determination logic with multiple input variables
 * - UI flag generation edge cases
 * - State transition validation with timing dependencies
 * - Context assembly race conditions
 * 
 * @compliance TEST_CREATION_GUIDE.md - Follows SSOT patterns for frontend tests
 * @compliance CLAUDE.md - Real business value tests, validates actual UI state logic
 */

import {
  createWebSocketState,
  createThreadState,
  createProcessingState,
  determineLoadingState,
  validateStateTransition,
  createLoadingResult,
  createChatStateContext,
} from '@/utils/loading-state-machine';

import {
  ChatLoadingState,
  WebSocketConnectionState,
  ThreadLoadingState,
  ProcessingState,
  ChatStateContext,
  LoadingStateResult,
  StateTransitionResult,
} from '@/types/loading-state';

import { WebSocketStatus } from '@/services/webSocketService';

describe('Loading State Machine Core Functions', () => {
  describe('State Creation Functions', () => {
    describe('createWebSocketState', () => {
      it('should create correct WebSocket state for OPEN status', () => {
        const state = createWebSocketState('OPEN');
        
        expect(state).toEqual({
          isConnected: true,
          isConnecting: false,
          isFailed: false,
          status: 'OPEN'
        });
      });

      it('should create correct WebSocket state for CONNECTING status', () => {
        const state = createWebSocketState('CONNECTING');
        
        expect(state).toEqual({
          isConnected: false,
          isConnecting: true,
          isFailed: false,
          status: 'CONNECTING'
        });
      });

      it('should create correct WebSocket state for CLOSED status', () => {
        const state = createWebSocketState('CLOSED');
        
        expect(state).toEqual({
          isConnected: false,
          isConnecting: false,
          isFailed: true,
          status: 'CLOSED'
        });
      });

      it('should handle all WebSocket status types correctly', () => {
        const statusMappings: Array<{
          status: WebSocketStatus;
          expectedConnected: boolean;
          expectedConnecting: boolean;
          expectedFailed: boolean;
        }> = [
          { status: 'CONNECTING', expectedConnected: false, expectedConnecting: true, expectedFailed: false },
          { status: 'OPEN', expectedConnected: true, expectedConnecting: false, expectedFailed: false },
          { status: 'CLOSING', expectedConnected: false, expectedConnecting: false, expectedFailed: true },
          { status: 'CLOSED', expectedConnected: false, expectedConnecting: false, expectedFailed: true },
        ];

        statusMappings.forEach(({ status, expectedConnected, expectedConnecting, expectedFailed }) => {
          const state = createWebSocketState(status);
          
          expect(state.isConnected).toBe(expectedConnected);
          expect(state.isConnecting).toBe(expectedConnecting);
          expect(state.isFailed).toBe(expectedFailed);
          expect(state.status).toBe(status);
        });
      });
    });

    describe('createThreadState', () => {
      it('should create correct thread state with active thread', () => {
        const messages = [
          { id: '1', content: 'Hello' },
          { id: '2', content: 'World' }
        ];
        
        const state = createThreadState('thread-123', false, messages);
        
        expect(state).toEqual({
          isLoading: false,
          hasActiveThread: true,
          hasMessages: true,
          threadId: 'thread-123'
        });
      });

      it('should create correct thread state with no thread', () => {
        const state = createThreadState(null, false, []);
        
        expect(state).toEqual({
          isLoading: false,
          hasActiveThread: false,
          hasMessages: false,
          threadId: null
        });
      });

      it('should handle loading state correctly', () => {
        const state = createThreadState('thread-456', true, []);
        
        expect(state).toEqual({
          isLoading: true,
          hasActiveThread: true,
          hasMessages: false,
          threadId: 'thread-456'
        });
      });

      it('should handle edge case with thread but no messages', () => {
        const state = createThreadState('empty-thread', false, []);
        
        expect(state).toEqual({
          isLoading: false,
          hasActiveThread: true,
          hasMessages: false,
          threadId: 'empty-thread'
        });
      });
    });

    describe('createProcessingState', () => {
      it('should create correct processing state when active', () => {
        const state = createProcessingState(true, 'run-789', 'data_analyzer');
        
        expect(state).toEqual({
          isProcessing: true,
          currentRunId: 'run-789',
          agentName: 'data_analyzer'
        });
      });

      it('should create correct processing state when idle', () => {
        const state = createProcessingState(false, null, null);
        
        expect(state).toEqual({
          isProcessing: false,
          currentRunId: null,
          agentName: null
        });
      });

      it('should handle processing state with partial information', () => {
        const state = createProcessingState(true, 'run-123', null);
        
        expect(state).toEqual({
          isProcessing: true,
          currentRunId: 'run-123',
          agentName: null
        });
      });
    });
  });

  describe('State Determination Logic', () => {
    describe('determineLoadingState', () => {
      it('should return INITIALIZING when not initialized', () => {
        const context: ChatStateContext = {
          isInitialized: false,
          webSocket: createWebSocketState('OPEN'),
          thread: createThreadState('thread-1', false, []),
          processing: createProcessingState(false, null, null)
        };

        const state = determineLoadingState(context);
        expect(state).toBe(ChatLoadingState.INITIALIZING);
      });

      it('should return CONNECTING when WebSocket is connecting', () => {
        const context: ChatStateContext = {
          isInitialized: true,
          webSocket: createWebSocketState('CONNECTING'),
          thread: createThreadState(null, false, []),
          processing: createProcessingState(false, null, null)
        };

        const state = determineLoadingState(context);
        expect(state).toBe(ChatLoadingState.CONNECTING);
      });

      it('should return CONNECTION_FAILED when WebSocket connection failed', () => {
        const context: ChatStateContext = {
          isInitialized: true,
          webSocket: createWebSocketState('CLOSED'),
          thread: createThreadState(null, false, []),
          processing: createProcessingState(false, null, null)
        };

        const state = determineLoadingState(context);
        expect(state).toBe(ChatLoadingState.CONNECTION_FAILED);
      });

      it('should return LOADING_THREAD when thread is loading', () => {
        const context: ChatStateContext = {
          isInitialized: true,
          webSocket: createWebSocketState('OPEN'),
          thread: createThreadState('thread-1', true, []),
          processing: createProcessingState(false, null, null)
        };

        const state = determineLoadingState(context);
        expect(state).toBe(ChatLoadingState.LOADING_THREAD);
      });

      it('should return PROCESSING when agent is processing', () => {
        const context: ChatStateContext = {
          isInitialized: true,
          webSocket: createWebSocketState('OPEN'),
          thread: createThreadState('thread-1', false, [{ id: '1', content: 'Test' }]),
          processing: createProcessingState(true, 'run-1', 'test_agent')
        };

        const state = determineLoadingState(context);
        expect(state).toBe(ChatLoadingState.PROCESSING);
      });

      it('should return READY when no active thread', () => {
        const context: ChatStateContext = {
          isInitialized: true,
          webSocket: createWebSocketState('OPEN'),
          thread: createThreadState(null, false, []),
          processing: createProcessingState(false, null, null)
        };

        const state = determineLoadingState(context);
        expect(state).toBe(ChatLoadingState.READY);
      });

      it('should return THREAD_READY when thread is active and not loading', () => {
        const context: ChatStateContext = {
          isInitialized: true,
          webSocket: createWebSocketState('OPEN'),
          thread: createThreadState('thread-1', false, [{ id: '1', content: 'Message' }]),
          processing: createProcessingState(false, null, null)
        };

        const state = determineLoadingState(context);
        expect(state).toBe(ChatLoadingState.THREAD_READY);
      });

      it('should handle priority order correctly', () => {
        // Test that state determination follows correct priority
        // INITIALIZING has highest priority
        const uninitializedContext: ChatStateContext = {
          isInitialized: false,
          webSocket: createWebSocketState('CONNECTING'), // Would normally be CONNECTING
          thread: createThreadState('thread-1', true, []), // Would normally be LOADING_THREAD
          processing: createProcessingState(true, 'run-1', 'agent') // Would normally be PROCESSING
        };

        expect(determineLoadingState(uninitializedContext)).toBe(ChatLoadingState.INITIALIZING);

        // CONNECTING has second priority
        const connectingContext: ChatStateContext = {
          isInitialized: true,
          webSocket: createWebSocketState('CONNECTING'),
          thread: createThreadState('thread-1', true, []), // Would normally be LOADING_THREAD
          processing: createProcessingState(true, 'run-1', 'agent') // Would normally be PROCESSING
        };

        expect(determineLoadingState(connectingContext)).toBe(ChatLoadingState.CONNECTING);

        // PROCESSING has priority over THREAD_READY
        const processingContext: ChatStateContext = {
          isInitialized: true,
          webSocket: createWebSocketState('OPEN'),
          thread: createThreadState('thread-1', false, [{ id: '1', content: 'Message' }]), // Would be THREAD_READY
          processing: createProcessingState(true, 'run-1', 'agent')
        };

        expect(determineLoadingState(processingContext)).toBe(ChatLoadingState.PROCESSING);
      });
    });

    describe('State Transition Validation', () => {
      it('should validate legal state transitions', () => {
        const validTransitions: Array<[ChatLoadingState, ChatLoadingState]> = [
          [ChatLoadingState.INITIALIZING, ChatLoadingState.CONNECTING],
          [ChatLoadingState.INITIALIZING, ChatLoadingState.READY],
          [ChatLoadingState.INITIALIZING, ChatLoadingState.THREAD_READY],
          [ChatLoadingState.CONNECTING, ChatLoadingState.READY],
          [ChatLoadingState.CONNECTING, ChatLoadingState.CONNECTION_FAILED],
          [ChatLoadingState.READY, ChatLoadingState.LOADING_THREAD],
          [ChatLoadingState.LOADING_THREAD, ChatLoadingState.THREAD_READY],
          [ChatLoadingState.THREAD_READY, ChatLoadingState.PROCESSING],
          [ChatLoadingState.PROCESSING, ChatLoadingState.THREAD_READY],
        ];

        validTransitions.forEach(([from, to]) => {
          const result = validateStateTransition(from, to);
          expect(result.isValid).toBe(true);
          expect(result.newState).toBe(to);
          expect(result.reason).toBeUndefined();
        });
      });

      it('should reject invalid state transitions', () => {
        const invalidTransitions: Array<[ChatLoadingState, ChatLoadingState]> = [
          [ChatLoadingState.READY, ChatLoadingState.INITIALIZING], // Can't go back to initializing
          [ChatLoadingState.THREAD_READY, ChatLoadingState.CONNECTING], // Can't go back to connecting
          [ChatLoadingState.PROCESSING, ChatLoadingState.READY], // Can't skip THREAD_READY
          [ChatLoadingState.CONNECTION_FAILED, ChatLoadingState.PROCESSING], // Can't process without connection
        ];

        invalidTransitions.forEach(([from, to]) => {
          const result = validateStateTransition(from, to);
          expect(result.isValid).toBe(false);
          expect(result.newState).toBe(to);
          expect(result.reason).toContain('Invalid transition');
        });
      });

      it('should allow error recovery transitions', () => {
        const errorRecoveryTransitions: Array<[ChatLoadingState, ChatLoadingState]> = [
          [ChatLoadingState.CONNECTION_FAILED, ChatLoadingState.CONNECTING],
          [ChatLoadingState.ERROR, ChatLoadingState.INITIALIZING],
          [ChatLoadingState.ERROR, ChatLoadingState.CONNECTING],
        ];

        errorRecoveryTransitions.forEach(([from, to]) => {
          const result = validateStateTransition(from, to);
          expect(result.isValid).toBe(true);
        });
      });
    });
  });

  describe('UI State Generation', () => {
    describe('createLoadingResult', () => {
      it('should create correct loading result for INITIALIZING state', () => {
        const context = createChatStateContext(
          'CONNECTING', null, false, [], false, null, null, false
        );
        
        const result = createLoadingResult(ChatLoadingState.INITIALIZING, context);

        expect(result).toEqual({
          state: ChatLoadingState.INITIALIZING,
          shouldShowLoading: true,
          shouldShowEmptyState: false,
          shouldShowExamplePrompts: false,
          loadingMessage: 'Loading chat...'
        });
      });

      it('should create correct loading result for CONNECTING state', () => {
        const context = createChatStateContext(
          'CONNECTING', null, false, [], false, null, null, true
        );
        
        const result = createLoadingResult(ChatLoadingState.CONNECTING, context);

        expect(result).toEqual({
          state: ChatLoadingState.CONNECTING,
          shouldShowLoading: true,
          shouldShowEmptyState: false,
          shouldShowExamplePrompts: false,
          loadingMessage: 'Connecting to chat service...'
        });
      });

      it('should create correct loading result for READY state', () => {
        const context = createChatStateContext(
          'OPEN', null, false, [], false, null, null, true
        );
        
        const result = createLoadingResult(ChatLoadingState.READY, context);

        expect(result).toEqual({
          state: ChatLoadingState.READY,
          shouldShowLoading: false,
          shouldShowEmptyState: true,
          shouldShowExamplePrompts: false,
          loadingMessage: 'Ready'
        });
      });

      it('should create correct loading result for THREAD_READY with no messages', () => {
        const context = createChatStateContext(
          'OPEN', 'thread-123', false, [], false, null, null, true
        );
        
        const result = createLoadingResult(ChatLoadingState.THREAD_READY, context);

        expect(result).toEqual({
          state: ChatLoadingState.THREAD_READY,
          shouldShowLoading: false,
          shouldShowEmptyState: false,
          shouldShowExamplePrompts: true, // Should show prompts for empty thread
          loadingMessage: 'Thread ready'
        });
      });

      it('should create correct loading result for THREAD_READY with messages', () => {
        const messages = [{ id: '1', content: 'Existing message' }];
        const context = createChatStateContext(
          'OPEN', 'thread-123', false, messages, false, null, null, true
        );
        
        const result = createLoadingResult(ChatLoadingState.THREAD_READY, context);

        expect(result).toEqual({
          state: ChatLoadingState.THREAD_READY,
          shouldShowLoading: false,
          shouldShowEmptyState: false,
          shouldShowExamplePrompts: false, // Should NOT show prompts when messages exist
          loadingMessage: 'Thread ready'
        });
      });

      it('should create correct loading result for PROCESSING state', () => {
        const context = createChatStateContext(
          'OPEN', 'thread-123', false, [{ id: '1', content: 'Message' }], true, 'run-456', 'data_analyzer', true
        );
        
        const result = createLoadingResult(ChatLoadingState.PROCESSING, context);

        expect(result).toEqual({
          state: ChatLoadingState.PROCESSING,
          shouldShowLoading: false, // Processing should NOT show loading indicator
          shouldShowEmptyState: false,
          shouldShowExamplePrompts: false,
          loadingMessage: 'Processing with data_analyzer...'
        });
      });

      it('should create correct loading result for LOADING_THREAD state', () => {
        const context = createChatStateContext(
          'OPEN', 'thread-123', true, [], false, null, null, true
        );
        
        const result = createLoadingResult(ChatLoadingState.LOADING_THREAD, context);

        expect(result).toEqual({
          state: ChatLoadingState.LOADING_THREAD,
          shouldShowLoading: true,
          shouldShowEmptyState: false,
          shouldShowExamplePrompts: false,
          loadingMessage: 'Loading thread messages...'
        });
      });

      it('should handle processing state with no agent name', () => {
        const context = createChatStateContext(
          'OPEN', 'thread-123', false, [{ id: '1', content: 'Message' }], true, 'run-456', null, true
        );
        
        const result = createLoadingResult(ChatLoadingState.PROCESSING, context);

        expect(result.loadingMessage).toBe('Processing with agent...');
      });
    });

    describe('Edge Cases and Business Logic', () => {
      it('should handle rapid state changes correctly', () => {
        // Simulate rapid state changes that could happen during initialization
        const baseContext = createChatStateContext(
          'CONNECTING', null, false, [], false, null, null, false
        );

        // Test sequence: INITIALIZING -> CONNECTING -> READY -> THREAD_READY
        let state = determineLoadingState(baseContext);
        expect(state).toBe(ChatLoadingState.INITIALIZING);

        // Initialize
        const initializedContext = { ...baseContext, isInitialized: true };
        state = determineLoadingState(initializedContext);
        expect(state).toBe(ChatLoadingState.CONNECTING);

        // Connect
        const connectedContext = {
          ...initializedContext,
          webSocket: createWebSocketState('OPEN')
        };
        state = determineLoadingState(connectedContext);
        expect(state).toBe(ChatLoadingState.READY);

        // Load thread
        const threadLoadedContext = {
          ...connectedContext,
          thread: createThreadState('thread-123', false, [])
        };
        state = determineLoadingState(threadLoadedContext);
        expect(state).toBe(ChatLoadingState.THREAD_READY);

        // Validate each transition was legal
        expect(validateStateTransition(ChatLoadingState.INITIALIZING, ChatLoadingState.CONNECTING).isValid).toBe(true);
        expect(validateStateTransition(ChatLoadingState.CONNECTING, ChatLoadingState.READY).isValid).toBe(true);
        expect(validateStateTransition(ChatLoadingState.READY, ChatLoadingState.THREAD_READY).isValid).toBe(false); // Should go through LOADING_THREAD
      });

      it('should handle concurrent operations correctly', () => {
        // Test state machine behavior when multiple async operations are happening
        const context = createChatStateContext(
          'OPEN', 'thread-123', true, [], true, 'run-456', 'concurrent_agent', true
        );

        // Thread loading + processing should prioritize thread loading
        const state = determineLoadingState(context);
        expect(state).toBe(ChatLoadingState.LOADING_THREAD);

        // After thread loads, should show processing
        const threadLoadedContext = {
          ...context,
          thread: createThreadState('thread-123', false, [{ id: '1', content: 'Message' }])
        };

        const newState = determineLoadingState(threadLoadedContext);
        expect(newState).toBe(ChatLoadingState.PROCESSING);
      });

      it('should handle error states correctly', () => {
        const errorContext = createChatStateContext(
          'CLOSED', null, false, [], false, null, null, true
        );

        const state = determineLoadingState(errorContext);
        expect(state).toBe(ChatLoadingState.CONNECTION_FAILED);

        const result = createLoadingResult(state, errorContext);
        expect(result.shouldShowLoading).toBe(false);
        expect(result.shouldShowEmptyState).toBe(false);
        expect(result.shouldShowExamplePrompts).toBe(false);
        expect(result.loadingMessage).toBe('Connection failed. Retrying...');
      });

      it('should handle WebSocket reconnection scenarios', () => {
        // Start with failed connection
        let context = createChatStateContext('CLOSED', null, false, [], false, null, null, true);
        let state = determineLoadingState(context);
        expect(state).toBe(ChatLoadingState.CONNECTION_FAILED);

        // Attempt reconnection
        context = { ...context, webSocket: createWebSocketState('CONNECTING') };
        state = determineLoadingState(context);
        expect(state).toBe(ChatLoadingState.CONNECTING);

        // Successful reconnection
        context = { ...context, webSocket: createWebSocketState('OPEN') };
        state = determineLoadingState(context);
        expect(state).toBe(ChatLoadingState.READY);

        // Validate transition sequence
        expect(validateStateTransition(ChatLoadingState.CONNECTION_FAILED, ChatLoadingState.CONNECTING).isValid).toBe(true);
        expect(validateStateTransition(ChatLoadingState.CONNECTING, ChatLoadingState.READY).isValid).toBe(true);
      });
    });
  });

  describe('Context Assembly Function', () => {
    describe('createChatStateContext', () => {
      it('should create complete context with all parameters', () => {
        const messages = [{ id: '1', content: 'Test message' }];
        
        const context = createChatStateContext(
          'OPEN',              // wsStatus
          'thread-123',        // threadId
          false,               // isThreadLoading
          messages,            // messages
          true,                // isProcessing
          'run-456',           // runId
          'test_agent',        // agentName
          true                 // isInitialized
        );

        expect(context).toEqual({
          isInitialized: true,
          webSocket: {
            isConnected: true,
            isConnecting: false,
            isFailed: false,
            status: 'OPEN'
          },
          thread: {
            isLoading: false,
            hasActiveThread: true,
            hasMessages: true,
            threadId: 'thread-123'
          },
          processing: {
            isProcessing: true,
            currentRunId: 'run-456',
            agentName: 'test_agent'
          }
        });
      });

      it('should handle null/empty values correctly', () => {
        const context = createChatStateContext(
          'CONNECTING',
          null,
          false,
          [],
          false,
          null,
          null,
          false
        );

        expect(context).toEqual({
          isInitialized: false,
          webSocket: {
            isConnected: false,
            isConnecting: true,
            isFailed: false,
            status: 'CONNECTING'
          },
          thread: {
            isLoading: false,
            hasActiveThread: false,
            hasMessages: false,
            threadId: null
          },
          processing: {
            isProcessing: false,
            currentRunId: null,
            agentName: null
          }
        });
      });

      it('should handle partial agent information correctly', () => {
        const context = createChatStateContext(
          'OPEN',
          'thread-789',
          true,
          [{ id: '1', content: 'Message' }],
          true,
          'run-123',
          null, // No agent name
          true
        );

        expect(context.processing).toEqual({
          isProcessing: true,
          currentRunId: 'run-123',
          agentName: null
        });

        // Test that loading message handles missing agent name
        const result = createLoadingResult(ChatLoadingState.PROCESSING, context);
        expect(result.loadingMessage).toBe('Processing with agent...');
      });
    });
  });

  describe('Business Value Validation', () => {
    it('should prevent user confusion during initialization sequence', () => {
      // Test that loading states provide clear user feedback during critical moments
      const initializationSequence = [
        { 
          description: 'App starting',
          context: createChatStateContext('CONNECTING', null, false, [], false, null, null, false),
          expectedState: ChatLoadingState.INITIALIZING,
          shouldShowLoading: true,
          userExperience: 'Shows loading, prevents blank screen'
        },
        {
          description: 'WebSocket connecting',
          context: createChatStateContext('CONNECTING', null, false, [], false, null, null, true),
          expectedState: ChatLoadingState.CONNECTING,
          shouldShowLoading: true,
          userExperience: 'Shows connection progress'
        },
        {
          description: 'Connected, no thread',
          context: createChatStateContext('OPEN', null, false, [], false, null, null, true),
          expectedState: ChatLoadingState.READY,
          shouldShowLoading: false,
          userExperience: 'Shows thread selection UI'
        },
        {
          description: 'Loading thread',
          context: createChatStateContext('OPEN', 'thread-1', true, [], false, null, null, true),
          expectedState: ChatLoadingState.LOADING_THREAD,
          shouldShowLoading: true,
          userExperience: 'Shows thread loading progress'
        },
        {
          description: 'Thread ready, no messages',
          context: createChatStateContext('OPEN', 'thread-1', false, [], false, null, null, true),
          expectedState: ChatLoadingState.THREAD_READY,
          shouldShowLoading: false,
          userExperience: 'Shows example prompts to guide user'
        }
      ];

      initializationSequence.forEach(({ description, context, expectedState, shouldShowLoading, userExperience }) => {
        const state = determineLoadingState(context);
        const result = createLoadingResult(state, context);

        expect(state).toBe(expectedState);
        expect(result.shouldShowLoading).toBe(shouldShowLoading);
        
        // Verify user experience expectations
        if (expectedState === ChatLoadingState.READY) {
          expect(result.shouldShowEmptyState).toBe(true);
        }
        
        if (expectedState === ChatLoadingState.THREAD_READY && !context.thread.hasMessages) {
          expect(result.shouldShowExamplePrompts).toBe(true);
        }

        // Log for debugging
        console.log(`✓ ${description}: ${userExperience}`);
      });
    });

    it('should handle agent processing states to show progress', () => {
      // Verify that processing states provide appropriate feedback
      const processingScenarios = [
        {
          agentName: 'data_analyzer',
          expectedMessage: 'Processing with data_analyzer...'
        },
        {
          agentName: 'cost_optimizer',
          expectedMessage: 'Processing with cost_optimizer...'
        },
        {
          agentName: null,
          expectedMessage: 'Processing with agent...'
        },
        {
          agentName: '',
          expectedMessage: 'Processing with agent...'
        }
      ];

      processingScenarios.forEach(({ agentName, expectedMessage }) => {
        const context = createChatStateContext(
          'OPEN', 'thread-1', false, [{ id: '1', content: 'Request' }],
          true, 'run-123', agentName, true
        );

        const state = determineLoadingState(context);
        const result = createLoadingResult(state, context);

        expect(state).toBe(ChatLoadingState.PROCESSING);
        expect(result.loadingMessage).toBe(expectedMessage);
        expect(result.shouldShowLoading).toBe(false); // Processing shows progress differently
        expect(result.shouldShowExamplePrompts).toBe(false); // No prompts during processing
      });
    });

    it('should handle error states to prevent user abandonment', () => {
      const errorScenarios = [
        {
          description: 'Connection failed',
          context: createChatStateContext('CLOSED', null, false, [], false, null, null, true),
          expectedState: ChatLoadingState.CONNECTION_FAILED,
          expectedMessage: 'Connection failed. Retrying...',
          businessImpact: 'User sees retry message instead of blank screen'
        },
        {
          description: 'WebSocket error during processing',
          context: createChatStateContext('CLOSED', 'thread-1', false, [{ id: '1', content: 'Message' }], true, 'run-1', 'agent', true),
          expectedState: ChatLoadingState.CONNECTION_FAILED,
          expectedMessage: 'Connection failed. Retrying...',
          businessImpact: 'Processing interrupted gracefully with clear error message'
        }
      ];

      errorScenarios.forEach(({ description, context, expectedState, expectedMessage, businessImpact }) => {
        const state = determineLoadingState(context);
        const result = createLoadingResult(state, context);

        expect(state).toBe(expectedState);
        expect(result.loadingMessage).toBe(expectedMessage);
        expect(result.shouldShowLoading).toBe(false);
        expect(result.shouldShowEmptyState).toBe(false);
        expect(result.shouldShowExamplePrompts).toBe(false);

        console.log(`✓ ${description}: ${businessImpact}`);
      });
    });

    it('should optimize for chat engagement with example prompts', () => {
      // Test that example prompts are shown at the right times to encourage engagement
      const engagementScenarios = [
        {
          description: 'New thread, no messages',
          context: createChatStateContext('OPEN', 'thread-1', false, [], false, null, null, true),
          shouldShowPrompts: true,
          businessReason: 'Guide new users on what they can ask'
        },
        {
          description: 'Thread with messages',
          context: createChatStateContext('OPEN', 'thread-1', false, [{ id: '1', content: 'Previous message' }], false, null, null, true),
          shouldShowPrompts: false,
          businessReason: 'Let user see conversation history'
        },
        {
          description: 'Processing in progress',
          context: createChatStateContext('OPEN', 'thread-1', false, [], true, 'run-1', 'agent', true),
          shouldShowPrompts: false,
          businessReason: 'Focus on processing, no distractions'
        },
        {
          description: 'No thread selected',
          context: createChatStateContext('OPEN', null, false, [], false, null, null, true),
          shouldShowPrompts: false,
          businessReason: 'Show thread selection instead'
        }
      ];

      engagementScenarios.forEach(({ description, context, shouldShowPrompts, businessReason }) => {
        const state = determineLoadingState(context);
        const result = createLoadingResult(state, context);

        expect(result.shouldShowExamplePrompts).toBe(shouldShowPrompts);
        console.log(`✓ ${description}: ${businessReason} -> Show prompts: ${shouldShowPrompts}`);
      });
    });

    it('should maintain state consistency during rapid changes', () => {
      // Test that state machine handles rapid state changes without corruption
      let context = createChatStateContext('CONNECTING', null, false, [], false, null, null, false);
      
      const stateSequence = [];
      const maxIterations = 20;

      for (let i = 0; i < maxIterations; i++) {
        const currentState = determineLoadingState(context);
        const result = createLoadingResult(currentState, context);
        
        stateSequence.push({
          iteration: i,
          state: currentState,
          context: JSON.stringify(context),
          result
        });

        // Simulate rapid context changes
        if (i === 2) context = { ...context, isInitialized: true };
        if (i === 4) context = { ...context, webSocket: createWebSocketState('OPEN') };
        if (i === 6) context = { ...context, thread: createThreadState('thread-1', true, []) };
        if (i === 8) context = { ...context, thread: createThreadState('thread-1', false, []) };
        if (i === 10) context = { ...context, processing: createProcessingState(true, 'run-1', 'agent') };
        if (i === 12) context = { ...context, processing: createProcessingState(false, null, null) };
        if (i === 14) context = { ...context, thread: createThreadState('thread-1', false, [{ id: '1', content: 'Message' }]) };
      }

      // Verify no state corruption occurred
      const uniqueStates = new Set(stateSequence.map(s => s.state));
      const validStates = Object.values(ChatLoadingState);
      
      uniqueStates.forEach(state => {
        expect(validStates).toContain(state);
      });

      // Verify final state is reasonable
      const finalState = stateSequence[stateSequence.length - 1];
      expect(finalState.state).toBe(ChatLoadingState.THREAD_READY);
      expect(finalState.result.shouldShowLoading).toBe(false);
    });
  });
});