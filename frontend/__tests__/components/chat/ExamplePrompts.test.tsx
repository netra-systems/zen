
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { jest } from '@jest/globals';

// Mock dependencies at the top level
const mockSendMessage = jest.fn();
const mockWebSocket = {
  sendMessage: mockSendMessage,
  connected: true,
  error: null,
  status: 'OPEN' as const,
  isConnected: true,
  connectionState: 'connected' as const,
};

const mockUnifiedChatStore = {
  isProcessing: false,
  messages: [],
  addMessage: jest.fn(),
  setProcessing: jest.fn(),
  clearMessages: jest.fn(),
  activeThreadId: 'thread-1',
  setActiveThread: jest.fn(),
};

const mockAuthStore = {
  isAuthenticated: true,
  user: { id: 'test-user', email: 'test@example.com', name: 'Test User' },
  token: 'test-token-123',
  login: jest.fn(),
  logout: jest.fn(),
  loading: false,
};

jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: jest.fn(() => mockWebSocket)
}));

jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: jest.fn(() => mockUnifiedChatStore)
}));

jest.mock('@/store/authStore', () => ({
  useAuthStore: jest.fn(() => mockAuthStore)
}));

import { ExamplePrompts } from '@/components/chat/ExamplePrompts';

const resetMocks = () => {
  jest.clearAllMocks();
  mockUnifiedChatStore.isProcessing = false;
  mockAuthStore.isAuthenticated = true;
};

beforeEach(() => {
  resetMocks();
});

describe('ExamplePrompts', () => {
  it('sends a message when an example prompt is clicked', () => {
    mockAuthStore.isAuthenticated = true;

    render(<ExamplePrompts />);

    const firstPrompt = screen.getByText(/I need to reduce costs but keep quality the same/i);
    fireEvent.click(firstPrompt);

    expect(mockUnifiedChatStore.addMessage).toHaveBeenCalledWith(expect.objectContaining({
      role: 'user',
      content: 'I need to reduce costs but keep quality the same. For feature X, I can accept a latency of 500ms. For feature Y, I need to maintain the current latency of 200ms.'
    }));
    expect(mockWebSocket.sendMessage).toHaveBeenCalledWith({
      type: 'user_message',
      payload: { 
        content: 'I need to reduce costs but keep quality the same. For feature X, I can accept a latency of 500ms. For feature Y, I need to maintain the current latency of 200ms.',
        references: []
      }
    });
    expect(mockUnifiedChatStore.setProcessing).toHaveBeenCalledWith(true);
  });

  it('does not send message when user is not authenticated', () => {
    mockAuthStore.isAuthenticated = false;
    
    const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();
    
    render(<ExamplePrompts />);
    
    const firstPrompt = screen.getByText(/I need to reduce costs but keep quality the same/i);
    fireEvent.click(firstPrompt);
    
    expect(consoleErrorSpy).toHaveBeenCalledWith('[ERROR]', 'User must be authenticated to send messages');
    expect(mockUnifiedChatStore.addMessage).not.toHaveBeenCalled();
    expect(mockWebSocket.sendMessage).not.toHaveBeenCalled();
    expect(mockUnifiedChatStore.setProcessing).not.toHaveBeenCalled();
    
    consoleErrorSpy.mockRestore();
  });
});
