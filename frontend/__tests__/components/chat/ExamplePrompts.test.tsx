
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ExamplePrompts } from '@/components/chat/ExamplePrompts';
import { setupChatMocks, resetChatMocks, renderWithChatSetup, mockUnifiedChatStore, mockWebSocket, mockAuthStore } from './shared-test-setup';

// Mock only necessary dependencies - use real component behavior
jest.mock('@/hooks/useWebSocket');
jest.mock('@/store/unified-chat');
jest.mock('@/store/authStore');

// Import the mocked hooks
import { useWebSocket } from '@/hooks/useWebSocket';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useAuthStore } from '@/store/authStore';

// Setup mocks before tests
beforeAll(() => {
  setupChatMocks();
});

beforeEach(() => {
  resetChatMocks();
  // Setup mock implementations
  (useWebSocket as jest.Mock).mockReturnValue(mockWebSocket);
  (useUnifiedChatStore as jest.Mock).mockReturnValue(mockUnifiedChatStore);
  (useAuthStore as jest.Mock).mockReturnValue(mockAuthStore);
});

describe('ExamplePrompts', () => {
  it('sends a message when an example prompt is clicked', () => {
    (useAuthStore as jest.Mock).mockReturnValue({
      ...mockAuthStore,
      isAuthenticated: true
    });

    renderWithChatSetup(<ExamplePrompts />);

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
    (useAuthStore as jest.Mock).mockReturnValue({
      ...mockAuthStore,
      isAuthenticated: false
    });
    
    const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();
    
    renderWithChatSetup(<ExamplePrompts />);
    
    const firstPrompt = screen.getByText(/I need to reduce costs but keep quality the same/i);
    fireEvent.click(firstPrompt);
    
    expect(consoleErrorSpy).toHaveBeenCalledWith('[ERROR]', 'User must be authenticated to send messages');
    expect(mockUnifiedChatStore.addMessage).not.toHaveBeenCalled();
    expect(mockWebSocket.sendMessage).not.toHaveBeenCalled();
    expect(mockUnifiedChatStore.setProcessing).not.toHaveBeenCalled();
    
    consoleErrorSpy.mockRestore();
  });
});
