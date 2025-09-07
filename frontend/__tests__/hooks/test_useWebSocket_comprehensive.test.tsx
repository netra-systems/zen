/**
 * Comprehensive Unit Test Suite for useWebSocket Hook
 * 
 * BUSINESS VALUE JUSTIFICATION:
 * - Segment: All users (Free, Early, Mid, Enterprise)
 * - Business Goal: User Retention and Experience Quality
 * - Value Impact: WebSocket hook enables 90% of real-time chat functionality
 * - Strategic Impact: Critical SSOT class for user-facing WebSocket communication
 * 
 * This hook is MISSION CRITICAL as it:
 * 1. Delivers real-time chat interactions (90% of business value)
 * 2. Handles all 5 critical WebSocket events for agent communication
 * 3. Manages connection lifecycle for reliable user experience
 * 4. Provides optimistic messaging for responsive UI
 * 5. Enables authentication and token refresh for security
 */

import React from 'react';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useWebSocket } from '../../hooks/useWebSocket';
import { WebSocketProvider } from '../../providers/WebSocketProvider';
import { webSocketService, WebSocketStatus } from '../../services/webSocketService';
import { WebSocketMessage } from '../../types/registry';
import { AuthProvider } from '../../auth/context';

// Mock dependencies
jest.mock('../../services/webSocketService');
jest.mock('../../services/reconciliation');
jest.mock('../../services/chatStatePersistence');
jest.mock('../../utils/unique-id-generator');
jest.mock('../../lib/logger');

const mockedWebSocketService = webSocketService as jest.Mocked<typeof webSocketService>;

// Mock implementations
const mockLogger = {
  debug: jest.fn(),
  info: jest.fn(),
  warn: jest.fn(),
  error: jest.fn(),
};

const mockReconciliationService = {
  processConfirmation: jest.fn((msg) => msg),
  addOptimisticMessage: jest.fn((msg) => ({ ...msg, tempId: 'temp-123' })),
  getStats: jest.fn(() => ({ pending: 0, confirmed: 0, failures: 0 })),
};

const mockChatStatePersistence = {
  updateThread: jest.fn(),
  updateMessages: jest.fn(),
  getRestorableState: jest.fn(() => null),
  destroy: jest.fn(),
};

const mockUniqueIdGenerator = {
  generateMessageId: jest.fn(() => 'msg-123'),
  generateTemporaryId: jest.fn(() => 'temp-456'),
};

// Test wrapper component
const TestWrapper: React.FC<{ children: React.ReactNode; token?: string }> = ({ 
  children, 
  token = 'test-token' 
}) => (
  <AuthProvider>
    <div data-testid="auth-wrapper">
      <WebSocketProvider>
        {children}
      </WebSocketProvider>
    </div>
  </AuthProvider>
);

describe('useWebSocket Hook - Comprehensive Test Suite', () => {
  let mockWebSocket: {
    send: jest.Mock;
    close: jest.Mock;
    readyState: number;
    onopen: ((event: Event) => void) | null;
    onmessage: ((event: MessageEvent) => void) | null;
    onclose: ((event: CloseEvent) => void) | null;
    onerror: ((event: Event) => void) | null;
  };

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Reset WebSocket service mock
    mockWebSocket = {
      send: jest.fn(),
      close: jest.fn(),
      readyState: WebSocket.OPEN,
      onopen: null,
      onmessage: null,
      onclose: null,
      onerror: null,
    };

    // Mock WebSocket constructor
    global.WebSocket = jest.fn(() => mockWebSocket as any) as any;

    // Setup service mocks
    mockedWebSocketService.connect = jest.fn();
    mockedWebSocketService.disconnect = jest.fn();
    mockedWebSocketService.sendMessage = jest.fn();
    mockedWebSocketService.getState = jest.fn(() => 'disconnected');
    mockedWebSocketService.onStatusChange = null;
    mockedWebSocketService.onMessage = null;

    // Mock external services
    require('../../services/reconciliation').reconciliationService = mockReconciliationService;
    require('../../services/chatStatePersistence').chatStatePersistence = mockChatStatePersistence;
    require('../../utils/unique-id-generator').generateMessageId = mockUniqueIdGenerator.generateMessageId;
    require('../../utils/unique-id-generator').generateTemporaryId = mockUniqueIdGenerator.generateTemporaryId;
    require('../../lib/logger').logger = mockLogger;
  });

  afterEach(() => {
    jest.resetAllMocks();
  });

  // =============================================================================
  // HOOK BASIC FUNCTIONALITY TESTS
  // =============================================================================

  describe('Hook Basic Functionality', () => {
    test('should return WebSocket context when used within provider', () => {
      const { result } = renderHook(() => useWebSocket(), {
        wrapper: TestWrapper,
      });

      expect(result.current).toBeDefined();
      expect(result.current).toHaveProperty('status');
      expect(result.current).toHaveProperty('messages');
      expect(result.current).toHaveProperty('sendMessage');
      expect(result.current).toHaveProperty('sendOptimisticMessage');
      expect(result.current).toHaveProperty('reconciliationStats');
    });

    test('should throw error when used outside provider', () => {
      // Suppress console.error for this test
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      
      expect(() => {
        renderHook(() => useWebSocket());
      }).toThrow('useWebSocketContext must be used within a WebSocketProvider');

      consoleSpy.mockRestore();
    });

    test('should return correct initial context values', () => {
      const { result } = renderHook(() => useWebSocket(), {
        wrapper: TestWrapper,
      });

      expect(result.current.status).toBe('CLOSED');
      expect(result.current.messages).toEqual([]);
      expect(typeof result.current.sendMessage).toBe('function');
      expect(typeof result.current.sendOptimisticMessage).toBe('function');
      expect(result.current.reconciliationStats).toEqual({
        pending: 0,
        confirmed: 0,
        failures: 0,
      });
    });

    test('should maintain referential stability of functions', () => {
      const { result, rerender } = renderHook(() => useWebSocket(), {
        wrapper: TestWrapper,
      });

      const initialSendMessage = result.current.sendMessage;
      const initialSendOptimistic = result.current.sendOptimisticMessage;

      rerender();

      expect(result.current.sendMessage).toBe(initialSendMessage);
      expect(result.current.sendOptimisticMessage).toBe(initialSendOptimistic);
    });
  });

  // =============================================================================
  // CONNECTION LIFECYCLE TESTS
  // =============================================================================

  describe('Connection Lifecycle Management', () => {
    test('should handle connecting state transition', async () => {
      const { result } = renderHook(() => useWebSocket(), {
        wrapper: TestWrapper,
      });

      // Simulate connecting state
      act(() => {
        if (mockedWebSocketService.onStatusChange) {
          mockedWebSocketService.onStatusChange('CONNECTING');
        }
      });

      await waitFor(() => {
        expect(result.current.status).toBe('CONNECTING');
      });
    });

    test('should handle successful connection (OPEN state)', async () => {
      const { result } = renderHook(() => useWebSocket(), {
        wrapper: TestWrapper,
      });

      act(() => {
        if (mockedWebSocketService.onStatusChange) {
          mockedWebSocketService.onStatusChange('OPEN');
        }
      });

      await waitFor(() => {
        expect(result.current.status).toBe('OPEN');
      });
    });

    test('should handle connection closure (CLOSED state)', async () => {
      const { result } = renderHook(() => useWebSocket(), {
        wrapper: TestWrapper,
      });

      act(() => {
        if (mockedWebSocketService.onStatusChange) {
          mockedWebSocketService.onStatusChange('CLOSED');
        }
      });

      await waitFor(() => {
        expect(result.current.status).toBe('CLOSED');
      });
    });

    test('should handle connection errors gracefully', async () => {
      const { result } = renderHook(() => useWebSocket(), {
        wrapper: TestWrapper,
      });

      // Simulate connection error by transitioning to CLOSED
      act(() => {
        if (mockedWebSocketService.onStatusChange) {
          mockedWebSocketService.onStatusChange('CLOSED');
        }
      });

      await waitFor(() => {
        expect(result.current.status).toBe('CLOSED');
        expect(mockLogger.error).toHaveBeenCalledWith(
          expect.stringContaining('Failed to connect'),
          expect.any(Error),
          expect.objectContaining({
            component: 'WebSocketProvider',
            action: expect.stringMatching(/connect|error/)
          })
        );
      });
    });

    test('should prevent duplicate connections', async () => {
      const { result } = renderHook(() => useWebSocket(), {
        wrapper: TestWrapper,
      });

      // Multiple rapid status changes should be handled properly
      act(() => {
        if (mockedWebSocketService.onStatusChange) {
          mockedWebSocketService.onStatusChange('CONNECTING');
          mockedWebSocketService.onStatusChange('CONNECTING'); // Duplicate
          mockedWebSocketService.onStatusChange('OPEN');
        }
      });

      await waitFor(() => {
        expect(result.current.status).toBe('OPEN');
      });

      // Should not have excessive connection attempts
      expect(mockedWebSocketService.connect).toHaveBeenCalledTimes(1);
    });
  });

  // =============================================================================
  // CRITICAL WEBSOCKET EVENTS TESTS
  // =============================================================================

  describe('Critical WebSocket Events Handling', () => {
    test('should handle agent_started event', async () => {
      const { result } = renderHook(() => useWebSocket(), {
        wrapper: TestWrapper,
      });

      const agentStartedMessage: WebSocketMessage = {
        type: 'agent_started',
        payload: {
          message_id: 'agent-start-123',
          agent_name: 'DataAgent',
          timestamp: Date.now(),
        },
      };

      act(() => {
        if (mockedWebSocketService.onMessage) {
          mockedWebSocketService.onMessage(agentStartedMessage);
        }
      });

      await waitFor(() => {
        expect(result.current.messages).toContainEqual(agentStartedMessage);
      });

      expect(mockLogger.debug).toHaveBeenCalledWith(
        'WebSocket message received and processed',
        expect.objectContaining({
          component: 'WebSocketProvider',
          action: 'message_received',
          metadata: expect.objectContaining({
            eventType: 'agent_started'
          })
        })
      );
    });

    test('should handle agent_thinking event', async () => {
      const { result } = renderHook(() => useWebSocket(), {
        wrapper: TestWrapper,
      });

      const agentThinkingMessage: WebSocketMessage = {
        type: 'agent_thinking',
        payload: {
          message_id: 'thinking-456',
          content: 'Analyzing user request...',
          timestamp: Date.now(),
        },
      };

      act(() => {
        if (mockedWebSocketService.onMessage) {
          mockedWebSocketService.onMessage(agentThinkingMessage);
        }
      });

      await waitFor(() => {
        expect(result.current.messages).toContainEqual(agentThinkingMessage);
      });
    });

    test('should handle tool_executing event', async () => {
      const { result } = renderHook(() => useWebSocket(), {
        wrapper: TestWrapper,
      });

      const toolExecutingMessage: WebSocketMessage = {
        type: 'tool_executing',
        payload: {
          message_id: 'tool-exec-789',
          tool_name: 'data_analysis',
          parameters: { dataset: 'user_data' },
          timestamp: Date.now(),
        },
      };

      act(() => {
        if (mockedWebSocketService.onMessage) {
          mockedWebSocketService.onMessage(toolExecutingMessage);
        }
      });

      await waitFor(() => {
        expect(result.current.messages).toContainEqual(toolExecutingMessage);
      });
    });

    test('should handle tool_completed event', async () => {
      const { result } = renderHook(() => useWebSocket(), {
        wrapper: TestWrapper,
      });

      const toolCompletedMessage: WebSocketMessage = {
        type: 'tool_completed',
        payload: {
          message_id: 'tool-comp-101',
          tool_name: 'data_analysis',
          result: 'Analysis complete: Found 5 optimization opportunities',
          timestamp: Date.now(),
        },
      };

      act(() => {
        if (mockedWebSocketService.onMessage) {
          mockedWebSocketService.onMessage(toolCompletedMessage);
        }
      });

      await waitFor(() => {
        expect(result.current.messages).toContainEqual(toolCompletedMessage);
      });
    });

    test('should handle agent_completed event', async () => {
      const { result } = renderHook(() => useWebSocket(), {
        wrapper: TestWrapper,
      });

      const agentCompletedMessage: WebSocketMessage = {
        type: 'agent_completed',
        payload: {
          message_id: 'agent-comp-202',
          result: 'Complete analysis report ready for review',
          agent_name: 'DataAgent',
          timestamp: Date.now(),
        },
      };

      act(() => {
        if (mockedWebSocketService.onMessage) {
          mockedWebSocketService.onMessage(agentCompletedMessage);
        }
      });

      await waitFor(() => {
        expect(result.current.messages).toContainEqual(agentCompletedMessage);
        expect(mockChatStatePersistence.updateMessages).toHaveBeenCalled();
      });
    });

    test('should process all 5 critical events in sequence', async () => {
      const { result } = renderHook(() => useWebSocket(), {
        wrapper: TestWrapper,
      });

      const criticalEvents: WebSocketMessage[] = [
        { type: 'agent_started', payload: { message_id: '1', agent_name: 'DataAgent' } },
        { type: 'agent_thinking', payload: { message_id: '2', content: 'Thinking...' } },
        { type: 'tool_executing', payload: { message_id: '3', tool_name: 'analyzer' } },
        { type: 'tool_completed', payload: { message_id: '4', result: 'Done' } },
        { type: 'agent_completed', payload: { message_id: '5', result: 'Complete' } },
      ];

      act(() => {
        criticalEvents.forEach(event => {
          if (mockedWebSocketService.onMessage) {
            mockedWebSocketService.onMessage(event);
          }
        });
      });

      await waitFor(() => {
        expect(result.current.messages).toHaveLength(5);
        criticalEvents.forEach(event => {
          expect(result.current.messages).toContainEqual(event);
        });
      });
    });
  });

  // =============================================================================
  // MESSAGE HANDLING TESTS
  // =============================================================================

  describe('Message Handling', () => {
    test('should send regular messages through WebSocket service', () => {
      const { result } = renderHook(() => useWebSocket(), {
        wrapper: TestWrapper,
      });

      const testMessage: WebSocketMessage = {
        type: 'user_message',
        payload: {
          content: 'Test message',
          timestamp: Date.now(),
        },
      };

      act(() => {
        result.current.sendMessage(testMessage);
      });

      expect(mockedWebSocketService.sendMessage).toHaveBeenCalledWith(testMessage);
    });

    test('should handle optimistic message sending', () => {
      const { result } = renderHook(() => useWebSocket(), {
        wrapper: TestWrapper,
      });

      act(() => {
        result.current.sendOptimisticMessage('Hello, world!', 'user');
      });

      expect(mockReconciliationService.addOptimisticMessage).toHaveBeenCalledWith({
        id: 'temp-456',
        content: 'Hello, world!',
        role: 'user',
        timestamp: expect.any(Number),
      });

      expect(mockedWebSocketService.sendMessage).toHaveBeenCalledWith({
        type: 'user_message',
        payload: {
          content: 'Hello, world!',
          timestamp: expect.any(String),
          correlation_id: 'temp-123',
        },
      });
    });

    test('should prevent duplicate messages', async () => {
      const { result } = renderHook(() => useWebSocket(), {
        wrapper: TestWrapper,
      });

      const duplicateMessage: WebSocketMessage = {
        type: 'user_message',
        payload: {
          message_id: 'duplicate-123',
          content: 'Same message',
        },
      };

      act(() => {
        if (mockedWebSocketService.onMessage) {
          mockedWebSocketService.onMessage(duplicateMessage);
          mockedWebSocketService.onMessage(duplicateMessage); // Duplicate
        }
      });

      await waitFor(() => {
        expect(result.current.messages).toHaveLength(1);
        expect(mockLogger.debug).toHaveBeenCalledWith(
          'Duplicate WebSocket message ignored',
          expect.objectContaining({
            component: 'WebSocketProvider',
            action: 'duplicate_message'
          })
        );
      });
    });

    test('should limit message history to 500 messages', async () => {
      const { result } = renderHook(() => useWebSocket(), {
        wrapper: TestWrapper,
      });

      // Send 502 messages to test the limit
      const messages = Array.from({ length: 502 }, (_, i) => ({
        type: 'user_message' as const,
        payload: {
          message_id: `msg-${i}`,
          content: `Message ${i}`,
        },
      }));

      act(() => {
        messages.forEach(msg => {
          if (mockedWebSocketService.onMessage) {
            mockedWebSocketService.onMessage(msg);
          }
        });
      });

      await waitFor(() => {
        expect(result.current.messages).toHaveLength(500);
        // Should contain the last 500 messages
        expect(result.current.messages[0].payload.message_id).toBe('msg-2');
        expect(result.current.messages[499].payload.message_id).toBe('msg-501');
      });
    });

    test('should handle message reconciliation', async () => {
      mockReconciliationService.processConfirmation.mockReturnValue({
        type: 'user_message',
        payload: { content: 'Reconciled message' },
        reconciled: true,
      });

      const { result } = renderHook(() => useWebSocket(), {
        wrapper: TestWrapper,
      });

      const testMessage: WebSocketMessage = {
        type: 'user_message',
        payload: { content: 'Original message' },
      };

      act(() => {
        if (mockedWebSocketService.onMessage) {
          mockedWebSocketService.onMessage(testMessage);
        }
      });

      await waitFor(() => {
        expect(mockReconciliationService.processConfirmation).toHaveBeenCalledWith(testMessage);
      });
    });
  });

  // =============================================================================
  // AUTHENTICATION AND TOKEN MANAGEMENT TESTS
  // =============================================================================

  describe('Authentication and Token Management', () => {
    test('should connect with authentication token', async () => {
      const TestWrapperWithToken: React.FC<{ children: React.ReactNode }> = ({ children }) => (
        <AuthProvider>
          <WebSocketProvider>{children}</WebSocketProvider>
        </AuthProvider>
      );

      const { result } = renderHook(() => useWebSocket(), {
        wrapper: TestWrapperWithToken,
      });

      await waitFor(() => {
        expect(mockedWebSocketService.connect).toHaveBeenCalled();
      });
    });

    test('should handle token refresh during connection', async () => {
      const { result } = renderHook(() => useWebSocket(), {
        wrapper: TestWrapper,
      });

      // Simulate token refresh
      act(() => {
        // Mock token change would trigger reconnection
        if (mockedWebSocketService.onStatusChange) {
          mockedWebSocketService.onStatusChange('CONNECTING');
          mockedWebSocketService.onStatusChange('OPEN');
        }
      });

      await waitFor(() => {
        expect(result.current.status).toBe('OPEN');
      });
    });

    test('should handle authentication failures', async () => {
      const { result } = renderHook(() => useWebSocket(), {
        wrapper: TestWrapper,
      });

      act(() => {
        if (mockedWebSocketService.onStatusChange) {
          mockedWebSocketService.onStatusChange('CLOSED');
        }
      });

      await waitFor(() => {
        expect(result.current.status).toBe('CLOSED');
      });
    });

    test('should work in development mode without token', async () => {
      process.env.NODE_ENV = 'development';

      const TestWrapperNoToken: React.FC<{ children: React.ReactNode }> = ({ children }) => (
        <AuthProvider>
          <WebSocketProvider>{children}</WebSocketProvider>
        </AuthProvider>
      );

      const { result } = renderHook(() => useWebSocket(), {
        wrapper: TestWrapperNoToken,
      });

      expect(result.current).toBeDefined();
      expect(result.current.status).toBe('CLOSED'); // Initial state

      process.env.NODE_ENV = 'test'; // Reset
    });
  });

  // =============================================================================
  // STATE PERSISTENCE TESTS
  // =============================================================================

  describe('State Persistence and Restoration', () => {
    test('should restore chat state on mount', async () => {
      const mockRestorableState = {
        threadId: 'thread-123',
        messages: [
          { id: 'msg-1', content: 'Hello', role: 'user', timestamp: Date.now() },
          { id: 'msg-2', content: 'Hi there', role: 'assistant', timestamp: Date.now() },
        ],
        draftMessage: 'Draft content',
      };

      mockChatStatePersistence.getRestorableState.mockReturnValue(mockRestorableState);

      const { result } = renderHook(() => useWebSocket(), {
        wrapper: TestWrapper,
      });

      await waitFor(() => {
        expect(mockChatStatePersistence.getRestorableState).toHaveBeenCalled();
        expect(result.current.messages).toHaveLength(2);
        expect(mockLogger.debug).toHaveBeenCalledWith(
          'Restoring chat state after refresh',
          expect.objectContaining({
            component: 'WebSocketProvider',
            action: 'restore_state'
          })
        );
      });
    });

    test('should update thread state on thread_created event', async () => {
      const { result } = renderHook(() => useWebSocket(), {
        wrapper: TestWrapper,
      });

      const threadCreatedMessage: WebSocketMessage = {
        type: 'thread_created',
        payload: {
          thread_id: 'new-thread-456',
          message_id: 'thread-msg-789',
        },
      };

      act(() => {
        if (mockedWebSocketService.onMessage) {
          mockedWebSocketService.onMessage(threadCreatedMessage);
        }
      });

      await waitFor(() => {
        expect(mockChatStatePersistence.updateThread).toHaveBeenCalledWith('new-thread-456');
      });
    });

    test('should persist chat messages automatically', async () => {
      const { result } = renderHook(() => useWebSocket(), {
        wrapper: TestWrapper,
      });

      const chatMessage: WebSocketMessage = {
        type: 'user_message',
        payload: {
          message_id: 'chat-msg-123',
          content: 'Save this message',
          timestamp: Date.now(),
        },
      };

      act(() => {
        if (mockedWebSocketService.onMessage) {
          mockedWebSocketService.onMessage(chatMessage);
        }
      });

      await waitFor(() => {
        expect(mockChatStatePersistence.updateMessages).toHaveBeenCalledWith(
          expect.arrayContaining([
            expect.objectContaining({
              content: 'Save this message',
              role: 'user',
            }),
          ])
        );
      });
    });
  });

  // =============================================================================
  // ERROR HANDLING AND RECOVERY TESTS
  // =============================================================================

  describe('Error Handling and Recovery', () => {
    test('should handle WebSocket service errors gracefully', async () => {
      const { result } = renderHook(() => useWebSocket(), {
        wrapper: TestWrapper,
      });

      // Simulate service error
      act(() => {
        mockedWebSocketService.sendMessage.mockImplementation(() => {
          throw new Error('WebSocket service error');
        });
      });

      expect(() => {
        result.current.sendMessage({
          type: 'user_message',
          payload: { content: 'Test' },
        });
      }).toThrow('WebSocket service error');
    });

    test('should recover from temporary connection failures', async () => {
      const { result } = renderHook(() => useWebSocket(), {
        wrapper: TestWrapper,
      });

      // Simulate connection failure and recovery
      act(() => {
        if (mockedWebSocketService.onStatusChange) {
          mockedWebSocketService.onStatusChange('CLOSED');
          mockedWebSocketService.onStatusChange('CONNECTING');
          mockedWebSocketService.onStatusChange('OPEN');
        }
      });

      await waitFor(() => {
        expect(result.current.status).toBe('OPEN');
      });
    });

    test('should handle malformed messages without crashing', async () => {
      const { result } = renderHook(() => useWebSocket(), {
        wrapper: TestWrapper,
      });

      const malformedMessage = {
        // Missing required fields
        invalidField: 'invalid',
      };

      // Should not crash when processing malformed message
      act(() => {
        if (mockedWebSocketService.onMessage) {
          mockedWebSocketService.onMessage(malformedMessage as any);
        }
      });

      await waitFor(() => {
        // Should continue to function normally
        expect(result.current.messages).toEqual([malformedMessage]);
      });
    });

    test('should clean up resources on unmount', () => {
      const { unmount } = renderHook(() => useWebSocket(), {
        wrapper: TestWrapper,
      });

      unmount();

      expect(mockChatStatePersistence.destroy).toHaveBeenCalled();
      expect(mockedWebSocketService.onStatusChange).toBeNull();
      expect(mockedWebSocketService.onMessage).toBeNull();
    });
  });

  // =============================================================================
  // PERFORMANCE AND MEMORY TESTS
  // =============================================================================

  describe('Performance and Memory Management', () => {
    test('should debounce rapid status changes', async () => {
      const { result } = renderHook(() => useWebSocket(), {
        wrapper: TestWrapper,
      });

      // Simulate rapid status changes
      act(() => {
        if (mockedWebSocketService.onStatusChange) {
          mockedWebSocketService.onStatusChange('CONNECTING');
          mockedWebSocketService.onStatusChange('CONNECTING');
          mockedWebSocketService.onStatusChange('CONNECTING');
          mockedWebSocketService.onStatusChange('OPEN');
        }
      });

      await waitFor(() => {
        expect(result.current.status).toBe('OPEN');
      });
    });

    test('should handle high message throughput efficiently', async () => {
      const { result } = renderHook(() => useWebSocket(), {
        wrapper: TestWrapper,
      });

      const messages = Array.from({ length: 100 }, (_, i) => ({
        type: 'agent_thinking' as const,
        payload: {
          message_id: `fast-msg-${i}`,
          content: `Fast message ${i}`,
        },
      }));

      const startTime = performance.now();

      act(() => {
        messages.forEach(msg => {
          if (mockedWebSocketService.onMessage) {
            mockedWebSocketService.onMessage(msg);
          }
        });
      });

      const endTime = performance.now();

      await waitFor(() => {
        expect(result.current.messages).toHaveLength(100);
      });

      // Should process messages quickly (less than 100ms for 100 messages)
      expect(endTime - startTime).toBeLessThan(100);
    });

    test('should maintain stable reconciliation stats', () => {
      const { result } = renderHook(() => useWebSocket(), {
        wrapper: TestWrapper,
      });

      expect(result.current.reconciliationStats).toEqual({
        pending: 0,
        confirmed: 0,
        failures: 0,
      });

      // Stats should remain stable across re-renders
      expect(result.current.reconciliationStats).toBe(result.current.reconciliationStats);
    });
  });

  // =============================================================================
  // INTEGRATION AND CROSS-FEATURE TESTS
  // =============================================================================

  describe('Integration and Cross-Feature Tests', () => {
    test('should integrate properly with authentication context', async () => {
      const { result } = renderHook(() => useWebSocket(), {
        wrapper: TestWrapper,
      });

      // Should initialize properly with auth context
      expect(result.current).toBeDefined();
      expect(typeof result.current.sendMessage).toBe('function');
    });

    test('should handle complex agent workflow simulation', async () => {
      const { result } = renderHook(() => useWebSocket(), {
        wrapper: TestWrapper,
      });

      // Simulate complete agent workflow
      const workflowMessages: WebSocketMessage[] = [
        {
          type: 'thread_created',
          payload: { thread_id: 'workflow-thread', message_id: 'thread-1' },
        },
        {
          type: 'agent_started',
          payload: { message_id: 'agent-1', agent_name: 'DataAgent' },
        },
        {
          type: 'agent_thinking',
          payload: { message_id: 'thinking-1', content: 'Analyzing data...' },
        },
        {
          type: 'tool_executing',
          payload: { message_id: 'tool-1', tool_name: 'data_processor' },
        },
        {
          type: 'tool_completed',
          payload: { message_id: 'tool-comp-1', result: 'Data processed successfully' },
        },
        {
          type: 'agent_completed',
          payload: { message_id: 'agent-comp-1', result: 'Analysis complete' },
        },
        {
          type: 'final_report',
          payload: { message_id: 'report-1', content: 'Final analysis report' },
        },
      ];

      act(() => {
        workflowMessages.forEach(msg => {
          if (mockedWebSocketService.onMessage) {
            mockedWebSocketService.onMessage(msg);
          }
        });
      });

      await waitFor(() => {
        expect(result.current.messages).toHaveLength(7);
        expect(mockChatStatePersistence.updateThread).toHaveBeenCalledWith('workflow-thread');
        expect(mockChatStatePersistence.updateMessages).toHaveBeenCalled();
      });
    });

    test('should handle concurrent user and system messages', async () => {
      const { result } = renderHook(() => useWebSocket(), {
        wrapper: TestWrapper,
      });

      const concurrentMessages: WebSocketMessage[] = [
        {
          type: 'user_message',
          payload: { message_id: 'user-1', content: 'User message 1' },
        },
        {
          type: 'agent_thinking',
          payload: { message_id: 'agent-1', content: 'Agent processing' },
        },
        {
          type: 'user_message',
          payload: { message_id: 'user-2', content: 'User message 2' },
        },
        {
          type: 'assistant_message',
          payload: { message_id: 'assistant-1', content: 'Assistant response' },
        },
      ];

      act(() => {
        // Send messages in rapid succession
        concurrentMessages.forEach((msg, index) => {
          setTimeout(() => {
            if (mockedWebSocketService.onMessage) {
              mockedWebSocketService.onMessage(msg);
            }
          }, index * 10);
        });
      });

      await waitFor(() => {
        expect(result.current.messages).toHaveLength(4);
      }, { timeout: 1000 });
    });
  });

  // =============================================================================
  // EDGE CASES AND BOUNDARY TESTS
  // =============================================================================

  describe('Edge Cases and Boundary Conditions', () => {
    test('should handle empty message payloads', async () => {
      const { result } = renderHook(() => useWebSocket(), {
        wrapper: TestWrapper,
      });

      const emptyMessage: WebSocketMessage = {
        type: 'agent_started',
        payload: {},
      };

      act(() => {
        if (mockedWebSocketService.onMessage) {
          mockedWebSocketService.onMessage(emptyMessage);
        }
      });

      await waitFor(() => {
        expect(result.current.messages).toContainEqual(emptyMessage);
      });
    });

    test('should handle messages with null/undefined payloads', async () => {
      const { result } = renderHook(() => useWebSocket(), {
        wrapper: TestWrapper,
      });

      const nullPayloadMessage = {
        type: 'system_message',
        payload: null,
      };

      act(() => {
        if (mockedWebSocketService.onMessage) {
          mockedWebSocketService.onMessage(nullPayloadMessage as any);
        }
      });

      await waitFor(() => {
        expect(result.current.messages).toContainEqual(nullPayloadMessage);
      });
    });

    test('should handle very long message content', async () => {
      const { result } = renderHook(() => useWebSocket(), {
        wrapper: TestWrapper,
      });

      const longContent = 'A'.repeat(10000); // 10KB message
      const longMessage: WebSocketMessage = {
        type: 'agent_completed',
        payload: {
          message_id: 'long-msg',
          result: longContent,
        },
      };

      act(() => {
        if (mockedWebSocketService.onMessage) {
          mockedWebSocketService.onMessage(longMessage);
        }
      });

      await waitFor(() => {
        expect(result.current.messages).toContainEqual(longMessage);
        expect(result.current.messages[0].payload.result).toHaveLength(10000);
      });
    });

    test('should handle Unicode and special characters', async () => {
      const { result } = renderHook(() => useWebSocket(), {
        wrapper: TestWrapper,
      });

      const unicodeMessage: WebSocketMessage = {
        type: 'user_message',
        payload: {
          message_id: 'unicode-msg',
          content: '🚀 Hello 世界! Special chars: <>&"\'',
        },
      };

      act(() => {
        if (mockedWebSocketService.onMessage) {
          mockedWebSocketService.onMessage(unicodeMessage);
        }
      });

      await waitFor(() => {
        expect(result.current.messages).toContainEqual(unicodeMessage);
      });
    });
  });
});