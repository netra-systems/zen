import React from 'react';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { WebSocketProvider } from '@/providers/WebSocketProvider';
import { AuthContext } from '@/auth/AuthContext';
import { authService } from '@/auth/service';
import WS from 'jest-websocket-mock';

jest.mock('@/auth/service');

describe('useWebSocket', () => {
  let server: WS;
  const mockToken = 'test-token';
  const wsUrl = 'ws://localhost:8000/ws';

  // Create wrapper component with AuthContext and WebSocketProvider
  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <AuthContext.Provider value={{ token: mockToken, user: null, login: jest.fn(), logout: jest.fn(), isAuthenticated: true }}>
      <WebSocketProvider>{children}</WebSocketProvider>
    </AuthContext.Provider>
  );

  beforeEach(() => {
    server = new WS(`${wsUrl}?token=${mockToken}`);
    (authService.getToken as jest.Mock).mockReturnValue(mockToken);
    localStorage.setItem('access_token', mockToken);
  });

  afterEach(() => {
    WS.clean();
    jest.clearAllMocks();
    localStorage.clear();
  });

  it('should establish WebSocket connection with token', async () => {
    const { result } = renderHook(() => useWebSocket(), { wrapper });

    await server.connected;
    
    expect(result.current.isConnected).toBe(true);
    expect(server.server.clients()).toHaveLength(1);
  });

  it('should handle incoming messages', async () => {
    const { result } = renderHook(() => useWebSocket(), { wrapper });
    
    await server.connected;

    const testMessage = {
      type: 'agent_started',
      payload: { run_id: 'test-123' }
    };

    act(() => {
      server.send(JSON.stringify(testMessage));
    });

    await waitFor(() => {
      expect(result.current.lastMessage).toEqual(testMessage);
    });
  });

  it('should send messages correctly', async () => {
    const { result } = renderHook(() => useWebSocket(), { wrapper });
    
    await server.connected;

    const messageToSend = {
      type: 'user_message',
      payload: { text: 'Hello' }
    };

    act(() => {
      result.current.sendMessage(messageToSend);
    });

    await expect(server).toReceiveMessage(JSON.stringify(messageToSend));
  });

  it('should handle reconnection on disconnect', async () => {
    const { result } = renderHook(() => useWebSocket(), { wrapper });
    
    await server.connected;
    expect(result.current.isConnected).toBe(true);

    // Simulate disconnect
    server.close();

    await waitFor(() => {
      expect(result.current.isConnected).toBe(false);
    });

    // Create new server for reconnection
    const newServer = new WS(`${wsUrl}?token=${mockToken}`);
    
    await waitFor(() => {
      expect(result.current.isConnected).toBe(true);
    }, { timeout: 5000 });

    newServer.close();
  });

  it('should handle connection errors', async () => {
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
    
    // Force connection error by not starting server
    server.close();
    
    const { result } = renderHook(() => useWebSocket(), { wrapper });

    await waitFor(() => {
      expect(result.current.isConnected).toBe(false);
    });

    expect(consoleSpy).toHaveBeenCalledWith(
      expect.stringContaining('WebSocket error')
    );

    consoleSpy.mockRestore();
  });

  it('should clean up on unmount', async () => {
    const { result, unmount } = renderHook(() => useWebSocket());
    
    await server.connected;
    expect(result.current.isConnected).toBe(true);

    unmount();

    await waitFor(() => {
      expect(server.server.clients()).toHaveLength(0);
    });
  });

  it('should not connect without authentication token', () => {
    localStorage.clear();
    (authService.getAuthHeaders as jest.Mock).mockReturnValue({});

    const { result } = renderHook(() => useWebSocket());

    expect(result.current.isConnected).toBe(false);
    expect(server.server.clients()).toHaveLength(0);
  });

  it('should handle message queue when disconnected', async () => {
    const { result } = renderHook(() => useWebSocket());
    
    // Send message before connection
    const messageToSend = {
      type: 'user_message',
      payload: { text: 'Queued message' }
    };

    act(() => {
      result.current.sendMessage(messageToSend);
    });

    // Message should be queued
    await server.connected;

    // Check if queued message was sent after connection
    await expect(server).toReceiveMessage(JSON.stringify(messageToSend));
  });
});