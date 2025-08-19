/**
 * User Flow Simulation Utilities
 * Complex authentication and websocket flows with 8-line function limit enforcement
 */

import { fireEvent, waitFor, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// Types for user flow simulation
export interface AuthFlowConfig {
  email?: string;
  password?: string;
  rememberMe?: boolean;
  expectError?: boolean;
}

export interface WebSocketFlowConfig {
  messageCount?: number;
  messageDelay?: number;
  reconnectDelay?: number;
  expectDisconnect?: boolean;
}

export interface ChatFlowConfig {
  threadId?: string;
  messageText?: string;
  expectResponse?: boolean;
  streamingResponse?: boolean;
}

// Authentication flow simulation
export const simulateLoginFlow = async (config: AuthFlowConfig = {}) => {
  const email = config.email || 'test@example.com';
  const password = config.password || 'password123';
  
  await userEvent.type(screen.getByLabelText(/email/i), email);
  await userEvent.type(screen.getByLabelText(/password/i), password);
  
  if (config.rememberMe) {
    await userEvent.click(screen.getByLabelText(/remember/i));
  }
  
  await userEvent.click(screen.getByRole('button', { name: /login/i }));
};

export const simulateLogoutFlow = async () => {
  await userEvent.click(screen.getByRole('button', { name: /logout/i }));
  
  await waitFor(() => {
    expect(screen.queryByTestId('auth-status')).toHaveTextContent(/logged out/i);
  });
};

export const simulateRegistrationFlow = async (config: AuthFlowConfig = {}) => {
  const email = config.email || 'newuser@example.com';
  const password = config.password || 'newpassword123';
  
  await userEvent.type(screen.getByLabelText(/email/i), email);
  await userEvent.type(screen.getByLabelText(/password/i), password);
  await userEvent.type(screen.getByLabelText(/confirm password/i), password);
  
  await userEvent.click(screen.getByRole('button', { name: /register/i }));
};

export const simulatePasswordResetFlow = async (email: string = 'reset@example.com') => {
  await userEvent.type(screen.getByLabelText(/email/i), email);
  await userEvent.click(screen.getByRole('button', { name: /reset password/i }));
  
  await waitFor(() => {
    expect(screen.getByText(/reset email sent/i)).toBeInTheDocument();
  });
};

// WebSocket flow simulation
export const simulateWebSocketConnection = async (config: WebSocketFlowConfig = {}) => {
  fireEvent.click(screen.getByTestId('btn-connecting'));
  
  await waitFor(() => {
    expect(screen.getByTestId('ws-connecting')).toHaveTextContent('true');
  });
  
  fireEvent.click(screen.getByTestId('btn-connected'));
  
  await waitFor(() => {
    expect(screen.getByTestId('ws-connected')).toHaveTextContent('true');
  });
};

export const simulateWebSocketDisconnection = async () => {
  fireEvent.click(screen.getByTestId('btn-disconnected'));
  
  await waitFor(() => {
    expect(screen.getByTestId('ws-disconnected')).toHaveTextContent('true');
  });
};

export const simulateWebSocketReconnection = async (config: WebSocketFlowConfig = {}) => {
  fireEvent.click(screen.getByTestId('btn-reconnecting'));
  
  const delay = config.reconnectDelay || 100;
  await new Promise(resolve => setTimeout(resolve, delay));
  
  fireEvent.click(screen.getByTestId('btn-connected'));
  
  await waitFor(() => {
    expect(screen.getByTestId('ws-connected')).toHaveTextContent('true');
  });
};

export const simulateWebSocketError = async () => {
  fireEvent.click(screen.getByTestId('btn-error'));
  
  await waitFor(() => {
    expect(screen.getByTestId('ws-error')).toHaveTextContent('true');
  });
};

// Chat flow simulation
export const simulateChatMessageSend = async (config: ChatFlowConfig = {}) => {
  const message = config.messageText || 'Hello, this is a test message';
  
  const input = screen.getByRole('textbox', { name: /message/i });
  await userEvent.type(input, message);
  
  await userEvent.click(screen.getByRole('button', { name: /send/i }));
  
  if (config.expectResponse) {
    await waitFor(() => {
      expect(screen.getByTestId('message-list')).toHaveTextContent(message);
    });
  }
};

export const simulateThreadCreation = async (threadTitle: string = 'New Thread') => {
  await userEvent.click(screen.getByRole('button', { name: /new thread/i }));
  
  const titleInput = screen.getByLabelText(/thread title/i);
  await userEvent.type(titleInput, threadTitle);
  
  await userEvent.click(screen.getByRole('button', { name: /create/i }));
  
  await waitFor(() => {
    expect(screen.getByText(threadTitle)).toBeInTheDocument();
  });
};

export const simulateThreadNavigation = async (threadId: string) => {
  const threadElement = screen.getByTestId(`thread-${threadId}`);
  await userEvent.click(threadElement);
  
  await waitFor(() => {
    expect(screen.getByTestId('current-thread-id')).toHaveTextContent(threadId);
  });
};

// File upload simulation
export const simulateFileUpload = async (fileName: string = 'test.txt', content: string = 'test content') => {
  const file = new File([content], fileName, { type: 'text/plain' });
  const input = screen.getByLabelText(/upload file/i) as HTMLInputElement;
  
  await userEvent.upload(input, file);
  
  await waitFor(() => {
    expect(screen.getByText(fileName)).toBeInTheDocument();
  });
};

// Search and filter simulation
export const simulateSearch = async (query: string) => {
  const searchInput = screen.getByRole('searchbox') || screen.getByLabelText(/search/i);
  
  await userEvent.clear(searchInput);
  await userEvent.type(searchInput, query);
  
  await waitFor(() => {
    expect(searchInput).toHaveValue(query);
  });
};