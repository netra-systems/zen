import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { WebSocketProvider, useWebSocket } from '@/contexts/WebSocketContext';
import { AuthProvider, useAuth } from '@/contexts/AuthContext';

// Mock the WebSocket
const mockSend = jest.fn();
const mockClose = jest.fn();
global.WebSocket = jest.fn(() => ({
  onopen: jest.fn(),
  onmessage: jest.fn(),
  onclose: jest.fn(),
  onerror: jest.fn(),
  send: mockSend,
  close: mockClose,
})) as any;

const TestComponent = () => {
  const { sendMessage, lastMessage, isConnected } = useWebSocket();
  const { login, logout, user } = useAuth();

  return (
    <div>
      <button onClick={() => login()}>Login</button>
      <button onClick={() => logout()}>Logout</button>
      <button onClick={() => sendMessage({ payload: { query: 'test' } } as any)}>Send</button>
      <div data-testid="connected">{isConnected ? 'true' : 'false'}</div>
      <div data-testid="user">{user?.email}</div>
      <div data-testid="message">{JSON.stringify(lastMessage)}</div>
    </div>
  );
};

describe('WebSocketProvider', () => {
  it('should connect and disconnect with auth status', async () => {
    render(
      <AuthProvider>
        <WebSocketProvider>
          <TestComponent />
        </WebSocketProvider>
      </AuthProvider>
    );

    // Initially not connected
    expect(screen.getByTestId('connected')).toHaveTextContent('false');

    // Login
    fireEvent.click(screen.getByText('Login'));

    // Wait for connection
    await waitFor(() => expect(screen.getByTestId('connected')).toHaveTextContent('true'));

    // Logout
    fireEvent.click(screen.getByText('Logout'));

    // Wait for disconnection
    await waitFor(() => expect(screen.getByTestId('connected')).toHaveTextContent('false'));
  });

  it('should send and receive messages', async () => {
    render(
      <AuthProvider>
        <WebSocketProvider>
          <TestComponent />
        </WebSocketProvider>
      </AuthProvider>
    );

    // Login and connect
    fireEvent.click(screen.getByText('Login'));
    await waitFor(() => expect(screen.getByTestId('connected')).toHaveTextContent('true'));

    // Send a message
    fireEvent.click(screen.getByText('Send'));
    expect(mockSend).toHaveBeenCalledWith(JSON.stringify({ type: 'analysis_request', payload: { query: 'test' } }));

    // Simulate receiving a message
    const socketInstance = (global.WebSocket as any).mock.instances[0];
    const message = { type: 'test', payload: { data: 'some data' } };
    socketInstance.onmessage({ data: JSON.stringify(message) });

    // Check if the message is displayed
    await waitFor(() => {
      expect(screen.getByTestId('message')).toHaveTextContent(JSON.stringify(message));
    });
  });
});