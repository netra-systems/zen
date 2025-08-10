import WS from 'jest-websocket-mock';
import { webSocketService } from '../../services/webSocketService';

describe('WebSocketService', () => {
  let server: WS;
  const mockUrl = 'ws://localhost:8000/ws';
  const mockToken = 'test-jwt-token';

  beforeEach(() => {
    jest.useFakeTimers();
    server = new WS(mockUrl);
    localStorage.setItem('authToken', mockToken);
  });

  afterEach(() => {
    jest.useRealTimers();
    WS.clean();
    localStorage.clear();
    webSocketService.disconnect();
  });

  describe('Connection Management', () => {
    it('should establish WebSocket connection with authentication', async () => {
      const onOpen = jest.fn();
      const onMessage = jest.fn();
      const onError = jest.fn();
      const onClose = jest.fn();

      webSocketService.connect(mockUrl, {
        onOpen,
        onMessage,
        onError,
        onClose,
      });

      await server.connected;
      expect(server).toHaveReceivedMessages([
        JSON.stringify({ type: 'auth', token: mockToken })
      ]);
      expect(onOpen).toHaveBeenCalled();
    });

    it('should handle connection failure gracefully', async () => {
      const onError = jest.fn();
      server.close();

      webSocketService.connect(mockUrl, {
        onOpen: jest.fn(),
        onMessage: jest.fn(),
        onError,
        onClose: jest.fn(),
      });

      await expect(server.connected).rejects.toThrow();
    });

    it('should reconnect automatically on unexpected disconnect', async () => {
      jest.useFakeTimers();
      const onReconnect = jest.fn();

      webSocketService.connect(mockUrl, {
        onOpen: jest.fn(),
        onMessage: jest.fn(),
        onError: jest.fn(),
        onClose: jest.fn(),
        onReconnect,
      });

      await server.connected;
      server.error();
      
      jest.advanceTimersByTime(5000);
      
      expect(onReconnect).toHaveBeenCalled();
      jest.useRealTimers();
    });

    it('should handle message queuing when disconnected', async () => {
      const message = { type: 'chat', content: 'Hello' };
      
      webSocketService.send(message);
      
      webSocketService.connect(mockUrl, {
        onOpen: jest.fn(),
        onMessage: jest.fn(),
        onError: jest.fn(),
        onClose: jest.fn(),
      });

      await server.connected;
      
      expect(server).toHaveReceivedMessages([
        JSON.stringify({ type: 'auth', token: mockToken }),
        JSON.stringify(message)
      ]);
    });
  });

  describe('Message Handling', () => {
    it('should parse and route incoming messages correctly', async () => {
      const onMessage = jest.fn();
      
      webSocketService.connect(mockUrl, {
        onOpen: jest.fn(),
        onMessage,
        onError: jest.fn(),
        onClose: jest.fn(),
      });

      await server.connected;

      const testMessage = {
        type: 'agent_response',
        data: { content: 'Test response' }
      };

      server.send(JSON.stringify(testMessage));

      expect(onMessage).toHaveBeenCalledWith(testMessage);
    });

    it('should handle malformed messages gracefully', async () => {
      const onError = jest.fn();
      
      webSocketService.connect(mockUrl, {
        onOpen: jest.fn(),
        onMessage: jest.fn(),
        onError,
        onClose: jest.fn(),
      });

      await server.connected;
      
      server.send('invalid json {');
      
      expect(onError).toHaveBeenCalledWith(
        expect.objectContaining({
          message: expect.stringContaining('parse')
        })
      );
    });

    it('should handle binary data correctly', async () => {
      const onBinaryMessage = jest.fn();
      const onOpen = jest.fn();
      
      webSocketService.connect(mockUrl, {
        onOpen,
        onMessage: jest.fn(),
        onError: jest.fn(),
        onClose: jest.fn(),
        onBinaryMessage,
      });

      await server.connected;
      
      // Wait for onOpen to be called
      await new Promise(resolve => setTimeout(resolve, 0));
      
      const binaryData = new ArrayBuffer(8);
      server.send(binaryData);
      
      // Wait for message processing
      await new Promise(resolve => setTimeout(resolve, 0));
      
      expect(onBinaryMessage).toHaveBeenCalledWith(binaryData);
    });
  });

  describe('State Management', () => {
    it('should track connection state accurately', async () => {
      expect(webSocketService.getState()).toBe('disconnected');
      
      const onOpen = jest.fn();
      webSocketService.connect(mockUrl, {
        onOpen,
        onMessage: jest.fn(),
        onError: jest.fn(),
        onClose: jest.fn(),
      });

      expect(webSocketService.getState()).toBe('connecting');
      
      await server.connected;
      
      // Wait for the onOpen callback to be executed
      await new Promise(resolve => {
        const checkState = () => {
          if (webSocketService.getState() === 'connected' || onOpen.mock.calls.length > 0) {
            resolve(undefined);
          } else {
            setTimeout(checkState, 10);
          }
        };
        checkState();
      });
      
      expect(webSocketService.getState()).toBe('connected');
      
      webSocketService.disconnect();
      expect(webSocketService.getState()).toBe('disconnected');
    });

    it('should manage heartbeat/ping-pong correctly', async () => {
      const onOpen = jest.fn();
      
      webSocketService.connect(mockUrl, {
        onOpen,
        onMessage: jest.fn(),
        onError: jest.fn(),
        onClose: jest.fn(),
        heartbeatInterval: 30000,
      });

      await server.connected;
      await new Promise(resolve => setTimeout(resolve, 0));
      
      jest.advanceTimersByTime(30000);
      
      expect(server).toHaveReceivedMessages([
        JSON.stringify({ type: 'auth', token: mockToken }),
        JSON.stringify({ type: 'ping' })
      ]);
      
      jest.useRealTimers();
    });
  });

  describe('Error Handling', () => {
    it('should emit detailed error events', async () => {
      const onError = jest.fn();
      const onOpen = jest.fn();
      
      webSocketService.connect(mockUrl, {
        onOpen,
        onMessage: jest.fn(),
        onError,
        onClose: jest.fn(),
      });

      await server.connected;
      await new Promise(resolve => setTimeout(resolve, 0));
      
      const errorEvent = new Error('WebSocket error');
      server.error(errorEvent);
      
      await new Promise(resolve => setTimeout(resolve, 0));
      
      expect(onError).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'websocket_error',
          error: errorEvent
        })
      );
    });

    it('should handle rate limiting', async () => {
      const onRateLimit = jest.fn();
      const onOpen = jest.fn();
      
      webSocketService.connect(mockUrl, {
        onOpen,
        onMessage: jest.fn(),
        onError: jest.fn(),
        onClose: jest.fn(),
        onRateLimit,
        rateLimit: { messages: 10, window: 1000 }
      });

      await server.connected;
      await new Promise(resolve => setTimeout(resolve, 0));
      
      for (let i = 0; i < 15; i++) {
        webSocketService.send({ type: 'test', id: i });
      }
      
      expect(onRateLimit).toHaveBeenCalled();
    });
  });
});