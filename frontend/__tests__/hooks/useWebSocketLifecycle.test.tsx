import { renderHook, act } from '@testing-library/react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { WebSocketProvider } from '@/contexts/WebSocketContext';
import React from 'react';

// Mock WebSocket
const mockWebSocket = {
  send: jest.fn(),
  close: jest.fn(),
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
  readyState: WebSocket.OPEN,
  url: 'ws://localhost:8000/ws',
  protocol: '',
  extensions: '',
  bufferedAmount: 0,
  binaryType: 'blob' as BinaryType,
  onopen: null,
  onclose: null,
  onerror: null,
  onmessage: null,
  dispatchEvent: jest.fn(),
  CONNECTING: WebSocket.CONNECTING,
  OPEN: WebSocket.OPEN,
  CLOSING: WebSocket.CLOSING,
  CLOSED: WebSocket.CLOSED
};

// Mock WebSocket constructor
global.WebSocket = jest.fn().mockImplementation(() => mockWebSocket);

describe('useWebSocket Hook Lifecycle', () => {
  let wrapper: React.ComponentType<{ children: React.ReactNode }>;

  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
    
    wrapper = ({ children }) => (
      <WebSocketProvider>{children}</WebSocketProvider>
    );
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  describe('Hook Initialization and Cleanup', () => {
    it('should initialize WebSocket connection on mount', () => {
      const { result } = renderHook(() => useWebSocket(), { wrapper });

      expect(global.WebSocket).toHaveBeenCalled();
      expect(result.current.connectionState).toBe('connecting');
    });

    it('should setup event listeners on mount', () => {
      renderHook(() => useWebSocket(), { wrapper });

      expect(mockWebSocket.addEventListener).toHaveBeenCalledWith('open', expect.any(Function));
      expect(mockWebSocket.addEventListener).toHaveBeenCalledWith('close', expect.any(Function));
      expect(mockWebSocket.addEventListener).toHaveBeenCalledWith('error', expect.any(Function));
      expect(mockWebSocket.addEventListener).toHaveBeenCalledWith('message', expect.any(Function));
    });

    it('should cleanup WebSocket connection on unmount', () => {
      const { unmount } = renderHook(() => useWebSocket(), { wrapper });

      unmount();

      expect(mockWebSocket.close).toHaveBeenCalled();
      expect(mockWebSocket.removeEventListener).toHaveBeenCalledWith('open', expect.any(Function));
      expect(mockWebSocket.removeEventListener).toHaveBeenCalledWith('close', expect.any(Function));
      expect(mockWebSocket.removeEventListener).toHaveBeenCalledWith('error', expect.any(Function));
      expect(mockWebSocket.removeEventListener).toHaveBeenCalledWith('message', expect.any(Function));
    });

    it('should cleanup timers on unmount', () => {
      const clearTimeoutSpy = jest.spyOn(global, 'clearTimeout');
      const clearIntervalSpy = jest.spyOn(global, 'clearInterval');

      const { unmount } = renderHook(() => useWebSocket(), { wrapper });

      // Setup some timers (heartbeat, reconnection, etc.)
      act(() => {
        jest.advanceTimersByTime(1000);
      });

      unmount();

      expect(clearTimeoutSpy).toHaveBeenCalled();
      expect(clearIntervalSpy).toHaveBeenCalled();

      clearTimeoutSpy.mockRestore();
      clearIntervalSpy.mockRestore();
    });

    it('should handle multiple hook instances sharing the same connection', () => {
      const { result: result1 } = renderHook(() => useWebSocket(), { wrapper });
      const { result: result2 } = renderHook(() => useWebSocket(), { wrapper });

      // Both hooks should share the same connection state
      expect(result1.current.connectionState).toBe(result2.current.connectionState);
      expect(result1.current.isConnected).toBe(result2.current.isConnected);

      // Should not create multiple WebSocket instances
      expect(global.WebSocket).toHaveBeenCalledTimes(1);
    });

    it('should handle rapid mount/unmount cycles', () => {
      const connections: any[] = [];

      // Mount and unmount multiple times rapidly
      for (let i = 0; i < 5; i++) {
        const { unmount } = renderHook(() => useWebSocket(), { wrapper });
        connections.push(unmount);
        
        // Unmount immediately
        unmount();
      }

      // Should handle cleanup gracefully without errors
      expect(mockWebSocket.close).toHaveBeenCalledTimes(5);
    });

    it('should preserve connection across component re-renders', () => {
      let renderCount = 0;
      const { result, rerender } = renderHook(() => {
        renderCount++;
        return useWebSocket();
      }, { wrapper });

      const initialConnectionState = result.current.connectionState;

      // Force re-render
      rerender();

      expect(renderCount).toBe(2);
      expect(result.current.connectionState).toBe(initialConnectionState);
      
      // Should not create new WebSocket connection
      expect(global.WebSocket).toHaveBeenCalledTimes(1);
    });

    it('should cleanup abandoned connections', async () => {
      const { unmount } = renderHook(() => useWebSocket(), { wrapper });

      // Simulate connection being abandoned
      unmount();

      // Wait for cleanup timeout
      act(() => {
        jest.advanceTimersByTime(5000);
      });

      expect(mockWebSocket.close).toHaveBeenCalled();
    });
  });

  describe('Connection State Management', () => {
    it('should update state on connection open', () => {
      const { result } = renderHook(() => useWebSocket(), { wrapper });

      // Simulate WebSocket open event
      act(() => {
        const openHandler = mockWebSocket.addEventListener.mock.calls
          .find(call => call[0] === 'open')[1];
        openHandler(new Event('open'));
      });

      expect(result.current.isConnected).toBe(true);
      expect(result.current.connectionState).toBe('connected');
      expect(result.current.error).toBeNull();
    });

    it('should update state on connection close', () => {
      const { result } = renderHook(() => useWebSocket(), { wrapper });

      // First open the connection
      act(() => {
        const openHandler = mockWebSocket.addEventListener.mock.calls
          .find(call => call[0] === 'open')[1];
        openHandler(new Event('open'));
      });

      // Then close it
      act(() => {
        const closeHandler = mockWebSocket.addEventListener.mock.calls
          .find(call => call[0] === 'close')[1];
        closeHandler(new CloseEvent('close', { code: 1000, reason: 'Normal closure' }));
      });

      expect(result.current.isConnected).toBe(false);
      expect(result.current.connectionState).toBe('disconnected');
    });

    it('should handle connection errors', () => {
      const { result } = renderHook(() => useWebSocket(), { wrapper });

      act(() => {
        const errorHandler = mockWebSocket.addEventListener.mock.calls
          .find(call => call[0] === 'error')[1];
        errorHandler(new ErrorEvent('error', { error: new Error('Connection failed') }));
      });

      expect(result.current.isConnected).toBe(false);
      expect(result.current.connectionState).toBe('error');
      expect(result.current.error).toEqual(expect.any(Error));
    });

    it('should track reconnection attempts', () => {
      const { result } = renderHook(() => useWebSocket(), { wrapper });

      // Simulate connection error triggering reconnection
      act(() => {
        const errorHandler = mockWebSocket.addEventListener.mock.calls
          .find(call => call[0] === 'error')[1];
        errorHandler(new ErrorEvent('error'));
      });

      expect(result.current.reconnectAttempts).toBe(1);
      expect(result.current.connectionState).toBe('reconnecting');

      // Simulate another failed reconnection
      act(() => {
        jest.advanceTimersByTime(2000); // Reconnection delay
        const errorHandler = mockWebSocket.addEventListener.mock.calls
          .find(call => call[0] === 'error')[1];
        errorHandler(new ErrorEvent('error'));
      });

      expect(result.current.reconnectAttempts).toBe(2);
    });

    it('should reset reconnection attempts on successful connection', () => {
      const { result } = renderHook(() => useWebSocket(), { wrapper });

      // First, trigger some failed reconnections
      act(() => {
        const errorHandler = mockWebSocket.addEventListener.mock.calls
          .find(call => call[0] === 'error')[1];
        errorHandler(new ErrorEvent('error'));
      });

      expect(result.current.reconnectAttempts).toBe(1);

      // Then successfully connect
      act(() => {
        const openHandler = mockWebSocket.addEventListener.mock.calls
          .find(call => call[0] === 'open')[1];
        openHandler(new Event('open'));
      });

      expect(result.current.reconnectAttempts).toBe(0);
      expect(result.current.connectionState).toBe('connected');
    });

    it('should handle concurrent state changes', () => {
      const { result } = renderHook(() => useWebSocket(), { wrapper });

      // Simulate rapid state changes
      act(() => {
        const openHandler = mockWebSocket.addEventListener.mock.calls
          .find(call => call[0] === 'open')[1];
        const closeHandler = mockWebSocket.addEventListener.mock.calls
          .find(call => call[0] === 'close')[1];
        
        // Fire events rapidly
        openHandler(new Event('open'));
        closeHandler(new CloseEvent('close'));
        openHandler(new Event('open'));
      });

      // Should end up in final state
      expect(result.current.isConnected).toBe(true);
      expect(result.current.connectionState).toBe('connected');
    });

    it('should debounce rapid state changes', () => {
      const { result } = renderHook(() => useWebSocket(), { wrapper });
      const stateChanges: string[] = [];

      // Track state changes
      result.current.onConnectionStateChange?.((state) => {
        stateChanges.push(state);
      });

      act(() => {
        const openHandler = mockWebSocket.addEventListener.mock.calls
          .find(call => call[0] === 'open')[1];
        
        // Fire multiple open events rapidly
        for (let i = 0; i < 10; i++) {
          openHandler(new Event('open'));
        }
      });

      // Should debounce to prevent excessive updates
      expect(stateChanges.length).toBeLessThan(10);
    });
  });

  describe('Message Handling and Lifecycle', () => {
    it('should handle incoming messages', () => {
      const { result } = renderHook(() => useWebSocket(), { wrapper });
      const receivedMessages: any[] = [];

      // Set up message handler
      result.current.onMessage?.((message) => {
        receivedMessages.push(message);
      });

      // Simulate receiving a message
      act(() => {
        const messageHandler = mockWebSocket.addEventListener.mock.calls
          .find(call => call[0] === 'message')[1];
        
        const messageData = { type: 'test', payload: { data: 'test message' } };
        messageHandler(new MessageEvent('message', { 
          data: JSON.stringify(messageData) 
        }));
      });

      expect(receivedMessages).toHaveLength(1);
      expect(receivedMessages[0]).toEqual({ type: 'test', payload: { data: 'test message' } });
      expect(result.current.lastMessage).toEqual({ type: 'test', payload: { data: 'test message' } });
    });

    it('should queue messages while disconnected', () => {
      const { result } = renderHook(() => useWebSocket(), { wrapper });

      // Send message while disconnected
      const message = { type: 'test', payload: { data: 'queued message' } };
      result.current.sendMessage(message);

      expect(result.current.messageQueue).toContain(message);
      expect(mockWebSocket.send).not.toHaveBeenCalled();
    });

    it('should send queued messages after reconnection', () => {
      const { result } = renderHook(() => useWebSocket(), { wrapper });

      // Queue messages while disconnected
      const message1 = { type: 'test1', payload: {} };
      const message2 = { type: 'test2', payload: {} };
      
      result.current.sendMessage(message1);
      result.current.sendMessage(message2);

      // Connect
      act(() => {
        const openHandler = mockWebSocket.addEventListener.mock.calls
          .find(call => call[0] === 'open')[1];
        openHandler(new Event('open'));
      });

      // Should send queued messages
      expect(mockWebSocket.send).toHaveBeenCalledWith(JSON.stringify(message1));
      expect(mockWebSocket.send).toHaveBeenCalledWith(JSON.stringify(message2));
      expect(result.current.messageQueue).toHaveLength(0);
    });

    it('should handle message sending errors', () => {
      const { result } = renderHook(() => useWebSocket(), { wrapper });
      
      // Connect first
      act(() => {
        const openHandler = mockWebSocket.addEventListener.mock.calls
          .find(call => call[0] === 'open')[1];
        openHandler(new Event('open'));
      });

      // Mock send to throw error
      mockWebSocket.send.mockImplementationOnce(() => {
        throw new Error('Send failed');
      });

      const message = { type: 'test', payload: {} };
      
      act(() => {
        result.current.sendMessage(message);
      });

      expect(result.current.error).toEqual(expect.any(Error));
    });

    it('should limit message queue size', () => {
      const { result } = renderHook(() => useWebSocket(), { wrapper });

      // Send many messages while disconnected
      for (let i = 0; i < 1000; i++) {
        result.current.sendMessage({ type: 'test', payload: { index: i } });
      }

      // Queue should be limited to prevent memory issues
      expect(result.current.messageQueue.length).toBeLessThanOrEqual(100);
    });

    it('should clear message queue on explicit disconnect', () => {
      const { result } = renderHook(() => useWebSocket(), { wrapper });

      // Queue some messages
      result.current.sendMessage({ type: 'test1', payload: {} });
      result.current.sendMessage({ type: 'test2', payload: {} });

      expect(result.current.messageQueue).toHaveLength(2);

      // Explicitly disconnect
      act(() => {
        result.current.disconnect();
      });

      expect(result.current.messageQueue).toHaveLength(0);
    });
  });

  describe('Reconnection Logic and Timing', () => {
    it('should implement exponential backoff for reconnections', () => {
      const { result } = renderHook(() => useWebSocket(), { wrapper });
      const reconnectionDelays: number[] = [];

      // Mock setTimeout to capture delays
      const originalSetTimeout = global.setTimeout;
      global.setTimeout = jest.fn((callback, delay) => {
        reconnectionDelays.push(delay);
        return originalSetTimeout(callback, 0);
      }) as any;

      // Trigger multiple reconnection attempts
      for (let i = 0; i < 4; i++) {
        act(() => {
          const errorHandler = mockWebSocket.addEventListener.mock.calls
            .find(call => call[0] === 'error')[1];
          errorHandler(new ErrorEvent('error'));
          jest.advanceTimersByTime(1000);
        });
      }

      global.setTimeout = originalSetTimeout;

      // Should show exponential backoff pattern
      expect(reconnectionDelays[0]).toBe(1000);  // 1 second
      expect(reconnectionDelays[1]).toBe(2000);  // 2 seconds
      expect(reconnectionDelays[2]).toBe(4000);  // 4 seconds
      expect(reconnectionDelays[3]).toBe(8000);  // 8 seconds
    });

    it('should stop reconnection after max attempts', () => {
      const { result } = renderHook(() => useWebSocket(), { wrapper });

      // Trigger many failed reconnections
      for (let i = 0; i < 10; i++) {
        act(() => {
          const errorHandler = mockWebSocket.addEventListener.mock.calls
            .find(call => call[0] === 'error')[1];
          errorHandler(new ErrorEvent('error'));
          jest.advanceTimersByTime(1000);
        });
      }

      // Should stop at max attempts (e.g., 5)
      expect(result.current.reconnectAttempts).toBeLessThanOrEqual(5);
      expect(result.current.connectionState).toBe('failed');
    });

    it('should allow manual reconnection', () => {
      const { result } = renderHook(() => useWebSocket(), { wrapper });

      // Disconnect
      act(() => {
        result.current.disconnect();
      });

      expect(result.current.connectionState).toBe('disconnected');

      // Manually reconnect
      act(() => {
        result.current.connect();
      });

      expect(result.current.connectionState).toBe('connecting');
      expect(global.WebSocket).toHaveBeenCalledTimes(2);
    });

    it('should handle network status changes', () => {
      const { result } = renderHook(() => useWebSocket(), { wrapper });

      // Mock navigator.onLine
      Object.defineProperty(navigator, 'onLine', {
        writable: true,
        value: false
      });

      // Simulate going offline
      act(() => {
        window.dispatchEvent(new Event('offline'));
      });

      expect(result.current.connectionState).toBe('offline');

      // Come back online
      Object.defineProperty(navigator, 'onLine', { value: true });
      
      act(() => {
        window.dispatchEvent(new Event('online'));
      });

      expect(result.current.connectionState).toBe('connecting');
    });

    it('should pause reconnection while page is hidden', () => {
      const { result } = renderHook(() => useWebSocket(), { wrapper });

      // Mock document.hidden
      Object.defineProperty(document, 'hidden', {
        writable: true,
        value: true
      });

      // Trigger error while page is hidden
      act(() => {
        const errorHandler = mockWebSocket.addEventListener.mock.calls
          .find(call => call[0] === 'error')[1];
        errorHandler(new ErrorEvent('error'));
        
        window.dispatchEvent(new Event('visibilitychange'));
        jest.advanceTimersByTime(5000);
      });

      // Should not attempt reconnection while hidden
      expect(result.current.connectionState).toBe('paused');

      // Resume when page becomes visible
      Object.defineProperty(document, 'hidden', { value: false });
      
      act(() => {
        window.dispatchEvent(new Event('visibilitychange'));
        jest.advanceTimersByTime(1000);
      });

      expect(result.current.connectionState).toBe('connecting');
    });
  });

  describe('Memory Management and Performance', () => {
    it('should cleanup event listeners properly', () => {
      const { unmount } = renderHook(() => useWebSocket(), { wrapper });
      
      const removeEventListenerSpy = jest.spyOn(mockWebSocket, 'removeEventListener');

      unmount();

      expect(removeEventListenerSpy).toHaveBeenCalledWith('open', expect.any(Function));
      expect(removeEventListenerSpy).toHaveBeenCalledWith('close', expect.any(Function));
      expect(removeEventListenerSpy).toHaveBeenCalledWith('error', expect.any(Function));
      expect(removeEventListenerSpy).toHaveBeenCalledWith('message', expect.any(Function));
    });

    it('should prevent memory leaks with message handlers', () => {
      const { result, unmount } = renderHook(() => useWebSocket(), { wrapper });

      const handlers: Function[] = [];

      // Add multiple message handlers
      for (let i = 0; i < 100; i++) {
        const handler = jest.fn();
        handlers.push(handler);
        result.current.onMessage?.(handler);
      }

      unmount();

      // Handlers should be cleaned up
      expect(result.current.onMessage).toBeUndefined();
    });

    it('should throttle rapid reconnection attempts', () => {
      const { result } = renderHook(() => useWebSocket(), { wrapper });
      
      // Rapidly trigger errors
      act(() => {
        for (let i = 0; i < 20; i++) {
          const errorHandler = mockWebSocket.addEventListener.mock.calls
            .find(call => call[0] === 'error')[1];
          errorHandler(new ErrorEvent('error'));
        }
      });

      // Should throttle reconnection attempts
      expect(result.current.reconnectAttempts).toBeLessThan(20);
    });

    it('should limit message history to prevent memory growth', () => {
      const { result } = renderHook(() => useWebSocket(), { wrapper });

      // Send many messages
      act(() => {
        const messageHandler = mockWebSocket.addEventListener.mock.calls
          .find(call => call[0] === 'message')[1];
        
        for (let i = 0; i < 1000; i++) {
          messageHandler(new MessageEvent('message', { 
            data: JSON.stringify({ type: 'test', payload: { index: i } })
          }));
        }
      });

      // Message history should be limited
      expect(result.current.messageHistory?.length || 0).toBeLessThanOrEqual(100);
    });

    it('should handle component unmount during async operations', async () => {
      const { result, unmount } = renderHook(() => useWebSocket(), { wrapper });

      // Start async operation
      const connectPromise = result.current.connect();

      // Unmount before operation completes
      unmount();

      // Should handle gracefully without errors
      await expect(connectPromise).resolves.toBeUndefined();
    });

    it('should debounce state updates for performance', () => {
      const { result } = renderHook(() => useWebSocket(), { wrapper });
      const stateUpdates: string[] = [];

      result.current.onConnectionStateChange?.((state) => {
        stateUpdates.push(state);
      });

      // Fire many rapid state changes
      act(() => {
        for (let i = 0; i < 100; i++) {
          const openHandler = mockWebSocket.addEventListener.mock.calls
            .find(call => call[0] === 'open')[1];
          openHandler(new Event('open'));
        }
      });

      // Should debounce updates
      expect(stateUpdates.length).toBeLessThan(100);
    });

    it('should cleanup resources when WebSocket becomes stale', () => {
      const { result } = renderHook(() => useWebSocket(), { wrapper });

      // Simulate stale connection detection
      act(() => {
        jest.advanceTimersByTime(300000); // 5 minutes of inactivity
      });

      // Should cleanup and reconnect
      expect(mockWebSocket.close).toHaveBeenCalled();
      expect(result.current.connectionState).toBe('reconnecting');
    });
  });

  describe('Error Handling and Edge Cases', () => {
    it('should handle WebSocket constructor failures', () => {
      // Mock WebSocket constructor to throw
      global.WebSocket = jest.fn().mockImplementation(() => {
        throw new Error('WebSocket not supported');
      });

      const { result } = renderHook(() => useWebSocket(), { wrapper });

      expect(result.current.connectionState).toBe('error');
      expect(result.current.error?.message).toBe('WebSocket not supported');
    });

    it('should handle invalid message formats gracefully', () => {
      const { result } = renderHook(() => useWebSocket(), { wrapper });

      act(() => {
        const messageHandler = mockWebSocket.addEventListener.mock.calls
          .find(call => call[0] === 'message')[1];
        
        // Send invalid JSON
        messageHandler(new MessageEvent('message', { data: 'invalid json' }));
      });

      expect(result.current.error).toEqual(expect.any(Error));
      expect(result.current.lastMessage).toBeNull();
    });

    it('should handle connection timeouts', () => {
      const { result } = renderHook(() => useWebSocket(), { wrapper });

      // Simulate connection timeout
      act(() => {
        jest.advanceTimersByTime(30000); // 30 second timeout
      });

      expect(result.current.connectionState).toBe('timeout');
    });

    it('should handle browser-specific WebSocket limitations', () => {
      // Mock old browser without WebSocket support
      const originalWebSocket = global.WebSocket;
      (global as any).WebSocket = undefined;

      const { result } = renderHook(() => useWebSocket(), { wrapper });

      expect(result.current.connectionState).toBe('unsupported');

      // Restore WebSocket
      global.WebSocket = originalWebSocket;
    });

    it('should handle concurrent hook instances gracefully', () => {
      // Create multiple hook instances
      const hooks = Array.from({ length: 5 }, () => 
        renderHook(() => useWebSocket(), { wrapper })
      );

      // All should share the same connection state
      const firstState = hooks[0].result.current.connectionState;
      hooks.forEach(({ result }) => {
        expect(result.current.connectionState).toBe(firstState);
      });

      // Cleanup all hooks
      hooks.forEach(({ unmount }) => unmount());

      // Should cleanup connection properly
      expect(mockWebSocket.close).toHaveBeenCalledTimes(5);
    });
  });
});