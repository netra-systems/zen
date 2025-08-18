/**
 * MessageInput Message History Tests
 * Tests for message history functionality
 */

// Mock dependencies BEFORE imports
const mockSendMessage = jest.fn();
const mockUseWebSocket = jest.fn();
const mockUseUnifiedChatStore = jest.fn();
const mockUseThreadStore = jest.fn();
const mockUseAuthStore = jest.fn();
const mockGenerateUniqueId = jest.fn();

jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: mockUseWebSocket
}));
jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: mockUseUnifiedChatStore
}));
jest.mock('@/store/threadStore', () => ({
  useThreadStore: mockUseThreadStore
}));
jest.mock('@/store/authStore', () => ({
  useAuthStore: mockUseAuthStore
}));
jest.mock('@/lib/utils', () => ({
  generateUniqueId: mockGenerateUniqueId,
  cn: jest.fn((...classes) => classes.filter(Boolean).join(' '))
}));
jest.mock('@/components/chat/utils/messageInputUtils', () => ({
  getPlaceholder: jest.fn((isAuthenticated, isProcessing, messageLength) => {
    if (!isAuthenticated) return 'Please sign in to send messages';
    if (isProcessing) return 'Agent is thinking...';
    if (messageLength > 9000) return `${10000 - messageLength} characters remaining`;
    return 'Type a message...';
  }),
  getTextareaClassName: jest.fn(() => 'mocked-textarea-class'),
  getCharCountClassName: jest.fn(() => 'mocked-char-count-class'),
  shouldShowCharCount: jest.fn((messageLength) => messageLength > 8000),
  isMessageDisabled: jest.fn((isProcessing, isAuthenticated, isSending) => {
    return isProcessing || !isAuthenticated || isSending;
  }),
  canSendMessage: jest.fn((isDisabled, message, messageLength) => {
    return !isDisabled && !!message.trim() && messageLength <= 10000;
  })
}));
// Create a stateful message history mock
let mockMessageHistory: string[] = [];
let mockHistoryIndex = -1;

const mockAddToHistory = jest.fn((message: string) => {
  mockMessageHistory.push(message);
  mockHistoryIndex = mockMessageHistory.length;
});

const mockNavigateHistory = jest.fn((direction: 'up' | 'down') => {
  if (direction === 'up' && mockHistoryIndex > 0) {
    mockHistoryIndex--;
    return mockMessageHistory[mockHistoryIndex];
  }
  if (direction === 'down' && mockHistoryIndex < mockMessageHistory.length - 1) {
    mockHistoryIndex++;
    return mockMessageHistory[mockHistoryIndex];
  }
  if (direction === 'down' && mockHistoryIndex === mockMessageHistory.length - 1) {
    mockHistoryIndex = mockMessageHistory.length;
    return '';
  }
  return mockMessageHistory[mockHistoryIndex] || '';
});

jest.mock('@/components/chat/hooks/useMessageHistory', () => ({
  useMessageHistory: jest.fn(() => ({
    messageHistory: mockMessageHistory,
    addToHistory: mockAddToHistory,
    navigateHistory: mockNavigateHistory
  }))
}));
jest.mock('@/components/chat/hooks/useTextareaResize', () => ({
  useTextareaResize: jest.fn(() => ({ rows: 1 }))
}));
jest.mock('@/components/chat/hooks/useMessageSending', () => ({
  useMessageSending: jest.fn(() => ({
    isSending: false,
    handleSend: jest.fn(async (params) => {
      if (params.isAuthenticated && params.message && params.message.trim()) {
        mockSendMessage({
          type: 'user_message',
          payload: {
            content: params.message,
            references: [],
            thread_id: params.activeThreadId || params.currentThreadId
          }
        });
      }
    })
  }))
}));

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MessageInput } from '@/components/chat/MessageInput';

describe('MessageInput - Message History', () => {
  const mockChatStore = {
    setProcessing: jest.fn(),
    addMessage: jest.fn()
  };
  const mockThreadStore = {
    setCurrentThread: jest.fn(),
    addThread: jest.fn()
  };

  beforeEach(() => {
    jest.clearAllMocks();
    // Reset message history state
    mockMessageHistory.length = 0;
    mockHistoryIndex = -1;
    
    // Setup default mocks
    mockUseWebSocket.mockReturnValue({
      sendMessage: mockSendMessage,
    });
    
    mockUseUnifiedChatStore.mockReturnValue({
      activeThreadId: 'thread-1',
      isProcessing: false,
      setProcessing: mockChatStore.setProcessing,
      addMessage: mockChatStore.addMessage,
    });
    
    mockUseThreadStore.mockReturnValue({
      currentThreadId: 'thread-1',
      setCurrentThread: mockThreadStore.setCurrentThread,
      addThread: mockThreadStore.addThread,
    });
    
    mockUseAuthStore.mockReturnValue({
      isAuthenticated: true,
    });
    
    mockGenerateUniqueId.mockImplementation((prefix) => `${prefix}-${Date.now()}`);
  });

  describe('Message history', () => {
    it('should add sent messages to history', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i) as HTMLTextAreaElement;
      
      // Send first message
      await userEvent.type(textarea, 'First message');
      await userEvent.type(textarea, '{enter}');
      
      await waitFor(() => {
        expect(textarea.value).toBe('');
        expect(mockSendMessage).toHaveBeenCalledWith({
          type: 'user_message',
          payload: {
            content: 'First message',
            references: [],
            thread_id: 'thread-1'
          }
        });
      });
      
      // Navigate up should show the message in history
      await userEvent.type(textarea, '{arrowup}');
      await waitFor(() => {
        expect(textarea.value).toBe('First message');
      });
    });

    it('should not add empty messages to history', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i) as HTMLTextAreaElement;
      
      // Try to send empty message
      await userEvent.type(textarea, '   ');
      await userEvent.clear(textarea);
      
      // Enter on empty should not send
      await userEvent.type(textarea, '{enter}');
      expect(mockSendMessage).not.toHaveBeenCalled();
      
      // Arrow up should not show any history
      await userEvent.type(textarea, '{arrowup}');
      expect(textarea.value).toBe('');
    });

    it('should maintain history across component lifecycle', async () => {
      const { rerender } = render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i) as HTMLTextAreaElement;
      
      // Send a message
      await userEvent.type(textarea, 'Persistent message');
      await userEvent.type(textarea, '{enter}');
      
      // Re-render component
      rerender(<MessageInput />);
      
      // History should be maintained (in component state)
      const newTextarea = screen.getByPlaceholderText(/Type a message/i) as HTMLTextAreaElement;
      await userEvent.type(newTextarea, '{arrowup}');
      
      // Re-render maintains component instance, so history persists
      // Navigate up to see the history
      fireEvent.keyDown(newTextarea, { key: 'ArrowUp' });
      await waitFor(() => {
        expect(newTextarea.value).toBe('Persistent message');
      });
    });
  });
});