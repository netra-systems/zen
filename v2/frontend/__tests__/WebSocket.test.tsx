import React, { ReactNode } from 'react';
import { render, screen, act } from '@testing-library/react';
import { WebSocketProvider } from '@/app/providers/WebSocketProvider';
import { useWebSocket } from '@/app/hooks/useWebSocket';
import { Server, WebSocket } from 'mock-socket';
import { useChatStore } from '@/app/store';
import { useAuth } from '@/app/contexts/AuthContext';

import { WEBSOCKET_URL } from '@/config';

jest.mock('@/app/store', () => ({
  useChatStore: jest.fn(),
}));

jest.mock('@/app/contexts/AuthContext', () => ({
  useAuth: jest.fn(),
}));

describe('WebSocketProvider', () => {
  let mockServer: Server;

  beforeEach(() => {
    mockServer = new Server(WS_URL);
    (useChatStore as jest.Mock).mockReturnValue({
      addMessage: jest.fn(),
      setSubAgentName: jest.fn(),
      setSubAgentStatus: jest.fn(),
    });
    (useAuth as jest.Mock).mockReturnValue({
      user: { id: 'test-user' },
      token: 'test-token',
    });
  });

  afterEach(() => {
    mockServer.stop();
  });

  const TestComponent = () => {
    useWebSocket();
    return null;
  };

  it('should connect and disconnect', async () => {
    const { unmount } = render(
      <WebSocketProvider>
        <TestComponent />
      </WebSocketProvider>
    );

    // Wait for the connection to be established
    await new Promise(resolve => mockServer.on('connection', resolve));

    expect(mockServer.clients().length).toBe(1);

    unmount();

    // Wait for the connection to be closed
    await new Promise(resolve => mockServer.on('close', resolve));

    expect(mockServer.clients().length).toBe(0);
  });
});