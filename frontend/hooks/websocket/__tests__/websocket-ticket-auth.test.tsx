import { renderHook, act, waitFor } from '@testing-library/react';
import { ReactNode } from 'react';
import { TicketAuthProvider } from '../../../auth/providers/ticket-auth-provider';
import { useWebSocketTicketAuth } from '../use-websocket-ticket-auth';

// Mock WebSocket
const mockWebSocket = {
  send: jest.fn(),
  close: jest.fn(),
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
  readyState: WebSocket.OPEN,
  CONNECTING: WebSocket.CONNECTING,
  OPEN: WebSocket.OPEN,
  CLOSING: WebSocket.CLOSING,
  CLOSED: WebSocket.CLOSED,
  url: '',
  protocol: '',
  extensions: '',
  bufferedAmount: 0,
  binaryType: 'blob' as BinaryType,
  onopen: null,
  onclose: null,
  onmessage: null,
  onerror: null,
  dispatchEvent: jest.fn()
};

const MockedWebSocket = jest.fn(() => mockWebSocket);
(global as any).WebSocket = MockedWebSocket;

// Mock fetch for ticket operations
const mockFetch = jest.fn();
global.fetch = mockFetch;

describe('useWebSocketTicketAuth', () => {
  const defaultConfig = {
    websocketUrl: 'ws://localhost:8000/ws',
    userId: 'test-user-123',
    autoConnect: false, // Disable for testing
    reconnectAttempts: 2,
    reconnectDelay: 100
  };

  const wrapper = ({ children }: { children: ReactNode }) => (
    <TicketAuthProvider apiBaseUrl="http://localhost:8000" enableAutoRefresh={false}>
      {children}
    </TicketAuthProvider>
  );

  beforeEach(() => {
    jest.clearAllMocks();
    jest.clearAllTimers();
    jest.useFakeTimers();
    MockedWebSocket.mockClear();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  describe('initialization', () => {
    it('should initialize with correct default state', () => {
      const { result } = renderHook(
        () => useWebSocketTicketAuth(defaultConfig),
        { wrapper }
      );

      expect(result.current.state).toEqual({
        isConnected: false,
        isConnecting: false,
        error: null,
        lastConnectTime: null,
        connectionAttempts: 0,
        currentTicket: null
      });
    });

    it('should auto-connect when enabled', async () => {
      const mockTicketData = {
        ticketId: 'test-ticket-123',
        userId: 'test-user-123',
        expires: '2024-12-31T23:59:59Z',
        permissions: ['websocket']
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTicketData
      });

      const autoConnectConfig = { ...defaultConfig, autoConnect: true };

      const { result } = renderHook(
        () => useWebSocketTicketAuth(autoConnectConfig),
        { wrapper }
      );

      await waitFor(() => {
        expect(MockedWebSocket).toHaveBeenCalled();
      });

      expect(result.current.state.isConnecting).toBe(true);
    });
  });

  describe('connect', () => {
    it('should successfully connect with valid ticket', async () => {
      const mockTicketData = {
        ticketId: 'test-ticket-123',
        userId: 'test-user-123',
        expires: '2024-12-31T23:59:59Z',
        permissions: ['websocket']
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTicketData
      });

      const { result } = renderHook(
        () => useWebSocketTicketAuth(defaultConfig),
        { wrapper }
      );

      let connectResult = false;

      await act(async () => {
        connectResult = await result.current.connect();
      });

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/auth/tickets/generate',
        expect.any(Object)
      );

      expect(MockedWebSocket).toHaveBeenCalledWith(
        'ws://localhost:8000/ws?ticket=test-ticket-123&userId=test-user-123'
      );

      // Simulate WebSocket open event
      act(() => {
        if (mockWebSocket.onopen) {
          mockWebSocket.onopen({} as Event);
        }
      });

      expect(result.current.state.isConnecting).toBe(false);
      expect(result.current.state.isConnected).toBe(true);
      expect(result.current.state.error).toBeNull();
    });

    it('should handle ticket generation failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error'
      });

      const { result } = renderHook(
        () => useWebSocketTicketAuth(defaultConfig),
        { wrapper }
      );

      let connectResult = true;

      await act(async () => {
        connectResult = await result.current.connect();
      });

      expect(connectResult).toBe(false);
      expect(result.current.state.error).toBe('Unable to obtain valid authentication ticket');
      expect(MockedWebSocket).not.toHaveBeenCalled();
    });

    it('should handle WebSocket connection failure', async () => {
      const mockTicketData = {
        ticketId: 'test-ticket-123',
        userId: 'test-user-123',
        expires: '2024-12-31T23:59:59Z',
        permissions: ['websocket']
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTicketData
      });

      const { result } = renderHook(
        () => useWebSocketTicketAuth(defaultConfig),
        { wrapper }
      );

      let connectResult = true;

      await act(async () => {
        connectResult = await result.current.connect();
      });

      // Simulate WebSocket error
      act(() => {
        if (mockWebSocket.onerror) {
          mockWebSocket.onerror({} as Event);
        }
      });

      expect(connectResult).toBe(false);
      expect(result.current.state.error).toBe('WebSocket connection error');
      expect(result.current.state.isConnected).toBe(false);
    });

    it('should not connect if already connected', async () => {
      const { result } = renderHook(
        () => useWebSocketTicketAuth(defaultConfig),
        { wrapper }
      );

      // Manually set connected state
      act(() => {
        (result.current as any).updateState({ isConnected: true });
      });

      const connectResult = await act(async () => {
        return await result.current.connect();
      });

      expect(connectResult).toBe(true);
      expect(MockedWebSocket).not.toHaveBeenCalled();
    });

    it('should not connect if currently connecting', async () => {
      const { result } = renderHook(
        () => useWebSocketTicketAuth(defaultConfig),
        { wrapper }
      );

      // Manually set connecting state
      act(() => {
        (result.current as any).updateState({ isConnecting: true });
      });

      const connectResult = await act(async () => {
        return await result.current.connect();
      });

      expect(connectResult).toBe(false);
      expect(MockedWebSocket).not.toHaveBeenCalled();
    });
  });

  describe('disconnect', () => {
    it('should disconnect active WebSocket', () => {
      const { result } = renderHook(
        () => useWebSocketTicketAuth(defaultConfig),
        { wrapper }
      );

      // Manually set up connected state with WebSocket ref
      act(() => {
        (result.current as any).wsRef.current = mockWebSocket;
        (result.current as any).updateState({ isConnected: true });
      });

      act(() => {
        result.current.disconnect();
      });

      expect(mockWebSocket.close).toHaveBeenCalledWith(1000, 'User requested disconnect');
      expect(result.current.state.isConnected).toBe(false);
      expect(result.current.state.isConnecting).toBe(false);
      expect(result.current.state.connectionAttempts).toBe(0);
    });

    it('should handle disconnect when not connected', () => {
      const { result } = renderHook(
        () => useWebSocketTicketAuth(defaultConfig),
        { wrapper }
      );

      act(() => {
        result.current.disconnect();
      });

      expect(mockWebSocket.close).not.toHaveBeenCalled();
      expect(result.current.state.isConnected).toBe(false);
    });
  });

  describe('sendMessage', () => {
    it('should send message when connected', () => {
      const { result } = renderHook(
        () => useWebSocketTicketAuth(defaultConfig),
        { wrapper }
      );

      // Set up connected WebSocket
      act(() => {
        (result.current as any).wsRef.current = mockWebSocket;
        (result.current as any).updateState({ isConnected: true });
      });

      const message = { type: 'test', data: 'hello' };
      let sendResult = false;

      act(() => {
        sendResult = result.current.sendMessage(message);
      });

      expect(sendResult).toBe(true);
      expect(mockWebSocket.send).toHaveBeenCalledWith(JSON.stringify(message));
      expect(result.current.state.error).toBeNull();
    });

    it('should handle send when not connected', () => {
      const { result } = renderHook(
        () => useWebSocketTicketAuth(defaultConfig),
        { wrapper }
      );

      const message = { type: 'test', data: 'hello' };
      let sendResult = true;

      act(() => {
        sendResult = result.current.sendMessage(message);
      });

      expect(sendResult).toBe(false);
      expect(result.current.state.error).toBe('WebSocket is not connected');
      expect(mockWebSocket.send).not.toHaveBeenCalled();
    });

    it('should send string messages directly', () => {
      const { result } = renderHook(
        () => useWebSocketTicketAuth(defaultConfig),
        { wrapper }
      );

      // Set up connected WebSocket
      act(() => {
        (result.current as any).wsRef.current = mockWebSocket;
        (result.current as any).updateState({ isConnected: true });
      });

      const message = 'plain text message';
      let sendResult = false;

      act(() => {
        sendResult = result.current.sendMessage(message);
      });

      expect(sendResult).toBe(true);
      expect(mockWebSocket.send).toHaveBeenCalledWith(message);
    });

    it('should handle send errors', () => {
      const { result } = renderHook(
        () => useWebSocketTicketAuth(defaultConfig),
        { wrapper }
      );

      // Set up WebSocket that throws on send
      const errorWebSocket = {
        ...mockWebSocket,
        send: jest.fn(() => { throw new Error('Send failed'); })
      };

      act(() => {
        (result.current as any).wsRef.current = errorWebSocket;
        (result.current as any).updateState({ isConnected: true });
      });

      const message = { type: 'test' };
      let sendResult = true;

      act(() => {
        sendResult = result.current.sendMessage(message);
      });

      expect(sendResult).toBe(false);
      expect(result.current.state.error).toBe('Send failed');
    });
  });

  describe('event handlers', () => {
    it('should register and unregister message handlers', () => {
      const { result } = renderHook(
        () => useWebSocketTicketAuth(defaultConfig),
        { wrapper }
      );

      const messageHandler = jest.fn();
      let unregister: (() => void) | undefined;

      act(() => {
        unregister = result.current.onMessage(messageHandler);
      });

      // Simulate WebSocket message
      act(() => {
        if (mockWebSocket.onmessage) {
          mockWebSocket.onmessage({
            data: JSON.stringify({ type: 'test', message: 'hello' })
          } as MessageEvent);
        }
      });

      expect(messageHandler).toHaveBeenCalledWith({
        type: 'test',
        message: 'hello'
      });

      // Unregister handler
      act(() => {
        if (unregister) unregister();
      });

      // Message should not be handled after unregistering
      act(() => {
        if (mockWebSocket.onmessage) {
          mockWebSocket.onmessage({
            data: JSON.stringify({ type: 'test2', message: 'world' })
          } as MessageEvent);
        }
      });

      expect(messageHandler).toHaveBeenCalledTimes(1);
    });

    it('should handle malformed JSON messages', () => {
      const { result } = renderHook(
        () => useWebSocketTicketAuth(defaultConfig),
        { wrapper }
      );

      const messageHandler = jest.fn();

      act(() => {
        result.current.onMessage(messageHandler);
      });

      // Simulate malformed JSON message
      act(() => {
        if (mockWebSocket.onmessage) {
          mockWebSocket.onmessage({
            data: 'invalid json {'
          } as MessageEvent);
        }
      });

      expect(messageHandler).toHaveBeenCalledWith({
        type: 'raw',
        data: 'invalid json {'
      });
    });

    it('should register connect/disconnect/error handlers', () => {
      const { result } = renderHook(
        () => useWebSocketTicketAuth(defaultConfig),
        { wrapper }
      );

      const connectHandler = jest.fn();
      const disconnectHandler = jest.fn();
      const errorHandler = jest.fn();

      act(() => {
        result.current.onConnect(connectHandler);
        result.current.onDisconnect(disconnectHandler);
        result.current.onError(errorHandler);
      });

      // Simulate events
      act(() => {
        if (mockWebSocket.onopen) mockWebSocket.onopen({} as Event);
        if (mockWebSocket.onclose) mockWebSocket.onclose({ reason: 'test close' } as CloseEvent);
        if (mockWebSocket.onerror) mockWebSocket.onerror({} as Event);
      });

      expect(connectHandler).toHaveBeenCalled();
      expect(disconnectHandler).toHaveBeenCalledWith('test close');
      expect(errorHandler).toHaveBeenCalledWith('WebSocket connection error');
    });
  });

  describe('reconnect', () => {
    it('should disconnect and reconnect', async () => {
      const mockTicketData = {
        ticketId: 'test-ticket-123',
        userId: 'test-user-123',
        expires: '2024-12-31T23:59:59Z',
        permissions: ['websocket']
      };

      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => mockTicketData
      });

      const { result } = renderHook(
        () => useWebSocketTicketAuth(defaultConfig),
        { wrapper }
      );

      // Set up connected state
      act(() => {
        (result.current as any).wsRef.current = mockWebSocket;
        (result.current as any).updateState({ isConnected: true });
      });

      let reconnectResult = false;

      await act(async () => {
        reconnectResult = await result.current.reconnect();
      });

      expect(mockWebSocket.close).toHaveBeenCalled();
      expect(MockedWebSocket).toHaveBeenCalledTimes(2); // Initial + reconnect
    });
  });

  describe('ticket refresh integration', () => {
    it('should refresh ticket and reconnect', async () => {
      const oldTicket = {
        ticketId: 'old-ticket-123',
        userId: 'test-user-123',
        expires: new Date(Date.now() + 30000), // 30 seconds
        permissions: ['websocket']
      };

      const refreshedTicket = {
        ticketId: 'refreshed-ticket-123',
        userId: 'test-user-123',
        expires: '2024-12-31T23:59:59Z',
        permissions: ['websocket']
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => refreshedTicket
      });

      const { result } = renderHook(
        () => useWebSocketTicketAuth(defaultConfig),
        { wrapper }
      );

      // Set current ticket
      act(() => {
        (result.current as any).updateState({ currentTicket: oldTicket });
      });

      let refreshResult = false;

      await act(async () => {
        refreshResult = await result.current.refreshTicketAndReconnect();
      });

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/auth/tickets/refresh',
        expect.any(Object)
      );

      expect(result.current.state.currentTicket?.ticketId).toBe('refreshed-ticket-123');
    });

    it('should generate new ticket if refresh fails', async () => {
      const oldTicket = {
        ticketId: 'old-ticket-123',
        userId: 'test-user-123',
        expires: new Date(Date.now() + 30000),
        permissions: ['websocket']
      };

      const newTicket = {
        ticketId: 'new-ticket-123',
        userId: 'test-user-123',
        expires: '2024-12-31T23:59:59Z',
        permissions: ['websocket']
      };

      // Mock refresh failure, then generation success
      mockFetch
        .mockResolvedValueOnce({
          ok: false,
          status: 404,
          statusText: 'Not Found'
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => newTicket
        });

      const { result } = renderHook(
        () => useWebSocketTicketAuth(defaultConfig),
        { wrapper }
      );

      // Set current ticket
      act(() => {
        (result.current as any).updateState({ currentTicket: oldTicket });
      });

      await act(async () => {
        await result.current.refreshTicketAndReconnect();
      });

      expect(mockFetch).toHaveBeenCalledTimes(2); // Refresh attempt + generate
    });
  });

  describe('cleanup', () => {
    it('should clean up on unmount', () => {
      const { result, unmount } = renderHook(
        () => useWebSocketTicketAuth(defaultConfig),
        { wrapper }
      );

      // Set up connected state
      act(() => {
        (result.current as any).wsRef.current = mockWebSocket;
        (result.current as any).updateState({ isConnected: true });
      });

      unmount();

      expect(mockWebSocket.close).toHaveBeenCalled();
    });

    it('should clear error', () => {
      const { result } = renderHook(
        () => useWebSocketTicketAuth(defaultConfig),
        { wrapper }
      );

      // Set error
      act(() => {
        (result.current as any).updateState({ error: 'Test error' });
      });

      expect(result.current.state.error).toBe('Test error');

      act(() => {
        result.current.clearError();
      });

      expect(result.current.state.error).toBeNull();
    });
  });
});