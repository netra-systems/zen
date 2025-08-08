import React, { ReactNode } from 'react';
import { render, screen, act, waitFor } from '@testing-library/react';
import { WebSocketProvider } from '../providers/WebSocketProvider';
import { useWebSocket } from '../hooks/useWebSocket';
import { Server, WebSocket } from 'mock-socket';
import { useChatStore } from '@/store';
import { useAuth } from '../contexts/AuthContext';

import { WEBSOCKET_URL } from '../config';

const WS_URL = WEBSOCKET_URL;

jest.mock('@/store', () => ({
  useChatStore: jest.fn(),
}));

jest.mock('../contexts/AuthContext', () => ({
  useAuth: jest.fn(),
}));

describe('WebSocketProvider', () => {
  let mockServer: Server;

  beforeEach(() => {
    mockServer = new Server(WEBSOCKET_URL);
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
    await waitFor(() => expect(mockServer.clients().length).toBe(1));

    expect(mockServer.clients().length).toBe(1);

    unmount();

    // Wait for the connection to be closed
    await new Promise(resolve => mockServer.on('close', resolve));

    expect(mockServer.clients().length).toBe(0);
  });
});