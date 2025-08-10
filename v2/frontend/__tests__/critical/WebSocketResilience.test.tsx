import { renderHook, act, waitFor } from '@testing-library/react';
import WS from 'jest-websocket-mock';
import { useWebSocket } from '../../hooks/useWebSocket';
import { WebSocketProvider } from '../../providers/WebSocketProvider';
import React from 'react';

describe('WebSocket Resilience Tests', () => {
  let server: WS;
  const wsUrl = 'ws://localhost:8000/ws/test-run-id';

  beforeEach(() => {
    server = new WS(wsUrl);
  });

  afterEach(() => {
    WS.clean();
  });

  describe('Connection Management', () => {
    it('should establish initial connection and handle handshake', async () => {
      const { result } = renderHook(() => useWebSocket(wsUrl), {
        wrapper: WebSocketProvider,
      });

      await server.connected;
      expect(result.current.readyState).toBe(WebSocket.CONNECTING);

      act(() => {
        server.send(JSON.stringify({ type: 'connection_established' }));
      });

      await waitFor(() => {
        expect(result.current.readyState).toBe(WebSocket.OPEN);
      });
    });

    it('should automatically reconnect on unexpected disconnection', async () => {
      const { result } = renderHook(() => useWebSocket(wsUrl), {
        wrapper: WebSocketProvider,
      });

      await server.connected;
      
      // Simulate unexpected disconnection
      server.close();
      
      await waitFor(() => {
        expect(result.current.readyState).toBe(WebSocket.CLOSED);
      });

      // Create new server instance for reconnection
      server = new WS(wsUrl);
      
      await waitFor(() => {
        expect(result.current.readyState).toBe(WebSocket.OPEN);
      }, { timeout: 5000 });
    });

    it('should implement exponential backoff for reconnection attempts', async () => {
      const reconnectAttempts: number[] = [];
      const { result } = renderHook(() => useWebSocket(wsUrl, {
        onReconnectAttempt: (attemptNumber) => {
          reconnectAttempts.push(attemptNumber);
        },
      }), {
        wrapper: WebSocketProvider,
      });

      await server.connected;
      
      // Force multiple disconnections
      for (let i = 0; i < 3; i++) {
        server.close();
        await waitFor(() => {
          expect(reconnectAttempts).toHaveLength(i + 1);
        });
        
        // Verify exponential backoff timing
        if (i > 0) {
          const expectedDelay = Math.min(1000 * Math.pow(2, i), 30000);
          expect(reconnectAttempts[i]).toBeGreaterThanOrEqual(expectedDelay);
        }
        
        server = new WS(wsUrl);
        await server.connected;
      }
    });

    it('should queue messages during disconnection and send on reconnect', async () => {
      const { result } = renderHook(() => useWebSocket(wsUrl), {
        wrapper: WebSocketProvider,
      });

      await server.connected;
      
      // Queue messages while disconnected
      server.close();
      
      const queuedMessages = [
        { type: 'message', content: 'test1' },
        { type: 'message', content: 'test2' },
        { type: 'message', content: 'test3' },
      ];
      
      act(() => {
        queuedMessages.forEach(msg => {
          result.current.sendMessage(msg);
        });
      });

      // Reconnect and verify queued messages are sent
      server = new WS(wsUrl);
      await server.connected;
      
      await waitFor(() => {
        expect(server.messages).toHaveLength(queuedMessages.length);
        queuedMessages.forEach((msg, index) => {
          expect(JSON.parse(server.messages[index] as string)).toEqual(msg);
        });
      });
    });

    it('should handle concurrent connections gracefully', async () => {
      const connections: any[] = [];
      
      // Create multiple connection attempts
      for (let i = 0; i < 3; i++) {
        const { result } = renderHook(() => useWebSocket(`${wsUrl}-${i}`), {
          wrapper: WebSocketProvider,
        });
        connections.push(result);
      }

      // Verify each connection is handled independently
      await waitFor(() => {
        connections.forEach((conn, index) => {
          expect(conn.current.connectionId).toBeDefined();
          expect(conn.current.connectionId).not.toBe(connections[(index + 1) % 3].current.connectionId);
        });
      });
    });
  });

  describe('Error Recovery', () => {
    it('should recover from malformed message errors', async () => {
      const onError = jest.fn();
      const { result } = renderHook(() => useWebSocket(wsUrl, { onError }), {
        wrapper: WebSocketProvider,
      });

      await server.connected;

      // Send malformed JSON
      act(() => {
        server.send('{ invalid json }');
      });

      await waitFor(() => {
        expect(onError).toHaveBeenCalledWith(
          expect.objectContaining({
            type: 'PARSE_ERROR',
            message: expect.stringContaining('JSON'),
          })
        );
      });

      // Verify connection remains open and functional
      expect(result.current.readyState).toBe(WebSocket.OPEN);
      
      // Send valid message to verify recovery
      act(() => {
        server.send(JSON.stringify({ type: 'test', data: 'valid' }));
      });

      await waitFor(() => {
        expect(result.current.lastMessage).toEqual({ type: 'test', data: 'valid' });
      });
    });

    it('should handle server-side errors gracefully', async () => {
      const { result } = renderHook(() => useWebSocket(wsUrl), {
        wrapper: WebSocketProvider,
      });

      await server.connected;

      // Simulate server error
      act(() => {
        server.send(JSON.stringify({
          type: 'error',
          code: 'INTERNAL_SERVER_ERROR',
          message: 'Database connection failed',
        }));
      });

      await waitFor(() => {
        expect(result.current.error).toEqual({
          type: 'error',
          code: 'INTERNAL_SERVER_ERROR',
          message: 'Database connection failed',
        });
      });

      // Verify connection strategy based on error type
      expect(result.current.reconnectStrategy).toBe('exponential');
    });
  });
});