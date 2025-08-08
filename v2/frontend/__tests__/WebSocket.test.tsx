import React from 'react';
import { render, screen, act } from '@testing-library/react';
import { WebSocketProvider, useWebSocket } from '../contexts/WebSocketContext';
import { Server } from 'mock-socket';
import { WebSocketMessage } from '../types/websockets';

const WS_URL = 'ws://localhost:8000/ws';

describe('WebSocketContext', () => {
  let mockServer: Server;

  beforeEach(() => {
    mockServer = new Server(WS_URL);
  });

  afterEach(() => {
    mockServer.close();
  });

  const TestComponent = () => {
    const { status, lastMessage, sendMessage } = useWebSocket();

    const handleSendMessage = () => {
      const message: WebSocketMessage = {
        type: 'analysis_request',
        payload: { request_model: { id: '1', user_id: '1', query: 'test', workloads: [] } },
      };
      sendMessage(message);
    };

    return (
      <div>
        <div data-testid="status">{status}</div>
        <div data-testid="message">{JSON.stringify(lastMessage)}</div>
        <button onClick={handleSendMessage}>Send</button>
      </div>
    );
  };

  it('should connect and disconnect', async () => {
    const { unmount } = render(
      <WebSocketProvider>
        <TestComponent />
      </WebSocketProvider>
    );

    await act(() => mockServer.emit('open'));
    expect(screen.getByTestId('status').textContent).toBe('OPEN');

    unmount();
    // In a real scenario, the client would initiate the close.
    // Here, we can check the server's connection count.
    expect(mockServer.clients().length).toBe(0);
  });

  it('should send and receive messages', async () => {
    render(
      <WebSocketProvider>
        <TestComponent />
      </WebSocketProvider>
    );

    await act(() => mockServer.emit('open'));

    const message: WebSocketMessage = {
        type: 'agent_started',
        payload: { run_id: '123' },
      };

    act(() => {
      mockServer.emit('message', JSON.stringify(message));
    });

    expect(screen.getByTestId('message').textContent).toBe(JSON.stringify(message));
  });
});
