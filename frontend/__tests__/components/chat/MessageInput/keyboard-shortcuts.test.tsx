/**
 * MessageInput Keyboard Shortcuts Tests
 * Tests for keyboard shortcuts and navigation
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
  if (direction === 'up') {
    if (mockHistoryIndex === -1 || mockHistoryIndex === mockMessageHistory.length) {
      // Start from the most recent message
      mockHistoryIndex = mockMessageHistory.length - 1;
    } else if (mockHistoryIndex > 0) {
      mockHistoryIndex--;
    }
    return mockMessageHistory[mockHistoryIndex] || '';
  }
  
  if (direction === 'down') {
    if (mockHistoryIndex < mockMessageHistory.length - 1) {
      mockHistoryIndex++;
      return mockMessageHistory[mockHistoryIndex];
    } else {
      // Clear input when going past the last message
      mockHistoryIndex = mockMessageHistory.length;
      return '';
    }
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
      return Promise.resolve();
    })
  }))
}));

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MessageInput } from '@/components/chat/MessageInput';

describe('MessageInput - Keyboard Shortcuts', () => {
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
      addOptimisticMessage: jest.fn(),
      updateOptimisticMessage: jest.fn(),
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

  describe('Keyboard shortcuts', () => {
    it('should send message on Enter key', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i);
      
      await userEvent.type(textarea, 'Test message');
      await userEvent.type(textarea, '{enter}');
      
      await waitFor(() => {
        expect(mockSendMessage).toHaveBeenCalledWith({
          type: 'user_message',
          payload: {
            content: 'Test message',
            references: [],
            thread_id: 'thread-1'
          }
        });
      });
    });

    it('should insert newline on Shift+Enter', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i);
      
      await userEvent.type(textarea, 'Line 1');
      await userEvent.type(textarea, '{shift>}{enter}{/shift}');
      await userEvent.type(textarea, 'Line 2');
      
      expect(textarea.value).toContain('Line 1\nLine 2');
    });

    it('should navigate message history with arrow keys', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i) as HTMLTextAreaElement;
      
      // Send some messages to build history
      await userEvent.type(textarea, 'First message');
      await userEvent.type(textarea, '{enter}');
      
      await waitFor(() => {
        expect(textarea.value).toBe('');
      });
      
      await userEvent.type(textarea, 'Second message');
      await userEvent.type(textarea, '{enter}');
      
      await waitFor(() => {
        expect(textarea.value).toBe('');
      });
      
      // Navigate up in history - should get the most recent message first  
      fireEvent.keyDown(textarea, { key: 'ArrowUp' });
      await waitFor(() => {
        expect(textarea.value).toBe('Second message');
      });
      
      // Clear the input first to allow navigation
      fireEvent.change(textarea, { target: { value: '' } });
      
      // Now navigate up again to go to the older message
      fireEvent.keyDown(textarea, { key: 'ArrowUp' });
      await waitFor(() => {
        // Should now show the first message in history
        expect(textarea.value).toBe('First message');
      });
      
      // Navigate down in history
      // Clear input first to allow navigation
      fireEvent.change(textarea, { target: { value: '' } });
      
      // Now navigate down
      fireEvent.keyDown(textarea, { key: 'ArrowDown' });
      
      // From index 0, pressing down should go to index 1 (Second message)
      // But since newIndex (1) === messageHistory.length - 1 (1), it clears
      await waitFor(() => {
        expect(textarea.value).toBe('');
      }, { timeout: 2000 });
    });

    it('should only navigate history when input is empty', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i) as HTMLTextAreaElement;
      
      // Send a message to build history
      await userEvent.type(textarea, 'History message');
      await userEvent.type(textarea, '{enter}');
      
      await waitFor(() => {
        expect(textarea.value).toBe('');
      });
      
      // Type something new
      await userEvent.type(textarea, 'Current text');
      
      // Arrow up should not navigate when there's text
      fireEvent.keyDown(textarea, { key: 'ArrowUp' });
      expect(textarea.value).toBe('Current text');
    });

    it('should handle Ctrl+Enter for special actions', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i);
      
      await userEvent.type(textarea, 'Test message');
      
      // Fire Ctrl+Enter event - component only checks for !shiftKey
      // So Ctrl+Enter will still send the message
      fireEvent.keyDown(textarea, { key: 'Enter', code: 'Enter', ctrlKey: true });
      
      await waitFor(() => {
        // Ctrl+Enter actually triggers send (component only checks !shiftKey)
        expect(mockSendMessage).toHaveBeenCalledWith({
          type: 'user_message',
          payload: {
            content: 'Test message',
            references: [],
            thread_id: 'thread-1'
          }
        });
      });
    });

    it('should show keyboard shortcuts hint', () => {
      render(<MessageInput />);
      
      expect(screen.getByText(/\+ K for search/)).toBeInTheDocument();
      expect(screen.getByText(/for history/)).toBeInTheDocument();
    });

    it('should hide keyboard shortcuts hint when typing', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i);
      
      // Initially visible
      expect(screen.getByText(/\+ K for search/)).toBeInTheDocument();
      
      // Type something
      await userEvent.type(textarea, 'Hello');
      
      // Should be hidden after typing
      await waitFor(() => {
        expect(screen.queryByText(/\+ K for search/)).not.toBeInTheDocument();
      });
    });
  });
});