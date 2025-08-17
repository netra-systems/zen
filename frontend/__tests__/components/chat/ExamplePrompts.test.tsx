
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ExamplePrompts } from '@/components/chat/ExamplePrompts';
import { setupChatMocks, resetChatMocks, renderWithChatSetup } from './shared-test-setup';

const mockSendMessage = jest.fn();
const mockSetProcessing = jest.fn();
const mockAddMessage = jest.fn();

// Mock all dependencies at the top level
jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: () => ({ sendMessage: mockSendMessage }),
}));

jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: () => ({ 
    setProcessing: mockSetProcessing,
    addMessage: mockAddMessage 
  }),
}));

jest.mock('@/store/authStore', () => ({
  useAuthStore: jest.fn()
}));

// Import the mocked hooks
import { useAuthStore } from '@/store/authStore';

// Setup mocks before tests
beforeAll(() => {
  setupChatMocks();
});

beforeEach(() => {
  resetChatMocks();
  mockSendMessage.mockClear();
  mockSetProcessing.mockClear();
  mockAddMessage.mockClear();
});

describe('ExamplePrompts', () => {
  it('sends a message when an example prompt is clicked', () => {
    (useAuthStore as jest.Mock).mockReturnValue({
      isAuthenticated: true
    });

    renderWithChatSetup(<ExamplePrompts />);

    const firstPrompt = screen.getByText(/I need to reduce costs but keep quality the same/i);
    fireEvent.click(firstPrompt);

    expect(mockAddMessage).toHaveBeenCalledWith(expect.objectContaining({
      role: 'user',
      content: 'I need to reduce costs but keep quality the same. For feature X, I can accept a latency of 500ms. For feature Y, I need to maintain the current latency of 200ms.'
    }));
    expect(mockSendMessage).toHaveBeenCalledWith({
      type: 'user_message',
      payload: { 
        content: 'I need to reduce costs but keep quality the same. For feature X, I can accept a latency of 500ms. For feature Y, I need to maintain the current latency of 200ms.',
        references: []
      }
    });
    expect(mockSetProcessing).toHaveBeenCalledWith(true);
  });

  it('does not send message when user is not authenticated', () => {
    (useAuthStore as jest.Mock).mockReturnValue({
      isAuthenticated: false
    });
    
    const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();
    
    renderWithChatSetup(<ExamplePrompts />);
    
    const firstPrompt = screen.getByText(/I need to reduce costs but keep quality the same/i);
    fireEvent.click(firstPrompt);
    
    expect(consoleErrorSpy).toHaveBeenCalledWith('User must be authenticated to send messages');
    expect(mockAddMessage).not.toHaveBeenCalled();
    expect(mockSendMessage).not.toHaveBeenCalled();
    expect(mockSetProcessing).not.toHaveBeenCalled();
    
    consoleErrorSpy.mockRestore();
  });
});
