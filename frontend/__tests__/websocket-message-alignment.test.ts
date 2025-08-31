/**
 * WebSocket Message Type Alignment Tests
 * 
 * This test suite verifies that the frontend correctly handles all message types
 * that the backend can send, ensuring proper alignment between backend and frontend.
 */

import { webSocketService } from '../services/webSocketService';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

describe('WebSocket Message Type Alignment', () => {
  setupAntiHang();
    jest.setTimeout(10000);
  let mockWebSocket: any;
  let onMessageCallback: jest.Mock;
  let onErrorCallback: jest.Mock;

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Create mock WebSocket
    mockWebSocket = {
      readyState: WebSocket.OPEN,
      send: jest.fn(),
      close: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
    };
    
    // Mock WebSocket constructor
    global.WebSocket = jest.fn().mockImplementation(() => mockWebSocket) as any;
    
    onMessageCallback = jest.fn();
    onErrorCallback = jest.fn();
  });

  afterEach(() => {
    webSocketService.disconnect();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
      cleanupAntiHang();
  });

  describe('Backend Message Types from MessageType Enum', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    // All message types from backend's MessageType enum
    const backendMessageTypes = [
      // Connection lifecycle
      { type: 'connect', data: { status: 'connected' } },
      { type: 'disconnect', data: { reason: 'server_shutdown' } },
      { type: 'heartbeat', data: { timestamp: Date.now() } },
      { type: 'heartbeat_ack', data: { timestamp: Date.now() } },
      { type: 'ping', timestamp: Date.now() },
      { type: 'pong', timestamp: Date.now(), original_timestamp: Date.now() - 100 },
      
      // User messages
      { type: 'user_message', data: { message: 'test' } },
      { type: 'system_message', data: { event: 'connection_established', connection_id: 'test123' } },
      { type: 'error_message', data: { error: 'test error', code: 'ERROR_001' } },
      
      // Agent communication
      { type: 'start_agent', data: { agent: 'test_agent' } },
      { type: 'agent_response', data: { response: 'test response' } },
      { type: 'agent_progress', data: { progress: 50 } },
      { type: 'agent_error', data: { error: 'agent error' } },
      
      // Thread/conversation
      { type: 'thread_update', data: { thread_id: 'thread123' } },
      { type: 'thread_message', data: { message: 'thread message' } },
      
      // Broadcasting
      { type: 'broadcast', data: { message: 'broadcast message' } },
      { type: 'room_message', data: { room: 'test_room', message: 'room message' } },
      
      // JSON-RPC (MCP compatibility)
      { type: 'jsonrpc_request', jsonrpc: '2.0', method: 'test', id: 1 },
      { type: 'jsonrpc_response', jsonrpc: '2.0', result: {}, id: 1 },
      { type: 'jsonrpc_notification', jsonrpc: '2.0', method: 'notify' },
    ];

    test.each(backendMessageTypes)('should handle backend message type: $type', async (message) => {
      // Connect to WebSocket
      await webSocketService.connect('ws://localhost:8000/ws', {
        onMessage: onMessageCallback,
        onError: onErrorCallback,
      });

      // Simulate receiving message from backend
      const messageEvent = new MessageEvent('message', {
        data: JSON.stringify(message)
      });
      
      // Get the onmessage handler that was set
      const onmessageHandler = (mockWebSocket as any).onmessage;
      expect(onmessageHandler).toBeDefined();
      
      // Call the handler
      onmessageHandler(messageEvent);
      
      // The message should be processed without errors
      if (onErrorCallback.mock.calls.length > 0) {
        const errors = onErrorCallback.mock.calls.map(call => call[0]);
        const parseErrors = errors.filter(e => e.type === 'parse');
        
        // If there was a parse error, this test should fail
        if (parseErrors.length > 0) {
          expect(parseErrors).toHaveLength(0);
        }
      }
    });
  });

  describe('Frontend-Specific Message Types', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    // Message types that frontend expects but might not be in backend enum
    const frontendSpecificTypes = [
      // Agent messages (some overlap but with different format expectations)
      { type: 'agent_started', payload: { agent_name: 'test' } },
      { type: 'tool_executing', payload: { tool: 'test_tool' } },
      { type: 'agent_thinking', payload: { status: 'thinking' } },
      { type: 'partial_result', payload: { result: 'partial' } },
      { type: 'agent_completed', payload: { result: 'completed' } },
      
      // Thread messages
      { type: 'thread_created', payload: { thread_id: 'new_thread' } },
      { type: 'thread_loading', payload: { thread_id: 'loading_thread' } },
      { type: 'thread_loaded', payload: { thread_id: 'loaded_thread' } },
      { type: 'thread_renamed', payload: { thread_id: 'renamed_thread', new_name: 'New Name' } },
      
      // Report messages
      { type: 'final_report', payload: { report: 'final report data' } },
      { type: 'error', payload: { error: 'error message' } },
      { type: 'step_created', payload: { step: 'new step' } },
      
      // System messages
      { type: 'auth', token: 'test_token' },
      { type: 'server_shutdown', drain_timeout: 5000, message: 'Server shutting down' },
    ];

    test.each(frontendSpecificTypes)('should handle frontend-expected message type: $type', async (message) => {
      // Connect to WebSocket
      await webSocketService.connect('ws://localhost:8000/ws', {
        onMessage: onMessageCallback,
        onError: onErrorCallback,
      });

      // Simulate receiving message
      const messageEvent = new MessageEvent('message', {
        data: JSON.stringify(message)
      });
      
      const onmessageHandler = (mockWebSocket as any).onmessage;
      onmessageHandler(messageEvent);
      
      // Check for parse errors
      if (onErrorCallback.mock.calls.length > 0) {
        const errors = onErrorCallback.mock.calls.map(call => call[0]);
        const parseErrors = errors.filter(e => e.type === 'parse');
        expect(parseErrors).toHaveLength(0);
      }
    });
  });

  describe('Message Field Alignment', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    test('should handle messages with "data" field instead of "payload"', () => {
      const messageWithData = {
        type: 'system_message',
        data: { event: 'test_event' },
        timestamp: Date.now()
      };

      // Connect to WebSocket
      webSocketService.connect('ws://localhost:8000/ws', {
        onMessage: onMessageCallback,
        onError: onErrorCallback,
      });

      const messageEvent = new MessageEvent('message', {
        data: JSON.stringify(messageWithData)
      });
      
      const onmessageHandler = (mockWebSocket as any).onmessage;
      onmessageHandler(messageEvent);
      
      // Should convert data to payload for compatibility
      expect(onMessageCallback).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'system_message',
          payload: expect.objectContaining({ event: 'test_event' })
        })
      );
    });

    test('should handle messages with both "data" and "payload" fields', () => {
      const messageWithBoth = {
        type: 'agent_response',
        data: { serverData: 'from backend' },
        payload: { clientData: 'expected by frontend' },
        timestamp: Date.now()
      };

      webSocketService.connect('ws://localhost:8000/ws', {
        onMessage: onMessageCallback,
        onError: onErrorCallback,
      });

      const messageEvent = new MessageEvent('message', {
        data: JSON.stringify(messageWithBoth)
      });
      
      const onmessageHandler = (mockWebSocket as any).onmessage;
      onmessageHandler(messageEvent);
      
      // Should preserve payload when both exist
      expect(onMessageCallback).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'agent_response',
          payload: expect.objectContaining({ clientData: 'expected by frontend' })
        })
      );
    });
  });

  describe('Error Handling for Unknown Message Types', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    test('should handle completely unknown message types gracefully', () => {
      const unknownMessage = {
        type: 'completely_unknown_type',
        data: { test: 'data' }
      };

      webSocketService.connect('ws://localhost:8000/ws', {
        onMessage: onMessageCallback,
        onError: onErrorCallback,
      });

      const messageEvent = new MessageEvent('message', {
        data: JSON.stringify(unknownMessage)
      });
      
      const onmessageHandler = (mockWebSocket as any).onmessage;
      onmessageHandler(messageEvent);
      
      // Should still process the message (with default handling)
      expect(onMessageCallback).toHaveBeenCalled();
      // Should not trigger parse error
      const parseErrors = onErrorCallback.mock.calls.filter(call => call[0].type === 'parse');
      expect(parseErrors).toHaveLength(0);
    });

    test('should reject messages without type field', () => {
      const messageWithoutType = {
        data: { test: 'data' },
        timestamp: Date.now()
      };

      webSocketService.connect('ws://localhost:8000/ws', {
        onMessage: onMessageCallback,
        onError: onErrorCallback,
      });

      const messageEvent = new MessageEvent('message', {
        data: JSON.stringify(messageWithoutType)
      });
      
      const onmessageHandler = (mockWebSocket as any).onmessage;
      onmessageHandler(messageEvent);
      
      // Should trigger an error for missing type
      expect(onErrorCallback).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'parse',
          message: expect.stringContaining('Invalid message structure')
        })
      );
    });
  });

  describe('Large Message Handling', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    test('should handle large messages with chunks', () => {
      const largeMessage = {
        type: 'agent_response',
        chunks: [
          { index: 0, total: 2, data: 'part1' },
          { index: 1, total: 2, data: 'part2' }
        ],
        message_id: 'large_msg_123'
      };

      webSocketService.connect('ws://localhost:8000/ws', {
        onMessage: onMessageCallback,
        onError: onErrorCallback,
      });

      const messageEvent = new MessageEvent('message', {
        data: JSON.stringify(largeMessage)
      });
      
      const onmessageHandler = (mockWebSocket as any).onmessage;
      onmessageHandler(messageEvent);
      
      // Should handle without parse errors
      const parseErrors = onErrorCallback.mock.calls.filter(call => call[0]?.type === 'parse');
      expect(parseErrors).toHaveLength(0);
    });
  });
});