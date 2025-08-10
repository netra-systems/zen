
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { WebSocketProvider } from '../providers/WebSocketProvider';
import { ExamplePrompts } from '@/components/chat/ExamplePrompts';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useChatStore } from '@/store/chat';
import { useAuthStore } from '@/store/authStore';

const mockSendMessage = jest.fn();
const mockSetProcessing = jest.fn();
const mockAddMessage = jest.fn();

jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: () => ({ sendMessage: mockSendMessage }),
}));

jest.mock('@/store/chat', () => ({
  useChatStore: () => ({ 
    setProcessing: mockSetProcessing,
    addMessage: mockAddMessage 
  }),
}));

jest.mock('@/store/authStore');

describe('ExamplePrompts', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Default mock for authenticated user
    (useAuthStore as jest.Mock).mockReturnValue({
      isAuthenticated: true
    });
  });

  it('sends a message when an example prompt is clicked', () => {
    render(<ExamplePrompts />);

    const firstPrompt = screen.getByText(/I need to reduce costs but keep quality the same/i);
    fireEvent.click(firstPrompt);

    expect(mockAddMessage).toHaveBeenCalledWith(expect.objectContaining({
      type: 'user',
      content: 'I need to reduce costs but keep quality the same. For feature X, I can accept a latency of 500ms. For feature Y, I need to maintain the current latency of 200ms.',
      displayed_to_user: true
    }));
    expect(mockSendMessage).toHaveBeenCalledWith({
      type: 'user_message',
      payload: { 
        text: 'I need to reduce costs but keep quality the same. For feature X, I can accept a latency of 500ms. For feature Y, I need to maintain the current latency of 200ms.',
        references: []
      }
    });
    expect(mockSetProcessing).toHaveBeenCalledWith(true);
  });

  it('does not send message when user is not authenticated', () => {
    // Override the mock for this test only
    (useAuthStore as jest.Mock).mockReturnValue({
      isAuthenticated: false
    });
    
    const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();
    
    render(<ExamplePrompts />);
    
    const firstPrompt = screen.getByText(/I need to reduce costs but keep quality the same/i);
    fireEvent.click(firstPrompt);
    
    expect(consoleErrorSpy).toHaveBeenCalledWith('User must be authenticated to send messages');
    expect(mockAddMessage).not.toHaveBeenCalled();
    expect(mockSendMessage).not.toHaveBeenCalled();
    expect(mockSetProcessing).not.toHaveBeenCalled();
    
    consoleErrorSpy.mockRestore();
  });
});
