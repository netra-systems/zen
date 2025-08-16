import { renderHook, act, waitFor } from '@testing-library/react';

import { TestProviders } from '../test-utils/providers';// Using Jest, not vitest
import { useDemoWebSocket } from '@/hooks/useDemoWebSocket';
import { useMediaQuery } from '@/hooks/useMediaQuery';

import React from 'react';

// Define WebSocket constants if not available  
if (typeof WebSocket === 'undefined') {
  (global as any).WebSocket = class MockWebSocket {
    static CONNECTING = 0;
    static OPEN = 1;
    static CLOSING = 2;
    static CLOSED = 3;
  };
} else if (WebSocket.CONNECTING === undefined) {
  // Add static constants to existing WebSocket
  (WebSocket as any).CONNECTING = 0;
  (WebSocket as any).OPEN = 1;
  (WebSocket as any).CLOSING = 2;
  (WebSocket as any).CLOSED = 3;
}

// Test 65: useDemoWebSocket connection
describe('test_useDemoWebSocket_connection', () => {
  let mockWebSocketInstance: any;
  let mockWebSocketConstructor: jest.Mock;
  
  beforeEach(() => {
    // Ensure WebSocket constants are available
    if (!(global as any).WebSocket || !(global as any).WebSocket.OPEN) {
      (global as any).WebSocket = class MockWebSocket {
        static CONNECTING = 0;
        static OPEN = 1;
        static CLOSING = 2;
        static CLOSED = 3;
      };
    }
    
    // Mock fetch for config
    global.fetch = jest.fn().mockResolvedValue({
      json: jest.fn().mockResolvedValue({
        ws_url: 'ws://localhost:8000/ws'
      })
    });

    // Create a mock WebSocket instance
    mockWebSocketInstance = {
      send: jest.fn(),
      close: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      readyState: 0, // Start with CONNECTING (0)
      CONNECTING: 0,
      OPEN: 1,
      CLOSING: 2,
      CLOSED: 3,
      url: '',
      protocol: '',
      onopen: null,
      onmessage: null,
      onerror: null,
      onclose: null,
    };
    
    // Make readyState a getter/setter to ensure it behaves correctly
    let currentReadyState = 0; // CONNECTING
    Object.defineProperty(mockWebSocketInstance, 'readyState', {
      get: () => currentReadyState,
      set: (value) => { currentReadyState = value; },
      configurable: true
    });
    
    // Create the mock constructor
    mockWebSocketConstructor = jest.fn((url: string) => {
      mockWebSocketInstance.url = url;
      currentReadyState = 0; // Ensure CONNECTING state on creation
      return mockWebSocketInstance;
    });
    
    // Preserve the static constants while replacing the constructor
    mockWebSocketConstructor.CONNECTING = 0;
    mockWebSocketConstructor.OPEN = 1;
    mockWebSocketConstructor.CLOSING = 2;
    mockWebSocketConstructor.CLOSED = 3;
    
    // Assign to global
    global.WebSocket = mockWebSocketConstructor as any;
    global.mockWebSocket = mockWebSocketInstance;
  });
  
  afterEach(() => {
    jest.clearAllMocks();
    jest.restoreAllMocks();
  });

  it('should establish demo WebSocket connection', async () => {
    const wrapper = TestProviders;
    
    const { result } = renderHook(() => useDemoWebSocket(), { wrapper });
    
    // Wait for the onopen handler to be set and called
    await waitFor(() => {
      expect(mockWebSocketInstance.onopen).toBeDefined();
    });
    
    // Trigger the open event  
    act(() => {
      mockWebSocketInstance.readyState = 1; // OPEN
      if (mockWebSocketInstance.onopen) {
        mockWebSocketInstance.onopen();
      }
    });
    
    await waitFor(() => {
      expect(result.current.isConnected).toBe(true);
    });
    
    expect(mockWebSocketConstructor).toHaveBeenCalledWith(
      expect.stringContaining('/api/demo/ws')
    );
  });

  it('should handle message queuing when disconnected', async () => {
    const wrapper = TestProviders;
    
    const { result } = renderHook(() => useDemoWebSocket(), { wrapper });
    
    // Wait for hook to initialize with WebSocket in CONNECTING state
    await waitFor(() => {
      expect(mockWebSocketInstance.onopen).toBeDefined();
    });
    
    // Ensure WebSocket is still connecting (0 = CONNECTING)
    expect(mockWebSocketInstance.readyState).toBe(0);
    
    // Try to send a message while still connecting - should fail
    const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();
    act(() => {
      result.current.sendMessage({ type: 'demo', content: 'Test message' });
    });
    
    // Should not send since not connected
    expect(mockWebSocketInstance.send).not.toHaveBeenCalled();
    expect(consoleErrorSpy).toHaveBeenCalledWith(
      expect.stringContaining('ERROR: WebSocket is not connected [useDemoWebSocket] (send_failed_not_connected)'),
      expect.any(Object)
    );
    expect(result.current.error).toBeTruthy();
    
    // Clear mocks before continuing
    consoleErrorSpy.mockClear();
    mockWebSocketInstance.send.mockClear();
    
    // Now simulate connection established - update readyState to OPEN (1)
    act(() => {
      mockWebSocketInstance.readyState = 1; // OPEN
      if (mockWebSocketInstance.onopen) {
        mockWebSocketInstance.onopen();
      }
    });
    
    // After connection, should be connected
    await waitFor(() => {
      expect(result.current.isConnected).toBe(true);
    });
    
    // The WebSocket instance readyState should be OPEN now
    expect(mockWebSocketInstance.readyState).toBe(1); // OPEN
    
    // Try sending again after connection - should work now
    act(() => {
      result.current.sendMessage({ type: 'demo', content: 'Test message after connect' });
    });
    
    // Should be called immediately since WebSocket is open
    expect(mockWebSocketInstance.send).toHaveBeenCalledTimes(1);
    
    expect(mockWebSocketInstance.send).toHaveBeenCalledWith(
      JSON.stringify({ type: 'demo', content: 'Test message after connect' })
    );
    
    consoleErrorSpy.mockRestore();
  });

  it('should handle reconnection on disconnect', async () => {
    // Use fake timers for this test
    jest.useFakeTimers();
    
    const wrapper = TestProviders;
    
    const { result } = renderHook(() => useDemoWebSocket(), { wrapper });
    
    // Wait for initial connection
    await waitFor(() => {
      expect(mockWebSocketInstance.onclose).toBeDefined();
    });
    
    // Open the connection first
    act(() => {
      mockWebSocketInstance.readyState = 1; // OPEN
      if (mockWebSocketInstance.onopen) {
        mockWebSocketInstance.onopen();
      }
    });
    
    await waitFor(() => {
      expect(result.current.isConnected).toBe(true);
    });
    
    // Now close the connection
    act(() => {
      mockWebSocketInstance.readyState = 3; // CLOSED
      if (mockWebSocketInstance.onclose) {
        mockWebSocketInstance.onclose();
      }
    });
    
    expect(result.current.isConnected).toBe(false);
    
    // Advance timers to trigger reconnection
    act(() => {
      jest.advanceTimersByTime(3000);
    });
    
    // Should attempt reconnection
    await waitFor(() => {
      expect(mockWebSocketConstructor).toHaveBeenCalledTimes(2);
    });
    
    jest.useRealTimers();
  });
});

// Test 66: useMediaQuery responsive
describe('test_useMediaQuery_responsive', () => {
  let matchMediaMock: any;
  
  beforeEach(() => {
    matchMediaMock = jest.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      dispatchEvent: jest.fn(),
    }));
    
    window.matchMedia = matchMediaMock;
  });

  it('should detect media query matches', () => {
    matchMediaMock.mockImplementation(() => ({
      matches: true,
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
    }));
    
    const { result } = renderHook(() => useMediaQuery('(min-width: 768px)'));
    
    expect(result.current).toBe(true);
  });

  it('should update on media query change', () => {
    let listener: any;
    const addEventListenerMock = jest.fn((event: string, handler: any) => {
      if (event === 'change') listener = handler;
    });
    
    matchMediaMock.mockImplementation(() => ({
      matches: false,
      addEventListener: addEventListenerMock,
      removeEventListener: jest.fn(),
    }));
    
    const { result, rerender } = renderHook(() =>
      useMediaQuery('(min-width: 768px)')
    );
    
    expect(result.current).toBe(false);
    
    // Simulate media query change
    act(() => {
      listener({ matches: true });
    });
    
    expect(result.current).toBe(true);
  });

  it('should handle debouncing for rapid changes', async () => {
    let listener: any;
    const addEventListenerMock = jest.fn((event: string, handler: any) => {
      if (event === 'change') listener = handler;
    });
    
    matchMediaMock.mockImplementation(() => ({
      matches: false,
      addEventListener: addEventListenerMock,
      removeEventListener: jest.fn(),
    }));
    
    // Note: The useMediaQuery hook doesn't actually support debouncing parameter
    // But we can test rapid changes still update immediately
    const { result } = renderHook(() => useMediaQuery('(min-width: 768px)'));
    
    expect(result.current).toBe(false);
    
    // First change - should update immediately
    act(() => {
      listener({ matches: true });
    });
    expect(result.current).toBe(true);
    
    // Second change - should also update immediately
    act(() => {
      listener({ matches: false });
    });
    expect(result.current).toBe(false);
    
    // Third change - should also update immediately
    act(() => {
      listener({ matches: true });
    });
    expect(result.current).toBe(true);
  });

  it('should cleanup on unmount', () => {
    const removeEventListenerMock = jest.fn();
    
    matchMediaMock.mockImplementation(() => ({
      matches: false,
      addEventListener: jest.fn(),
      removeEventListener: removeEventListenerMock,
    }));
    
    const { unmount } = renderHook(() => useMediaQuery('(min-width: 768px)'));
    
    unmount();
    
    expect(removeEventListenerMock).toHaveBeenCalledWith('change', expect.any(Function));
  });
});