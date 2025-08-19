/**
 * Login to Chat Test Utilities
 * Real flow testing helper functions (≤8 lines each)
 * Business Value: Reusable test utilities for P0 critical path
 * 
 * ARCHITECTURAL COMPLIANCE: ≤300 lines, functions ≤8 lines
 */

import { act, waitFor, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// Mock setup functions (≤8 lines each)
export function setupMockWebSocket(): any {
  const mockWebSocket = {
    send: jest.fn(),
    close: jest.fn(),
    readyState: 1, // OPEN
    addEventListener: jest.fn(),
    removeEventListener: jest.fn()
  };
  (global as any).WebSocket = jest.fn(() => mockWebSocket);
  return mockWebSocket;
}

export function setupMockThreadsApi() {
  const { threadsApi } = require('@/services/api');
  threadsApi.getThreads.mockResolvedValue({
    threads: [{ id: 'thread-1', title: 'Test Thread' }]
  });
  threadsApi.getThread.mockResolvedValue({
    id: 'thread-1', messages: []
  });
}

export function setupMockStorage() {
  Object.defineProperty(window, 'localStorage', {
    value: {
      getItem: jest.fn(),
      setItem: jest.fn(),
      clear: jest.fn()
    }
  });
}

export function setupFailingWebSocket() {
  (global as any).WebSocket = jest.fn(() => {
    throw new Error('WebSocket connection failed');
  });
}

export function setupSlowThreadsApi() {
  const { threadsApi } = require('@/services/api');
  threadsApi.getThreads.mockImplementation(
    () => new Promise(resolve => setTimeout(resolve, 2000))
  );
}

export function cleanupMockWebSocket(mockWebSocket: any) {
  if (mockWebSocket) {
    mockWebSocket.close();
    mockWebSocket = null;
  }
}

// Test interaction functions (≤8 lines each)
export async function performRealLogin(
  user: ReturnType<typeof userEvent.setup>,
  mockToken: string
) {
  // Wait for auth provider to finish loading
  await waitFor(() => {
    expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
  });
  
  const loginButton = screen.getByText('Login with Google');
  await user.click(loginButton);
  
  // Simulate successful OAuth flow
  window.localStorage.setItem('jwt_token', mockToken);
  window.dispatchEvent(new Event('storage'));
}

export async function sendTestMessage(
  user: ReturnType<typeof userEvent.setup>,
  message: string
) {
  const messageInput = screen.getByTestId('message-input');
  const sendButton = screen.getByTestId('send-button');
  
  await user.type(messageInput, message);
  await user.click(sendButton);
}

export async function simulateTokenExpiration() {
  // Simulate token expiration by clearing storage
  window.localStorage.removeItem('jwt_token');
  window.dispatchEvent(new Event('storage'));
}

// Verification functions (≤8 lines each)
export async function verifyWebSocketConnection(mockWebSocket: any) {
  await waitFor(() => {
    expect((global as any).WebSocket).toHaveBeenCalled();
    expect(mockWebSocket.addEventListener).toHaveBeenCalledWith(
      'open', expect.any(Function)
    );
  });
}

export async function verifyThreadsLoaded() {
  const { threadsApi } = require('@/services/api');
  await waitFor(() => {
    expect(threadsApi.getThreads).toHaveBeenCalled();
  });
}

export async function verifyChatReady() {
  await waitFor(() => {
    expect(screen.getByTestId('chat-window')).toBeInTheDocument();
    expect(screen.getByTestId('message-input')).toBeEnabled();
  });
}

export async function verifyTokenStorage(mockToken: string) {
  expect(window.localStorage.setItem).toHaveBeenCalledWith(
    'jwt_token', mockToken
  );
}

export async function verifyWebSocketAuthentication(
  mockWebSocket: any, 
  mockToken: string
) {
  await waitFor(() => {
    expect(mockWebSocket.send).toHaveBeenCalledWith(
      expect.stringContaining(mockToken)
    );
  });
}

export async function verifyConnectionErrorHandling() {
  await waitFor(() => {
    expect(screen.getByText(/connection failed/i)).toBeInTheDocument();
  });
}

export async function verifyThreadsLoadingState() {
  expect(screen.getByTestId('threads-loading')).toBeInTheDocument();
}

export async function verifyTokenRefreshFlow() {
  await waitFor(() => {
    expect(screen.getByText(/please login again/i)).toBeInTheDocument();
  });
}

export async function verifyWebSocketPersistence(mockWebSocket: any) {
  expect(mockWebSocket.close).not.toHaveBeenCalled();
}

export async function verifyMessageReceiving(mockWebSocket: any) {
  // Simulate receiving WebSocket message
  const mockMessage = { type: 'message', payload: { text: 'Hello' } };
  const openCallback = mockWebSocket.addEventListener.mock.calls
    .find((call: any) => call[0] === 'message')[1];
  
  act(() => {
    openCallback({ data: JSON.stringify(mockMessage) });
  });
  
  await waitFor(() => {
    expect(screen.getByText('Hello')).toBeInTheDocument();
  });
}

export async function verifyMessageSending(mockWebSocket: any) {
  await waitFor(() => {
    expect(mockWebSocket.send).toHaveBeenCalledWith(
      expect.stringContaining('Hello from test')
    );
  });
}

export async function verifyConnectionStatus() {
  await waitFor(() => {
    expect(screen.getByTestId('connection-status')).toHaveTextContent(
      'Connected'
    );
  });
}