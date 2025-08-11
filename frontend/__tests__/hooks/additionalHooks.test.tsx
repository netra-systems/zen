import { renderHook, act, waitFor } from '@testing-library/react';
// Using Jest, not vitest
import { useDemoWebSocket } from '@/hooks/useDemoWebSocket';
import { useMediaQuery } from '@/hooks/useMediaQuery';
import { WebSocketProvider } from '@/contexts/WebSocketContext';
import React from 'react';

// Test 65: useDemoWebSocket connection
describe('test_useDemoWebSocket_connection', () => {
  let mockWebSocket: any;
  
  beforeEach(() => {
    mockWebSocket = {
      send: jest.fn(),
      close: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      readyState: WebSocket.OPEN,
    };
    
    global.WebSocket = vi.fn(() => mockWebSocket) as any;
  });

  it('should establish demo WebSocket connection', async () => {
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <WebSocketProvider>{children}</WebSocketProvider>
    );
    
    const { result } = renderHook(() => useDemoWebSocket(), { wrapper });
    
    await waitFor(() => {
      expect(result.current.isConnected).toBe(true);
    });
    
    expect(global.WebSocket).toHaveBeenCalledWith(
      expect.stringContaining('/ws/demo')
    );
  });

  it('should handle message queuing when disconnected', async () => {
    mockWebSocket.readyState = WebSocket.CONNECTING;
    
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <WebSocketProvider>{children}</WebSocketProvider>
    );
    
    const { result } = renderHook(() => useDemoWebSocket(), { wrapper });
    
    act(() => {
      result.current.sendMessage({ type: 'demo', content: 'Test message' });
    });
    
    expect(mockWebSocket.send).not.toHaveBeenCalled();
    
    // Simulate connection established
    mockWebSocket.readyState = WebSocket.OPEN;
    const openHandler = mockWebSocket.addEventListener.mock.calls.find(
      (call: any[]) => call[0] === 'open'
    )[1];
    
    act(() => {
      openHandler();
    });
    
    await waitFor(() => {
      expect(mockWebSocket.send).toHaveBeenCalledWith(
        JSON.stringify({ type: 'demo', content: 'Test message' })
      );
    });
  });

  it('should handle reconnection on disconnect', async () => {
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <WebSocketProvider>{children}</WebSocketProvider>
    );
    
    const { result } = renderHook(() => useDemoWebSocket(), { wrapper });
    
    const closeHandler = mockWebSocket.addEventListener.mock.calls.find(
      (call: any[]) => call[0] === 'close'
    )[1];
    
    act(() => {
      closeHandler();
    });
    
    expect(result.current.isConnected).toBe(false);
    
    // Should attempt reconnection
    await waitFor(() => {
      expect(global.WebSocket).toHaveBeenCalledTimes(2);
    });
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
    const addEventListenerMock = vi.fn((event: string, handler: any) => {
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
    const addEventListenerMock = vi.fn((event: string, handler: any) => {
      if (event === 'change') listener = handler;
    });
    
    matchMediaMock.mockImplementation(() => ({
      matches: false,
      addEventListener: addEventListenerMock,
      removeEventListener: jest.fn(),
    }));
    
    const { result } = renderHook(() => useMediaQuery('(min-width: 768px)', 100));
    
    // Rapid changes
    act(() => {
      listener({ matches: true });
      listener({ matches: false });
      listener({ matches: true });
    });
    
    // Should not update immediately
    expect(result.current).toBe(false);
    
    // Wait for debounce
    await waitFor(() => {
      expect(result.current).toBe(true);
    }, { timeout: 150 });
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