import { webSocketService } from '@/services/webSocketService';
import { WebSocketManager } from '@/lib/websocket-manager';

// Mock WebSocketManager
jest.mock('@/lib/websocket-manager');

describe('webSocketService', () => {
  let mockWebSocketManager: jest.Mocked<WebSocketManager>;
  let mockWebSocket: jest.Mocked<WebSocket>;

  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();

    // Mock WebSocket
    mockWebSocket = {
      readyState: WebSocket.CONNECTING,
      close: jest.fn(),
      send: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      dispatchEvent: jest.fn(),
      url: 'ws://localhost:8000/ws',
      protocol: '',
      extensions: '',
      bufferedAmount: 0,
      binaryType: 'blob' as BinaryType,
      onopen: null,
      onclose: null,
      onerror: null,
      onmessage: null,
      CONNECTING: WebSocket.CONNECTING,
      OPEN: WebSocket.OPEN,
      CLOSING: WebSocket.CLOSING,
      CLOSED: WebSocket.CLOSED
    } as jest.Mocked<WebSocket>;

    // Mock WebSocketManager instance
    mockWebSocketManager = {
      connect: jest.fn(),
      disconnect: jest.fn(),
      send: jest.fn(),
      isConnected: jest.fn(),
      getConnectionState: jest.fn(),
      setMessageHandler: jest.fn(),
      setErrorHandler: jest.fn(),
      setConnectionHandler: jest.fn(),
      reconnect: jest.fn(),
      getSocket: jest.fn().mockReturnValue(mockWebSocket),
      destroy: jest.fn(),
      getReconnectAttempts: jest.fn().mockReturnValue(0),
      getLastError: jest.fn().mockReturnValue(null),
      onOpen: jest.fn(),
      onClose: jest.fn(),
      onError: jest.fn(),
      onMessage: jest.fn()
    } as jest.Mocked<WebSocketManager>;

    (WebSocketManager as jest.Mock).mockImplementation(() => mockWebSocketManager);
  });

  afterEach(() => {
    jest.useRealTimers();
    webSocketService.disconnect();
  });

  describe('Connection Management', () => {
    it('should establish WebSocket connection', async () => {
      mockWebSocketManager.connect.mockResolvedValueOnce(undefined);
      mockWebSocketManager.isConnected.mockReturnValue(false);

      await webSocketService.connect('ws://localhost:8000/ws');

      expect(mockWebSocketManager.connect).toHaveBeenCalledWith('ws://localhost:8000/ws');
    });

    it('should handle connection success', async () => {
      mockWebSocketManager.connect.mockResolvedValueOnce(undefined);
      mockWebSocketManager.isConnected.mockReturnValue(true);
      mockWebSocketManager.getConnectionState.mockReturnValue('connected');

      const connectionPromise = webSocketService.connect('ws://localhost:8000/ws');

      // Simulate connection open
      const connectHandler = mockWebSocketManager.setConnectionHandler.mock.calls[0][0];
      connectHandler('connected', null);

      await connectionPromise;

      expect(webSocketService.isConnected()).toBe(true);
      expect(webSocketService.getConnectionState()).toBe('connected');
    });

    it('should handle connection errors', async () => {
      const connectionError = new Error('Connection failed');
      mockWebSocketManager.connect.mockRejectedValueOnce(connectionError);

      await expect(webSocketService.connect('ws://localhost:8000/ws')).rejects.toThrow('Connection failed');
    });

    it('should disconnect WebSocket properly', () => {
      mockWebSocketManager.isConnected.mockReturnValue(true);

      webSocketService.disconnect();

      expect(mockWebSocketManager.disconnect).toHaveBeenCalled();
    });

    it('should handle multiple connection attempts gracefully', async () => {
      mockWebSocketManager.connect.mockResolvedValue(undefined);
      mockWebSocketManager.isConnected.mockReturnValue(false).mockReturnValueOnce(true);

      // First connection
      await webSocketService.connect('ws://localhost:8000/ws');
      
      // Second connection attempt should not create new connection
      await webSocketService.connect('ws://localhost:8000/ws');

      expect(mockWebSocketManager.connect).toHaveBeenCalledTimes(1);
    });

    it('should handle connection state transitions', () => {
      const states = ['connecting', 'connected', 'disconnected', 'error', 'reconnecting'];
      
      states.forEach(state => {
        mockWebSocketManager.getConnectionState.mockReturnValue(state);
        expect(webSocketService.getConnectionState()).toBe(state);
      });
    });
  });

  describe('Message Sending and Receiving', () => {
    beforeEach(() => {
      mockWebSocketManager.isConnected.mockReturnValue(true);
    });

    it('should send messages when connected', () => {
      const message = { type: 'test', payload: { data: 'test data' } };

      webSocketService.sendMessage(message);

      expect(mockWebSocketManager.send).toHaveBeenCalledWith(JSON.stringify(message));
    });

    it('should queue messages when disconnected', () => {
      mockWebSocketManager.isConnected.mockReturnValue(false);
      
      const message = { type: 'test', payload: { data: 'queued message' } };

      webSocketService.sendMessage(message);

      // Message should be queued, not sent immediately
      expect(mockWebSocketManager.send).not.toHaveBeenCalled();
    });

    it('should send queued messages after reconnection', () => {
      mockWebSocketManager.isConnected.mockReturnValue(false);
      
      // Queue messages while disconnected
      const message1 = { type: 'test1', payload: { data: 'message 1' } };
      const message2 = { type: 'test2', payload: { data: 'message 2' } };
      
      webSocketService.sendMessage(message1);
      webSocketService.sendMessage(message2);

      // Reconnect
      mockWebSocketManager.isConnected.mockReturnValue(true);
      const connectionHandler = mockWebSocketManager.setConnectionHandler.mock.calls[0][0];
      connectionHandler('connected', null);

      // Should send queued messages
      expect(mockWebSocketManager.send).toHaveBeenCalledWith(JSON.stringify(message1));
      expect(mockWebSocketManager.send).toHaveBeenCalledWith(JSON.stringify(message2));
    });

    it('should handle message receiving with proper parsing', () => {
      let messageHandler: ((message: any) => void) | null = null;
      mockWebSocketManager.setMessageHandler.mockImplementation(handler => {
        messageHandler = handler;
      });

      const onMessage = jest.fn();
      webSocketService.onMessage(onMessage);

      // Simulate receiving message
      const receivedMessage = { type: 'response', payload: { result: 'success' } };
      messageHandler?.(new MessageEvent('message', { 
        data: JSON.stringify(receivedMessage) 
      }));

      expect(onMessage).toHaveBeenCalledWith(receivedMessage);
    });

    it('should handle malformed message data gracefully', () => {
      let messageHandler: ((message: any) => void) | null = null;
      mockWebSocketManager.setMessageHandler.mockImplementation(handler => {
        messageHandler = handler;
      });

      const onMessage = jest.fn();
      const onError = jest.fn();
      webSocketService.onMessage(onMessage);
      webSocketService.onError(onError);

      // Send malformed JSON
      messageHandler?.(new MessageEvent('message', { data: 'invalid json' }));

      expect(onMessage).not.toHaveBeenCalled();
      expect(onError).toHaveBeenCalledWith(expect.any(Error));
    });

    it('should support message filtering by type', () => {
      let messageHandler: ((message: any) => void) | null = null;
      mockWebSocketManager.setMessageHandler.mockImplementation(handler => {
        messageHandler = handler;
      });

      const chatMessageHandler = jest.fn();
      const statusMessageHandler = jest.fn();
      
      webSocketService.onMessageType('chat_message', chatMessageHandler);
      webSocketService.onMessageType('status_update', statusMessageHandler);

      // Send different message types
      messageHandler?.(new MessageEvent('message', { 
        data: JSON.stringify({ type: 'chat_message', payload: { text: 'Hello' } })
      }));
      
      messageHandler?.(new MessageEvent('message', { 
        data: JSON.stringify({ type: 'status_update', payload: { status: 'processing' } })
      }));

      expect(chatMessageHandler).toHaveBeenCalledWith({ type: 'chat_message', payload: { text: 'Hello' } });
      expect(statusMessageHandler).toHaveBeenCalledWith({ type: 'status_update', payload: { status: 'processing' } });
    });

    it('should handle binary message data', () => {
      let messageHandler: ((message: any) => void) | null = null;
      mockWebSocketManager.setMessageHandler.mockImplementation(handler => {
        messageHandler = handler;
      });

      const onBinaryMessage = jest.fn();
      webSocketService.onBinaryMessage(onBinaryMessage);

      const binaryData = new Uint8Array([1, 2, 3, 4]);
      messageHandler?.(new MessageEvent('message', { data: binaryData }));

      expect(onBinaryMessage).toHaveBeenCalledWith(binaryData);
    });

    it('should validate message format before sending', () => {
      const invalidMessage = { invalid: 'message without type' };

      expect(() => {
        webSocketService.sendMessage(invalidMessage as any);
      }).toThrow('Invalid message format');

      expect(mockWebSocketManager.send).not.toHaveBeenCalled();
    });

    it('should add message IDs for tracking', () => {
      const message = { type: 'test', payload: { data: 'test' } };

      webSocketService.sendMessage(message);

      const sentMessage = JSON.parse(mockWebSocketManager.send.mock.calls[0][0]);
      expect(sentMessage.id).toBeDefined();
      expect(sentMessage.timestamp).toBeDefined();
    });
  });

  describe('Reconnection Logic and Exponential Backoff', () => {
    it('should attempt reconnection with exponential backoff', async () => {
      mockWebSocketManager.isConnected.mockReturnValue(false);
      mockWebSocketManager.getReconnectAttempts.mockReturnValue(0);

      // Enable auto-reconnect
      webSocketService.setAutoReconnect(true);

      // Simulate connection failure
      const connectionHandler = mockWebSocketManager.setConnectionHandler.mock.calls[0][0];
      connectionHandler('error', new Error('Connection lost'));

      // First reconnect attempt (immediate)
      expect(mockWebSocketManager.reconnect).toHaveBeenCalledTimes(1);

      // Simulate failure and advance time for exponential backoff
      mockWebSocketManager.getReconnectAttempts.mockReturnValue(1);
      connectionHandler('error', new Error('Reconnection failed'));

      jest.advanceTimersByTime(2000); // 2^1 * 1000ms = 2000ms

      expect(mockWebSocketManager.reconnect).toHaveBeenCalledTimes(2);
    });

    it('should implement exponential backoff with jitter', () => {
      mockWebSocketManager.isConnected.mockReturnValue(false);
      webSocketService.setAutoReconnect(true);

      const connectionHandler = mockWebSocketManager.setConnectionHandler.mock.calls[0][0];

      // Track reconnection delays
      const delays: number[] = [];
      let originalSetTimeout = global.setTimeout;
      
      global.setTimeout = jest.fn((callback, delay) => {
        delays.push(delay);
        return originalSetTimeout(callback, 0);
      });

      // Simulate multiple failed reconnections
      for (let i = 0; i < 5; i++) {
        mockWebSocketManager.getReconnectAttempts.mockReturnValue(i);
        connectionHandler('error', new Error('Connection failed'));
        jest.advanceTimersByTime(10000); // Advance enough time
      }

      global.setTimeout = originalSetTimeout;

      // Verify exponential backoff pattern
      expect(delays[0]).toBeLessThanOrEqual(2000); // First: 1000ms + jitter
      expect(delays[1]).toBeLessThanOrEqual(4000); // Second: 2000ms + jitter
      expect(delays[2]).toBeLessThanOrEqual(8000); // Third: 4000ms + jitter
      expect(delays[3]).toBeLessThanOrEqual(16000); // Fourth: 8000ms + jitter
      expect(delays[4]).toBeLessThanOrEqual(30000); // Fifth: max 30000ms
    });

    it('should stop reconnection after max attempts', () => {
      mockWebSocketManager.isConnected.mockReturnValue(false);
      webSocketService.setAutoReconnect(true);
      webSocketService.setMaxReconnectAttempts(3);

      const connectionHandler = mockWebSocketManager.setConnectionHandler.mock.calls[0][0];

      // Exceed max attempts
      mockWebSocketManager.getReconnectAttempts.mockReturnValue(3);
      connectionHandler('error', new Error('Max attempts reached'));

      jest.advanceTimersByTime(10000);

      // Should not attempt more reconnections
      expect(mockWebSocketManager.reconnect).toHaveBeenCalledTimes(3);
    });

    it('should reset reconnect attempts after successful connection', () => {
      mockWebSocketManager.isConnected.mockReturnValue(false);
      webSocketService.setAutoReconnect(true);

      const connectionHandler = mockWebSocketManager.setConnectionHandler.mock.calls[0][0];

      // Fail a few times
      mockWebSocketManager.getReconnectAttempts.mockReturnValue(2);
      connectionHandler('error', new Error('Connection failed'));

      // Then succeed
      mockWebSocketManager.isConnected.mockReturnValue(true);
      connectionHandler('connected', null);

      // Should reset attempts counter
      expect(webSocketService.getReconnectAttempts()).toBe(0);
    });

    it('should allow manual reconnection', async () => {
      mockWebSocketManager.isConnected.mockReturnValue(false);
      mockWebSocketManager.reconnect.mockResolvedValueOnce(undefined);

      await webSocketService.reconnect();

      expect(mockWebSocketManager.reconnect).toHaveBeenCalled();
    });

    it('should handle rapid connection state changes', () => {
      const connectionHandler = mockWebSocketManager.setConnectionHandler.mock.calls[0][0];
      const stateChanges: string[] = [];

      webSocketService.onConnectionChange((state) => {
        stateChanges.push(state);
      });

      // Rapid state changes
      connectionHandler('connecting', null);
      connectionHandler('connected', null);
      connectionHandler('error', new Error('Test'));
      connectionHandler('reconnecting', null);
      connectionHandler('connected', null);

      expect(stateChanges).toEqual(['connecting', 'connected', 'error', 'reconnecting', 'connected']);
    });

    it('should disable auto-reconnect when explicitly disconnected', () => {
      webSocketService.setAutoReconnect(true);
      mockWebSocketManager.isConnected.mockReturnValue(true);

      webSocketService.disconnect();

      const connectionHandler = mockWebSocketManager.setConnectionHandler.mock.calls[0][0];
      connectionHandler('disconnected', null);

      jest.advanceTimersByTime(10000);

      // Should not attempt reconnection after explicit disconnect
      expect(mockWebSocketManager.reconnect).not.toHaveBeenCalled();
    });

    it('should respect network status for reconnection attempts', () => {
      webSocketService.setAutoReconnect(true);
      
      // Mock navigator.onLine
      Object.defineProperty(navigator, 'onLine', {
        writable: true,
        value: false
      });

      const connectionHandler = mockWebSocketManager.setConnectionHandler.mock.calls[0][0];
      connectionHandler('error', new Error('Network error'));

      jest.advanceTimersByTime(5000);

      // Should not attempt reconnection while offline
      expect(mockWebSocketManager.reconnect).not.toHaveBeenCalled();

      // Come back online
      Object.defineProperty(navigator, 'onLine', { value: true });
      window.dispatchEvent(new Event('online'));

      jest.advanceTimersByTime(1000);

      // Should attempt reconnection when online
      expect(mockWebSocketManager.reconnect).toHaveBeenCalled();
    });
  });

  describe('Error Handling and Recovery', () => {
    it('should handle WebSocket errors gracefully', () => {
      const onError = jest.fn();
      webSocketService.onError(onError);

      const errorHandler = mockWebSocketManager.setErrorHandler.mock.calls[0][0];
      const error = new Error('WebSocket error');
      errorHandler(error);

      expect(onError).toHaveBeenCalledWith(error);
    });

    it('should categorize different error types', () => {
      const onError = jest.fn();
      webSocketService.onError(onError);

      const errorHandler = mockWebSocketManager.setErrorHandler.mock.calls[0][0];

      // Network error
      errorHandler(new Error('Network error'));
      expect(onError).toHaveBeenCalledWith(expect.objectContaining({
        type: 'network_error'
      }));

      // Protocol error
      errorHandler(new Error('WebSocket protocol error'));
      expect(onError).toHaveBeenCalledWith(expect.objectContaining({
        type: 'protocol_error'
      }));

      // Authentication error
      errorHandler(new Error('Authentication failed'));
      expect(onError).toHaveBeenCalledWith(expect.objectContaining({
        type: 'auth_error'
      }));
    });

    it('should implement circuit breaker pattern for failing connections', () => {
      webSocketService.setAutoReconnect(true);
      const connectionHandler = mockWebSocketManager.setConnectionHandler.mock.calls[0][0];

      // Fail rapidly 5 times within short period
      for (let i = 0; i < 5; i++) {
        mockWebSocketManager.getReconnectAttempts.mockReturnValue(i);
        connectionHandler('error', new Error('Rapid failure'));
        jest.advanceTimersByTime(100); // Very short interval
      }

      // Circuit should be open, no more attempts
      jest.advanceTimersByTime(5000);
      expect(webSocketService.getConnectionState()).toBe('circuit_open');

      // After circuit breaker timeout, should allow attempts again
      jest.advanceTimersByTime(30000); // Circuit breaker timeout
      expect(webSocketService.getConnectionState()).toBe('circuit_half_open');
    });

    it('should handle message sending errors', () => {
      mockWebSocketManager.isConnected.mockReturnValue(true);
      mockWebSocketManager.send.mockImplementation(() => {
        throw new Error('Send failed');
      });

      const onError = jest.fn();
      webSocketService.onError(onError);

      const message = { type: 'test', payload: { data: 'test' } };
      webSocketService.sendMessage(message);

      expect(onError).toHaveBeenCalledWith(expect.any(Error));
    });

    it('should recover from temporary network issues', async () => {
      webSocketService.setAutoReconnect(true);
      const connectionHandler = mockWebSocketManager.setConnectionHandler.mock.calls[0][0];

      // Simulate network interruption
      connectionHandler('error', new Error('Network interrupted'));

      // Should attempt reconnection
      expect(mockWebSocketManager.reconnect).toHaveBeenCalled();

      // Simulate successful recovery
      mockWebSocketManager.isConnected.mockReturnValue(true);
      connectionHandler('connected', null);

      expect(webSocketService.getConnectionState()).toBe('connected');
    });

    it('should handle server shutdown gracefully', () => {
      mockWebSocketManager.isConnected.mockReturnValue(true);
      const connectionHandler = mockWebSocketManager.setConnectionHandler.mock.calls[0][0];

      // Simulate clean server shutdown
      connectionHandler('closed', { code: 1000, reason: 'Server shutdown' });

      expect(webSocketService.getConnectionState()).toBe('disconnected');
    });

    it('should handle unexpected disconnections', () => {
      webSocketService.setAutoReconnect(true);
      mockWebSocketManager.isConnected.mockReturnValue(false);
      
      const connectionHandler = mockWebSocketManager.setConnectionHandler.mock.calls[0][0];

      // Simulate unexpected disconnection
      connectionHandler('closed', { code: 1006, reason: 'Abnormal closure' });

      // Should attempt reconnection for abnormal closures
      jest.advanceTimersByTime(1000);
      expect(mockWebSocketManager.reconnect).toHaveBeenCalled();
    });

    it('should maintain error logs for debugging', () => {
      const errorHandler = mockWebSocketManager.setErrorHandler.mock.calls[0][0];
      
      const errors = [
        new Error('Connection timeout'),
        new Error('Protocol violation'),
        new Error('Authentication failed')
      ];

      errors.forEach(error => errorHandler(error));

      const errorLog = webSocketService.getErrorLog();
      expect(errorLog).toHaveLength(3);
      expect(errorLog[0]).toMatchObject({
        error: 'Connection timeout',
        timestamp: expect.any(Number)
      });
    });
  });

  describe('Performance and Resource Management', () => {
    it('should manage message queue size to prevent memory leaks', () => {
      mockWebSocketManager.isConnected.mockReturnValue(false);

      // Send many messages while disconnected
      for (let i = 0; i < 1000; i++) {
        webSocketService.sendMessage({ type: 'test', payload: { index: i } });
      }

      const queueSize = webSocketService.getQueueSize();
      expect(queueSize).toBeLessThanOrEqual(100); // Should limit queue size
    });

    it('should clean up resources on disconnect', () => {
      const cleanup = jest.spyOn(webSocketService, 'cleanup' as any);
      
      webSocketService.disconnect();

      expect(mockWebSocketManager.destroy).toHaveBeenCalled();
      expect(cleanup).toHaveBeenCalled();
    });

    it('should throttle reconnection attempts under high frequency', () => {
      webSocketService.setAutoReconnect(true);
      const connectionHandler = mockWebSocketManager.setConnectionHandler.mock.calls[0][0];

      // Rapid fire connection attempts
      for (let i = 0; i < 10; i++) {
        connectionHandler('error', new Error('Rapid error'));
      }

      // Should throttle to prevent overwhelming the server
      expect(mockWebSocketManager.reconnect).toHaveBeenCalledTimes(1);
    });

    it('should implement heartbeat mechanism', () => {
      mockWebSocketManager.isConnected.mockReturnValue(true);
      
      webSocketService.startHeartbeat(30000); // 30 second heartbeat

      jest.advanceTimersByTime(30000);

      // Should send ping message
      expect(mockWebSocketManager.send).toHaveBeenCalledWith(
        JSON.stringify({ type: 'ping', timestamp: expect.any(Number) })
      );
    });

    it('should detect stale connections with heartbeat', () => {
      mockWebSocketManager.isConnected.mockReturnValue(true);
      webSocketService.startHeartbeat(30000);

      const messageHandler = mockWebSocketManager.setMessageHandler.mock.calls[0][0];
      const connectionHandler = mockWebSocketManager.setConnectionHandler.mock.calls[0][0];

      // Send ping
      jest.advanceTimersByTime(30000);

      // Don't receive pong within timeout
      jest.advanceTimersByTime(10000);

      // Should detect stale connection and reconnect
      expect(connectionHandler).toHaveBeenCalledWith('stale', expect.any(Error));
    });

    it('should optimize message batching for high throughput', () => {
      mockWebSocketManager.isConnected.mockReturnValue(true);
      webSocketService.enableMessageBatching(true);

      // Send multiple messages rapidly
      const messages = Array.from({ length: 5 }, (_, i) => ({
        type: 'batch_test',
        payload: { index: i }
      }));

      messages.forEach(msg => webSocketService.sendMessage(msg));

      // Should batch messages and send as single frame
      expect(mockWebSocketManager.send).toHaveBeenCalledTimes(1);
      
      const batchedMessage = JSON.parse(mockWebSocketManager.send.mock.calls[0][0]);
      expect(batchedMessage.type).toBe('batch');
      expect(batchedMessage.payload.messages).toHaveLength(5);
    });

    it('should handle memory pressure gracefully', () => {
      // Mock memory pressure
      const memoryInfo = { totalJSHeapSize: 100 * 1024 * 1024 }; // 100MB
      Object.defineProperty(performance, 'memory', { value: memoryInfo });

      webSocketService.handleMemoryPressure();

      // Should clean up non-essential data
      expect(webSocketService.getQueueSize()).toBe(0);
      expect(webSocketService.getErrorLog()).toHaveLength(0);
    });
  });

  describe('Security and Validation', () => {
    it('should validate WebSocket URL format', () => {
      const invalidUrls = [
        'http://localhost:8000', // Wrong protocol
        'ws://invalid-url', // Invalid URL
        '', // Empty URL
        'ws://localhost:8000/ws?token=', // Empty token
      ];

      invalidUrls.forEach(url => {
        expect(() => webSocketService.connect(url)).toThrow();
      });
    });

    it('should sanitize message data before sending', () => {
      mockWebSocketManager.isConnected.mockReturnValue(true);

      const maliciousMessage = {
        type: 'test',
        payload: {
          script: '<script>alert("xss")</script>',
          html: '<img src="x" onerror="alert(1)">',
          normal: 'safe content'
        }
      };

      webSocketService.sendMessage(maliciousMessage);

      const sentData = JSON.parse(mockWebSocketManager.send.mock.calls[0][0]);
      
      // Should sanitize HTML/script content
      expect(sentData.payload.script).not.toContain('<script>');
      expect(sentData.payload.html).not.toContain('onerror=');
      expect(sentData.payload.normal).toBe('safe content');
    });

    it('should handle authentication token refresh', async () => {
      const tokenRefreshCallback = jest.fn().mockResolvedValue('new_token_123');
      webSocketService.setTokenRefreshCallback(tokenRefreshCallback);

      // Simulate authentication error
      const errorHandler = mockWebSocketManager.setErrorHandler.mock.calls[0][0];
      errorHandler(new Error('Authentication expired'));

      await Promise.resolve(); // Wait for async operations

      expect(tokenRefreshCallback).toHaveBeenCalled();
      expect(mockWebSocketManager.reconnect).toHaveBeenCalledWith('new_token_123');
    });

    it('should prevent message injection attacks', () => {
      mockWebSocketManager.isConnected.mockReturnValue(true);

      const injectionAttempt = {
        type: 'test',
        payload: {
          __proto__: { malicious: 'payload' },
          constructor: { name: 'attack' }
        }
      };

      webSocketService.sendMessage(injectionAttempt);

      const sentData = JSON.parse(mockWebSocketManager.send.mock.calls[0][0]);
      
      // Should strip prototype pollution attempts
      expect(sentData.payload.__proto__).toBeUndefined();
      expect(sentData.payload.constructor).toBeUndefined();
    });

    it('should implement rate limiting for message sending', () => {
      mockWebSocketManager.isConnected.mockReturnValue(true);
      webSocketService.setRateLimit(5, 1000); // 5 messages per second

      // Send messages rapidly
      for (let i = 0; i < 10; i++) {
        webSocketService.sendMessage({ type: 'test', payload: { index: i } });
      }

      // Should only send allowed number of messages
      expect(mockWebSocketManager.send).toHaveBeenCalledTimes(5);
    });

    it('should validate message size limits', () => {
      mockWebSocketManager.isConnected.mockReturnValue(true);

      const largeMessage = {
        type: 'test',
        payload: {
          data: 'x'.repeat(1024 * 1024) // 1MB message
        }
      };

      expect(() => {
        webSocketService.sendMessage(largeMessage);
      }).toThrow('Message size exceeds limit');
    });

    it('should handle SSL/TLS connection upgrades', async () => {
      const httpsUrl = 'wss://secure.example.com/ws';
      mockWebSocketManager.connect.mockResolvedValueOnce(undefined);

      await webSocketService.connect(httpsUrl);

      expect(mockWebSocketManager.connect).toHaveBeenCalledWith(httpsUrl);
    });
  });
});