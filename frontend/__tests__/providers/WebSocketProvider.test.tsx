import React from 'react';
import { render, screen, act, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { WebSocketProvider, useWebSocket } from '@/providers/WebSocketProvider';
import { useAuth } from '@/hooks/useAuth';
import webSocketService from '@/services/webSocketService';
import { reconciliationService } from '@/services/reconciliationService';

// Mock external dependencies
jest.mock('@/hooks/useAuth');
jest.mock('@/services/webSocketService');
jest.mock('@/services/reconciliationService');
jest.mock('@/utils/debug-logger', () => ({
  debugLogger: {
    debug: jest.fn(),
    error: jest.fn(),
    warn: jest.fn()
  }
}));

// Test component to access WebSocket context
const TestComponent = () => {
  const { messages, status, sendMessage } = useWebSocket();
  return (
    <div>
      <div data-testid="status">{status}</div>
      <div data-testid="message-count">{messages.length}</div>
      {messages.map((msg, idx) => (
        <div key={idx} data-testid={`message-${idx}`}>
          {JSON.stringify(msg)}
        </div>
      ))}
      <button onClick={() => sendMessage({ type: 'test' })}>Send</button>
    </div>
  );
};

describe('WebSocketProvider', () => {
  let mockAuth: jest.Mocked<ReturnType<typeof useAuth>>;
  let mockWebSocketService: jest.Mocked<typeof webSocketService>;
  let mockReconciliationService: jest.Mocked<typeof reconciliationService>;

  beforeEach(() => {
    jest.useFakeTimers();
    
    // Setup auth mock
    mockAuth = {
      token: 'test-token',
      isAuthenticated: true,
      loading: false,
      user: null,
      error: null,
      login: jest.fn(),
      logout: jest.fn(),
      refreshToken: jest.fn()
    };
    (useAuth as jest.Mock).mockReturnValue(mockAuth);

    // Setup WebSocket service mock
    mockWebSocketService = {
      connect: jest.fn(),
      disconnect: jest.fn(),
      send: jest.fn(),
      onMessage: null,
      onStatusChange: null,
      isConnected: jest.fn().mockReturnValue(false),
      status: 'CLOSED' as any,
      lastHeartbeat: null
    };
    (webSocketService as any) = mockWebSocketService;

    // Setup reconciliation service mock
    mockReconciliationService = {
      processMessage: jest.fn((msg) => msg),
      getUnreconciledMessages: jest.fn().mockReturnValue([]),
      clearUnreconciledMessages: jest.fn()
    };
    (reconciliationService as any) = mockReconciliationService;
  });

  afterEach(() => {
    jest.clearAllMocks();
    jest.useRealTimers();
  });

  describe('Heartbeat Configuration', () => {
    it('configures WebSocket with 15 second heartbeat interval', async () => {
      render(
        <WebSocketProvider>
          <TestComponent />
        </WebSocketProvider>
      );

      // Wait for connection with delay
      await act(async () => {
        jest.advanceTimersByTime(100); // OAuth callback delay
      });

      await waitFor(() => {
        expect(mockWebSocketService.connect).toHaveBeenCalledWith(
          expect.objectContaining({
            heartbeatInterval: 15000 // 15 seconds
          })
        );
      });
    });

    it('maintains heartbeat interval when token updates', async () => {
      const { rerender } = render(
        <WebSocketProvider>
          <TestComponent />
        </WebSocketProvider>
      );

      await act(async () => {
        jest.advanceTimersByTime(100);
      });

      // Update token
      mockAuth.token = 'new-token';
      (useAuth as jest.Mock).mockReturnValue(mockAuth);
      
      rerender(
        <WebSocketProvider>
          <TestComponent />
        </WebSocketProvider>
      );

      await waitFor(() => {
        // Should still use 15 second heartbeat
        const calls = mockWebSocketService.connect.mock.calls;
        expect(calls[calls.length - 1][0]).toMatchObject({
          heartbeatInterval: 15000
        });
      });
    });
  });

  describe('Message Buffer Limit', () => {
    it('limits message buffer to 500 messages', async () => {
      render(
        <WebSocketProvider>
          <TestComponent />
        </WebSocketProvider>
      );

      // Simulate connection
      await act(async () => {
        jest.advanceTimersByTime(100);
        if (mockWebSocketService.onStatusChange) {
          mockWebSocketService.onStatusChange('OPEN' as any);
        }
      });

      // Send 502 messages
      await act(async () => {
        for (let i = 0; i < 502; i++) {
          if (mockWebSocketService.onMessage) {
            mockWebSocketService.onMessage({
              type: 'message',
              payload: { 
                message_id: `msg-${i}`,
                content: `Message ${i}`
              }
            });
          }
        }
      });

      // Should have exactly 500 messages (oldest 2 removed)
      expect(screen.getByTestId('message-count')).toHaveTextContent('500');
      
      // First message should be msg-2 (0 and 1 removed)
      const firstMessage = screen.getByTestId('message-0');
      expect(firstMessage.textContent).toContain('msg-2');
      
      // Last message should be msg-501
      const lastMessage = screen.getByTestId('message-499');
      expect(lastMessage.textContent).toContain('msg-501');
    });

    it('does not limit buffer when under 500 messages', async () => {
      render(
        <WebSocketProvider>
          <TestComponent />
        </WebSocketProvider>
      );

      await act(async () => {
        jest.advanceTimersByTime(100);
        if (mockWebSocketService.onStatusChange) {
          mockWebSocketService.onStatusChange('OPEN' as any);
        }
      });

      // Send 100 messages
      await act(async () => {
        for (let i = 0; i < 100; i++) {
          if (mockWebSocketService.onMessage) {
            mockWebSocketService.onMessage({
              type: 'message',
              payload: { 
                message_id: `msg-${i}`,
                content: `Message ${i}`
              }
            });
          }
        }
      });

      // Should have all 100 messages
      expect(screen.getByTestId('message-count')).toHaveTextContent('100');
    });

    it('maintains message order during buffer overflow', async () => {
      render(
        <WebSocketProvider>
          <TestComponent />
        </WebSocketProvider>
      );

      await act(async () => {
        jest.advanceTimersByTime(100);
        if (mockWebSocketService.onStatusChange) {
          mockWebSocketService.onStatusChange('OPEN' as any);
        }
      });

      // Send messages with identifiable order
      const testMessages = Array.from({ length: 510 }, (_, i) => ({
        type: 'test',
        payload: { 
          message_id: `id-${i}`,
          order: i 
        }
      }));

      await act(async () => {
        for (const msg of testMessages) {
          if (mockWebSocketService.onMessage) {
            mockWebSocketService.onMessage(msg);
          }
        }
      });

      // Should have last 500 messages (10-509)
      expect(screen.getByTestId('message-count')).toHaveTextContent('500');
      
      // Verify order is maintained
      const firstMessage = JSON.parse(screen.getByTestId('message-0').textContent!);
      expect(firstMessage.payload.order).toBe(10);
      
      const lastMessage = JSON.parse(screen.getByTestId('message-499').textContent!);
      expect(lastMessage.payload.order).toBe(509);
    });
  });

  describe('Connection Lifecycle', () => {
    it('establishes connection with token after delay', async () => {
      render(
        <WebSocketProvider>
          <TestComponent />
        </WebSocketProvider>
      );

      // Initially not connected
      expect(mockWebSocketService.connect).not.toHaveBeenCalled();

      // Advance past OAuth callback delay
      await act(async () => {
        jest.advanceTimersByTime(100);
      });

      await waitFor(() => {
        expect(mockWebSocketService.connect).toHaveBeenCalledWith(
          expect.objectContaining({
            url: expect.stringContaining('/websocket'),
            token: 'test-token'
          })
        );
      });
    });

    it('updates status when WebSocket status changes', async () => {
      render(
        <WebSocketProvider>
          <TestComponent />
        </WebSocketProvider>
      );

      // Initial status
      expect(screen.getByTestId('status')).toHaveTextContent('CLOSED');

      await act(async () => {
        jest.advanceTimersByTime(100);
      });

      // Simulate status changes
      await act(async () => {
        if (mockWebSocketService.onStatusChange) {
          mockWebSocketService.onStatusChange('CONNECTING' as any);
        }
      });
      expect(screen.getByTestId('status')).toHaveTextContent('CONNECTING');

      await act(async () => {
        if (mockWebSocketService.onStatusChange) {
          mockWebSocketService.onStatusChange('OPEN' as any);
        }
      });
      expect(screen.getByTestId('status')).toHaveTextContent('OPEN');
    });

    it('disconnects and reconnects when token changes', async () => {
      const { rerender } = render(
        <WebSocketProvider>
          <TestComponent />
        </WebSocketProvider>
      );

      await act(async () => {
        jest.advanceTimersByTime(100);
      });

      expect(mockWebSocketService.connect).toHaveBeenCalledTimes(1);

      // Change token
      mockAuth.token = 'new-token';
      (useAuth as jest.Mock).mockReturnValue(mockAuth);

      rerender(
        <WebSocketProvider>
          <TestComponent />
        </WebSocketProvider>
      );

      await waitFor(() => {
        expect(mockWebSocketService.disconnect).toHaveBeenCalled();
        expect(mockWebSocketService.connect).toHaveBeenCalledTimes(2);
        expect(mockWebSocketService.connect).toHaveBeenLastCalledWith(
          expect.objectContaining({
            token: 'new-token'
          })
        );
      });
    });

    it('disconnects when token is removed (logout)', async () => {
      const { rerender } = render(
        <WebSocketProvider>
          <TestComponent />
        </WebSocketProvider>
      );

      await act(async () => {
        jest.advanceTimersByTime(100);
      });

      expect(mockWebSocketService.connect).toHaveBeenCalledTimes(1);

      // Remove token (logout)
      mockAuth.token = null as any;
      (useAuth as jest.Mock).mockReturnValue(mockAuth);

      rerender(
        <WebSocketProvider>
          <TestComponent />
        </WebSocketProvider>
      );

      await waitFor(() => {
        expect(mockWebSocketService.disconnect).toHaveBeenCalled();
        // Should not reconnect without token
        expect(mockWebSocketService.connect).toHaveBeenCalledTimes(1);
      });
    });

    it('cleans up on unmount', async () => {
      const { unmount } = render(
        <WebSocketProvider>
          <TestComponent />
        </WebSocketProvider>
      );

      await act(async () => {
        jest.advanceTimersByTime(100);
      });

      unmount();

      expect(mockWebSocketService.disconnect).toHaveBeenCalled();
      expect(mockWebSocketService.onMessage).toBeNull();
      expect(mockWebSocketService.onStatusChange).toBeNull();
    });
  });

  describe('Message Handling', () => {
    it('processes messages through reconciliation service', async () => {
      render(
        <WebSocketProvider>
          <TestComponent />
        </WebSocketProvider>
      );

      await act(async () => {
        jest.advanceTimersByTime(100);
        if (mockWebSocketService.onStatusChange) {
          mockWebSocketService.onStatusChange('OPEN' as any);
        }
      });

      const testMessage = {
        type: 'test',
        payload: { message_id: 'test-123', content: 'Test' }
      };

      const reconciledMessage = {
        ...testMessage,
        reconciled: true
      };

      mockReconciliationService.processMessage.mockReturnValueOnce(reconciledMessage);

      await act(async () => {
        if (mockWebSocketService.onMessage) {
          mockWebSocketService.onMessage(testMessage);
        }
      });

      expect(mockReconciliationService.processMessage).toHaveBeenCalledWith(testMessage);
      
      // Should display reconciled message
      const message = screen.getByTestId('message-0');
      expect(message.textContent).toContain('reconciled');
    });

    it('deduplicates messages by message_id', async () => {
      render(
        <WebSocketProvider>
          <TestComponent />
        </WebSocketProvider>
      );

      await act(async () => {
        jest.advanceTimersByTime(100);
        if (mockWebSocketService.onStatusChange) {
          mockWebSocketService.onStatusChange('OPEN' as any);
        }
      });

      const message1 = {
        type: 'test',
        payload: { message_id: 'duplicate-id', content: 'First' }
      };

      const message2 = {
        type: 'test',
        payload: { message_id: 'duplicate-id', content: 'Second' }
      };

      await act(async () => {
        if (mockWebSocketService.onMessage) {
          mockWebSocketService.onMessage(message1);
          mockWebSocketService.onMessage(message2);
        }
      });

      // Should only have one message
      expect(screen.getByTestId('message-count')).toHaveTextContent('1');
      // Should keep the first message
      expect(screen.getByTestId('message-0').textContent).toContain('First');
    });

    it('sends messages through WebSocket service', async () => {
      render(
        <WebSocketProvider>
          <TestComponent />
        </WebSocketProvider>
      );

      await act(async () => {
        jest.advanceTimersByTime(100);
        if (mockWebSocketService.onStatusChange) {
          mockWebSocketService.onStatusChange('OPEN' as any);
        }
      });

      const button = screen.getByText('Send');
      
      await act(async () => {
        button.click();
      });

      expect(mockWebSocketService.send).toHaveBeenCalledWith({ type: 'test' });
    });

    it('handles malformed messages gracefully', async () => {
      render(
        <WebSocketProvider>
          <TestComponent />
        </WebSocketProvider>
      );

      await act(async () => {
        jest.advanceTimersByTime(100);
        if (mockWebSocketService.onStatusChange) {
          mockWebSocketService.onStatusChange('OPEN' as any);
        }
      });

      // Send message without payload
      await act(async () => {
        if (mockWebSocketService.onMessage) {
          mockWebSocketService.onMessage({ type: 'no-payload' });
        }
      });

      // Should still add the message
      expect(screen.getByTestId('message-count')).toHaveTextContent('1');
    });
  });

  describe('Rate Limiting', () => {
    it('configures rate limiting in WebSocket connection', async () => {
      render(
        <WebSocketProvider>
          <TestComponent />
        </WebSocketProvider>
      );

      await act(async () => {
        jest.advanceTimersByTime(100);
      });

      await waitFor(() => {
        expect(mockWebSocketService.connect).toHaveBeenCalledWith(
          expect.objectContaining({
            rateLimit: {
              messages: 60,
              window: 60000 // 60 messages per minute
            }
          })
        );
      });
    });
  });

  describe('Error Handling', () => {
    it('handles connection failure gracefully', async () => {
      mockWebSocketService.connect.mockRejectedValueOnce(new Error('Connection failed'));

      render(
        <WebSocketProvider>
          <TestComponent />
        </WebSocketProvider>
      );

      await act(async () => {
        jest.advanceTimersByTime(100);
      });

      await waitFor(() => {
        expect(mockWebSocketService.connect).toHaveBeenCalled();
      });

      // Should remain in CLOSED status
      expect(screen.getByTestId('status')).toHaveTextContent('CLOSED');
    });

    it('prevents concurrent connection attempts', async () => {
      render(
        <WebSocketProvider>
          <TestComponent />
        </WebSocketProvider>
      );

      // Trigger multiple connection attempts rapidly
      await act(async () => {
        jest.advanceTimersByTime(50);
        jest.advanceTimersByTime(50);
        jest.advanceTimersByTime(50);
      });

      // Should only connect once
      expect(mockWebSocketService.connect).toHaveBeenCalledTimes(1);
    });
  });
});