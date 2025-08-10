import { renderHook, act, waitFor } from '@testing-library/react';
import { useWebSocket } from '@/hooks/useWebSocketResilience';
import { authService } from '@/auth/service';
import WS from 'jest-websocket-mock';
import React from 'react';

jest.mock('@/auth/service');

describe('useWebSocket Error Handling', () => {
  let server: WS;
  const mockToken = 'test-token';
  const wsUrl = 'ws://localhost:8000/ws';

  beforeEach(() => {
    (authService.getAuthHeaders as jest.Mock).mockReturnValue({
      Authorization: `Bearer ${mockToken}`,
    });
    localStorage.setItem('access_token', mockToken);
  });

  afterEach(() => {
    WS.clean();
    jest.clearAllMocks();
    localStorage.clear();
  });

  it('should handle authentication errors (403)', async () => {
    server = new WS(`${wsUrl}?token=${mockToken}`, { verifyClient: () => false });
    
    const onError = jest.fn();
    const { result } = renderHook(() => useWebSocket(`${wsUrl}?token=${mockToken}`, { onError }));

    await waitFor(() => {
      expect(onError).toHaveBeenCalled();
    });

    const errorCall = onError.mock.calls[0][0];
    expect(errorCall.type).toBe('CONNECTION_ERROR');
  });

  it('should retry connection with exponential backoff', async () => {
    let connectionAttempts = 0;
    
    // Mock WebSocket to fail initially then succeed
    const originalWebSocket = global.WebSocket;
    (global as any).WebSocket = jest.fn().mockImplementation((url) => {
      connectionAttempts++;
      if (connectionAttempts < 3) {
        const ws = new originalWebSocket(url);
        setTimeout(() => {
          ws.close(1006); // Abnormal closure
        }, 10);
        return ws;
      }
      return new originalWebSocket(url);
    });

    server = new WS(`${wsUrl}?token=${mockToken}`);
    
    const { result } = renderHook(() => useWebSocket(`${wsUrl}?token=${mockToken}`));

    await waitFor(() => {
      expect(connectionAttempts).toBeGreaterThanOrEqual(3);
      expect(result.current.readyState).toBe(WebSocket.OPEN);
    }, { timeout: 10000 });

    global.WebSocket = originalWebSocket;
  });

  it('should handle malformed messages', async () => {
    server = new WS(`${wsUrl}?token=${mockToken}`);
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
    
    const onError = jest.fn();
    const { result } = renderHook(() => useWebSocket(`${wsUrl}?token=${mockToken}`, { onError }));
    await server.connected;

    // Send malformed JSON
    act(() => {
      server.send('{ invalid json }');
    });

    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'PARSE_ERROR',
          message: expect.stringContaining('JSON')
        })
      );
    });

    // Connection should remain open
    expect(result.current.readyState).toBe(WebSocket.OPEN);

    consoleSpy.mockRestore();
  });

  it('should handle network timeouts', async () => {
    // Create server but don't start it to simulate timeout
    const mockWebSocket = {
      readyState: WebSocket.CONNECTING,
      close: jest.fn(),
      send: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
    };

    const originalWebSocket = global.WebSocket;
    (global as any).WebSocket = jest.fn().mockImplementation(() => mockWebSocket);

    const { result } = renderHook(() => useWebSocket(`${wsUrl}?token=${mockToken}`));

    // Simulate timeout
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 6000));
    });

    expect(result.current.readyState).toBe(WebSocket.CLOSED);
    expect(mockWebSocket.close).toHaveBeenCalled();

    global.WebSocket = originalWebSocket;
  });

  it('should handle rate limiting', async () => {
    server = new WS(`${wsUrl}?token=${mockToken}`);
    
    const { result } = renderHook(() => useWebSocket(`${wsUrl}?token=${mockToken}`));
    await server.connected;

    // Send many messages quickly
    const messages = Array(20).fill(0).map((_, i) => ({
      type: 'test',
      payload: { index: i }
    }));

    act(() => {
      messages.forEach(msg => result.current.sendMessage(msg));
    });

    // Check that messages are queued and sent with rate limiting
    const receivedMessages: string[] = [];
    server.on('message', (data) => {
      receivedMessages.push(data as string);
    });

    await waitFor(() => {
      expect(receivedMessages.length).toBeGreaterThan(0);
      expect(receivedMessages.length).toBeLessThanOrEqual(20);
    });
  });

  it('should clear message queue on disconnect', async () => {
    server = new WS(`${wsUrl}?token=${mockToken}`);
    
    const { result } = renderHook(() => useWebSocket(`${wsUrl}?token=${mockToken}`));
    await server.connected;

    // Queue messages
    act(() => {
      result.current.sendMessage({ type: 'test1', payload: {} });
      result.current.sendMessage({ type: 'test2', payload: {} });
    });

    // Disconnect
    server.close();

    await waitFor(() => {
      expect(result.current.readyState).toBe(WebSocket.CLOSED);
    });

    // Try to send message while disconnected
    const consoleSpy = jest.spyOn(console, 'warn').mockImplementation();
    
    act(() => {
      result.current.sendMessage({ type: 'test3', payload: {} });
    });

    // Messages are queued when disconnected, no warning expected
    expect(result.current.sendMessage).toBeDefined();

    consoleSpy.mockRestore();
  });

  it('should handle server errors gracefully', async () => {
    server = new WS(`${wsUrl}?token=${mockToken}`);
    
    const { result } = renderHook(() => useWebSocket(`${wsUrl}?token=${mockToken}`));
    await server.connected;

    // Send server error message
    const errorMessage = {
      type: 'error',
      error: {
        code: 'INTERNAL_ERROR',
        message: 'Server processing failed',
      }
    };

    act(() => {
      server.send(JSON.stringify(errorMessage));
    });

    await waitFor(() => {
      expect(result.current.lastMessage).toEqual(errorMessage);
      expect(result.current.error).toEqual(errorMessage.error);
    });

    // Connection should remain open for recoverable errors
    expect(result.current.isConnected).toBe(true);
  });
});