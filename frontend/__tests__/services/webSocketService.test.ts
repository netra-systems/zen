import { webSocketService } from '@/services/webSocketService';

describe('webSocketService', () => {
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

    // Mock global WebSocket constructor
    global.WebSocket = jest.fn().mockImplementation(() => mockWebSocket) as any;
    
    // Mock localStorage
    Storage.prototype.getItem = jest.fn((key) => {
      if (key === 'authToken') return 'test-token-123';
      return null;
    });
  });

  afterEach(() => {
    jest.useRealTimers();
    webSocketService.disconnect();
  });

  describe('Connection Management', () => {
    it('should establish WebSocket connection', () => {
      const onStatusChange = jest.fn();
      webSocketService.onStatusChange = onStatusChange;
      
      webSocketService.connect('ws://localhost:8000/ws');

      expect(global.WebSocket).toHaveBeenCalledWith('ws://localhost:8000/ws');
      expect(onStatusChange).toHaveBeenCalledWith('CONNECTING');
    });

    it('should handle connection success', () => {
      const onStatusChange = jest.fn();
      const onOpen = jest.fn();
      webSocketService.onStatusChange = onStatusChange;
      
      webSocketService.connect('ws://localhost:8000/ws', { onOpen });
      
      // Simulate connection open
      mockWebSocket.readyState = WebSocket.OPEN;
      mockWebSocket.onopen?.();

      expect(onStatusChange).toHaveBeenCalledWith('OPEN');
      expect(onOpen).toHaveBeenCalled();
      
      // Should send auth token
      expect(mockWebSocket.send).toHaveBeenCalledWith(
        JSON.stringify({ type: 'auth', token: 'test-token-123' })
      );
    });

    it('should handle connection errors', () => {
      const onStatusChange = jest.fn();
      const onError = jest.fn();
      webSocketService.onStatusChange = onStatusChange;
      
      webSocketService.connect('ws://localhost:8000/ws', { onError });
      
      // Simulate error
      const error = new Error('Connection failed');
      mockWebSocket.onerror?.(error as any);

      expect(onStatusChange).toHaveBeenCalledWith('CLOSED');
      expect(onError).toHaveBeenCalledWith(error);
    });

    it('should disconnect WebSocket properly', () => {
      webSocketService.connect('ws://localhost:8000/ws');
      mockWebSocket.readyState = WebSocket.OPEN;
      
      webSocketService.disconnect();

      expect(mockWebSocket.close).toHaveBeenCalled();
    });

    it('should handle multiple connection attempts gracefully', () => {
      webSocketService.connect('ws://localhost:8000/ws');
      webSocketService.connect('ws://localhost:8000/ws');

      // Should only create one WebSocket
      expect(global.WebSocket).toHaveBeenCalledTimes(1);
    });

    it('should handle connection state transitions', () => {
      const onStatusChange = jest.fn();
      webSocketService.onStatusChange = onStatusChange;
      
      webSocketService.connect('ws://localhost:8000/ws');
      expect(webSocketService.getState()).toBe('connecting');
      
      // Open connection
      mockWebSocket.readyState = WebSocket.OPEN;
      mockWebSocket.onopen?.();
      expect(webSocketService.getState()).toBe('connected');
      
      // Close connection
      mockWebSocket.readyState = WebSocket.CLOSED;
      mockWebSocket.onclose?.();
      expect(webSocketService.getState()).toBe('disconnected');
    });
  });

  describe('Message Sending and Receiving', () => {
    beforeEach(() => {
      webSocketService.connect('ws://localhost:8000/ws');
      mockWebSocket.readyState = WebSocket.OPEN;
      mockWebSocket.onopen?.();
    });

    it('should send messages when connected', () => {
      const message = { type: 'test', payload: { data: 'test data' } };

      webSocketService.sendMessage(message);

      expect(mockWebSocket.send).toHaveBeenCalledWith(JSON.stringify(message));
    });

    it('should queue messages when disconnected', () => {
      mockWebSocket.readyState = WebSocket.CLOSED;
      
      const message = { type: 'test', payload: { data: 'queued message' } };

      webSocketService.sendMessage(message);

      // Message should be queued, not sent immediately
      // Auth token is sent on open, so check the send count
      const authCallCount = 1;
      expect(mockWebSocket.send).toHaveBeenCalledTimes(authCallCount);
    });

    it('should send queued messages after reconnection', () => {
      // Queue messages while disconnected
      mockWebSocket.readyState = WebSocket.CLOSED;
      
      const message1 = { type: 'test1', payload: { data: 'message 1' } };
      const message2 = { type: 'test2', payload: { data: 'message 2' } };
      
      webSocketService.sendMessage(message1);
      webSocketService.sendMessage(message2);

      // Clear previous calls
      mockWebSocket.send.mockClear();
      
      // Reconnect
      webSocketService.connect('ws://localhost:8000/ws');
      mockWebSocket.readyState = WebSocket.OPEN;
      mockWebSocket.onopen?.();

      // Should send auth token and queued messages
      expect(mockWebSocket.send).toHaveBeenCalledWith(JSON.stringify({ type: 'auth', token: 'test-token-123' }));
      expect(mockWebSocket.send).toHaveBeenCalledWith(JSON.stringify(message1));
      expect(mockWebSocket.send).toHaveBeenCalledWith(JSON.stringify(message2));
    });

    it('should handle message receiving with proper parsing', () => {
      const onMessage = jest.fn();
      webSocketService.onMessage = onMessage;

      // Simulate receiving message
      const receivedMessage = { type: 'response', payload: { result: 'success' } };
      const messageEvent = new MessageEvent('message', { 
        data: JSON.stringify(receivedMessage) 
      });
      
      mockWebSocket.onmessage?.(messageEvent);

      expect(onMessage).toHaveBeenCalledWith(receivedMessage);
    });

    it('should handle malformed message data gracefully', () => {
      const onMessage = jest.fn();
      const onError = jest.fn();
      webSocketService.onMessage = onMessage;
      
      // Connect with error handler
      webSocketService.connect('ws://localhost:8000/ws', { onError });
      mockWebSocket.readyState = WebSocket.OPEN;
      mockWebSocket.onopen?.();

      // Send malformed JSON
      const messageEvent = new MessageEvent('message', { data: 'invalid json' });
      mockWebSocket.onmessage?.(messageEvent);

      expect(onMessage).not.toHaveBeenCalled();
    });

    it('should handle binary message data', () => {
      const onBinaryMessage = jest.fn();
      
      // Connect with binary handler
      webSocketService.connect('ws://localhost:8000/ws', { onBinaryMessage });
      mockWebSocket.readyState = WebSocket.OPEN;
      mockWebSocket.onopen?.();

      const binaryData = new ArrayBuffer(8);
      const messageEvent = new MessageEvent('message', { data: binaryData });
      mockWebSocket.onmessage?.(messageEvent);

      expect(onBinaryMessage).toHaveBeenCalledWith(binaryData);
    });
  });

  describe('Reconnection Logic', () => {
    it('should attempt reconnection when onReconnect is provided', () => {
      const onReconnect = jest.fn();
      
      webSocketService.connect('ws://localhost:8000/ws', { onReconnect });
      mockWebSocket.readyState = WebSocket.OPEN;
      mockWebSocket.onopen?.();
      
      // Simulate connection close
      mockWebSocket.onclose?.();
      
      // Fast-forward timers to trigger reconnection
      jest.advanceTimersByTime(5000);
      
      expect(onReconnect).toHaveBeenCalled();
    });

    it('should not attempt reconnection without onReconnect', () => {
      webSocketService.connect('ws://localhost:8000/ws');
      mockWebSocket.readyState = WebSocket.OPEN;
      mockWebSocket.onopen?.();
      
      // Simulate connection close
      mockWebSocket.onclose?.();
      
      // Fast-forward timers
      jest.advanceTimersByTime(5000);
      
      // Should only have the initial connection
      expect(global.WebSocket).toHaveBeenCalledTimes(1);
    });

    it('should cancel reconnection on explicit disconnect', () => {
      const onReconnect = jest.fn();
      
      webSocketService.connect('ws://localhost:8000/ws', { onReconnect });
      mockWebSocket.readyState = WebSocket.OPEN;
      mockWebSocket.onopen?.();
      
      // Simulate connection close
      mockWebSocket.onclose?.();
      
      // Disconnect before reconnection timer fires
      webSocketService.disconnect();
      
      jest.advanceTimersByTime(5000);
      
      // Should not reconnect after explicit disconnect
      expect(onReconnect).not.toHaveBeenCalled();
    });
  });

  describe('Heartbeat Mechanism', () => {
    it('should send heartbeat messages at configured interval', () => {
      webSocketService.connect('ws://localhost:8000/ws', { heartbeatInterval: 30000 });
      mockWebSocket.readyState = WebSocket.OPEN;
      mockWebSocket.onopen?.();
      
      // Clear auth message
      mockWebSocket.send.mockClear();
      
      // Advance time to trigger heartbeat
      jest.advanceTimersByTime(30000);
      
      expect(mockWebSocket.send).toHaveBeenCalledWith(
        JSON.stringify({ type: 'ping' })
      );
    });

    it('should stop heartbeat on disconnect', () => {
      webSocketService.connect('ws://localhost:8000/ws', { heartbeatInterval: 30000 });
      mockWebSocket.readyState = WebSocket.OPEN;
      mockWebSocket.onopen?.();
      
      webSocketService.disconnect();
      
      // Clear all previous calls
      mockWebSocket.send.mockClear();
      
      // Advance time
      jest.advanceTimersByTime(30000);
      
      // Should not send heartbeat after disconnect
      expect(mockWebSocket.send).not.toHaveBeenCalled();
    });
  });

  describe('Rate Limiting', () => {
    it('should enforce rate limits when configured', () => {
      const onRateLimit = jest.fn();
      const rateLimit = { messages: 3, window: 1000 };
      
      webSocketService.connect('ws://localhost:8000/ws', { rateLimit, onRateLimit });
      mockWebSocket.readyState = WebSocket.OPEN;
      mockWebSocket.onopen?.();
      
      // Clear auth message
      mockWebSocket.send.mockClear();
      
      // Send messages rapidly
      for (let i = 0; i < 5; i++) {
        webSocketService.sendMessage({ type: 'test', payload: { index: i } });
      }
      
      // Should only send up to rate limit
      expect(mockWebSocket.send).toHaveBeenCalledTimes(3);
      expect(onRateLimit).toHaveBeenCalledTimes(2);
    });

    it('should reset rate limit window over time', () => {
      const rateLimit = { messages: 2, window: 1000 };
      
      webSocketService.connect('ws://localhost:8000/ws', { rateLimit });
      mockWebSocket.readyState = WebSocket.OPEN;
      mockWebSocket.onopen?.();
      
      // Clear auth message
      mockWebSocket.send.mockClear();
      
      // Send 2 messages (at limit)
      webSocketService.sendMessage({ type: 'test1', payload: {} });
      webSocketService.sendMessage({ type: 'test2', payload: {} });
      
      expect(mockWebSocket.send).toHaveBeenCalledTimes(2);
      
      // Advance time past window
      jest.advanceTimersByTime(1100);
      
      // Should be able to send more messages
      webSocketService.sendMessage({ type: 'test3', payload: {} });
      
      expect(mockWebSocket.send).toHaveBeenCalledTimes(3);
    });
  });

  describe('Error Handling', () => {
    it('should handle WebSocket errors gracefully', () => {
      const onError = jest.fn();
      const onStatusChange = jest.fn();
      webSocketService.onStatusChange = onStatusChange;
      
      webSocketService.connect('ws://localhost:8000/ws', { onError });
      
      const error = new Error('WebSocket error');
      mockWebSocket.onerror?.(error as any);

      expect(onError).toHaveBeenCalledWith(error);
      expect(onStatusChange).toHaveBeenCalledWith('CLOSED');
    });

    it('should handle connection failure gracefully', () => {
      const onError = jest.fn();
      
      // Make WebSocket constructor throw
      global.WebSocket = jest.fn().mockImplementation(() => {
        throw new Error('Failed to create WebSocket');
      }) as any;
      
      webSocketService.connect('ws://localhost:8000/ws', { onError });
      
      expect(onError).toHaveBeenCalledWith(expect.any(Error));
    });

    it('should handle message sending errors', () => {
      webSocketService.connect('ws://localhost:8000/ws');
      mockWebSocket.readyState = WebSocket.OPEN;
      mockWebSocket.onopen?.();
      
      // Make send throw an error
      mockWebSocket.send.mockImplementation(() => {
        throw new Error('Send failed');
      });
      
      // Should not throw when sending message
      expect(() => {
        webSocketService.sendMessage({ type: 'test', payload: {} });
      }).not.toThrow();
    });
  });

  describe('State Management', () => {
    it('should track connection state accurately', () => {
      expect(webSocketService.getState()).toBe('disconnected');
      
      webSocketService.connect('ws://localhost:8000/ws');
      expect(webSocketService.getState()).toBe('connecting');
      
      mockWebSocket.readyState = WebSocket.OPEN;
      mockWebSocket.onopen?.();
      expect(webSocketService.getState()).toBe('connected');
      
      mockWebSocket.onclose?.();
      expect(webSocketService.getState()).toBe('disconnected');
    });

    it('should track reconnecting state', () => {
      const onReconnect = jest.fn();
      
      webSocketService.connect('ws://localhost:8000/ws', { onReconnect });
      mockWebSocket.readyState = WebSocket.OPEN;
      mockWebSocket.onopen?.();
      
      // Trigger reconnection
      mockWebSocket.onclose?.();
      
      // State should change to reconnecting
      expect(webSocketService.getState()).toBe('reconnecting');
    });
  });
});