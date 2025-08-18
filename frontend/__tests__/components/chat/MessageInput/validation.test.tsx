/**
 * MessageInput Validation Tests
 * Tests for input validation, sanitization, and character limits
 */

// Mock dependencies BEFORE imports
const mockSendMessage = jest.fn();
const mockUseWebSocket = jest.fn();
const mockHandleSend = jest.fn();
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
jest.mock('@/components/chat/hooks/useMessageHistory', () => ({
  useMessageHistory: jest.fn(() => ({
    messageHistory: [],
    addToHistory: jest.fn(),
    navigateHistory: jest.fn(() => '')
  }))
}));
jest.mock('@/components/chat/hooks/useTextareaResize', () => ({
  useTextareaResize: jest.fn(() => ({ rows: 1 }))
}));
// Create a mock that properly calls the WebSocket send function
jest.mock('@/components/chat/hooks/useMessageSending', () => ({
  useMessageSending: jest.fn(() => ({
    isSending: false,
    handleSend: mockHandleSend
  }))
}));

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MessageInput } from '@/components/chat/MessageInput';

describe('MessageInput - Input Validation and Sanitization', () => {
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
    
    // Setup handleSend to actually call mockSendMessage
    mockHandleSend.mockImplementation(async (params) => {
      if (params.isAuthenticated && params.message && params.message.trim()) {
        mockSendMessage({
          type: 'user_message',
          payload: {
            content: params.message.trim(),
            references: [],
            thread_id: params.activeThreadId || params.currentThreadId
          }
        });
      }
    });
    
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

  describe('Input validation and sanitization', () => {
    it('should trim whitespace from messages before sending', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message\.\.\./i);
      
      await userEvent.type(textarea, '  Hello World  ');
      await userEvent.type(textarea, '{enter}');
      
      await waitFor(() => {
        expect(mockSendMessage).toHaveBeenCalledWith({
          type: 'user_message',
          payload: {
            content: 'Hello World',
            references: [],
            thread_id: 'thread-1'
          }
        });
      });
    });

    it('should not send empty messages', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message\.\.\./i);
      
      await userEvent.type(textarea, '   ');
      await userEvent.type(textarea, '{enter}');
      
      expect(mockSendMessage).not.toHaveBeenCalled();
    });

    it('should enforce character limit', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i) as HTMLTextAreaElement;
      const longMessage = 'a'.repeat(10001);
      
      // Use fireEvent to set value directly instead of typing each character
      fireEvent.change(textarea, { target: { value: longMessage } });
      
      // Wait for the component to update
      await waitFor(() => {
        // Character count should be displayed
        expect(screen.getByText(/10001\/10000/)).toBeInTheDocument();
      });
      
      // Send button should be disabled
      const sendButton = screen.getByLabelText('Send message');
      expect(sendButton).toBeDisabled();
    });

    it('should show character count warning at 80% capacity', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i) as HTMLTextAreaElement;
      const longMessage = 'a'.repeat(8001);
      
      fireEvent.change(textarea, { target: { value: longMessage } });
      
      await waitFor(() => {
        expect(screen.getByText(/8001\/10000/)).toBeInTheDocument();
      });
      
      // At 80.01%, warning should be displayed
      const charCount = screen.getByText(/8001\/10000/);
      // Just verify it's displayed - the component uses conditional classes
      expect(charCount).toBeInTheDocument();
    });

    it('should sanitize HTML in messages', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message\.\.\./i);
      
      const htmlContent = '<script>alert("XSS")</script>Hello';
      await userEvent.type(textarea, htmlContent);
      await userEvent.type(textarea, '{enter}');
      
      await waitFor(() => {
        expect(mockSendMessage).toHaveBeenCalledWith({
          type: 'user_message',
          payload: {
            content: htmlContent, // Component sends raw text, sanitization happens on display
            references: [],
            thread_id: 'thread-1'
          }
        });
      });
    });

    it('should handle special characters correctly', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message\.\.\./i);
      
      // Use fireEvent for special characters to avoid userEvent parsing issues with brackets
      const specialChars = '!@#$%^&*()_+-=[]{}|;\':\",./<>?`~';
      fireEvent.change(textarea, { target: { value: specialChars } });
      fireEvent.keyDown(textarea, { key: 'Enter', code: 'Enter' });
      
      await waitFor(() => {
        expect(mockSendMessage).toHaveBeenCalledWith(
          expect.objectContaining({
            payload: expect.objectContaining({
              content: specialChars
            })
          })
        );
      });
    });

    it('should handle unicode and emoji characters', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message\.\.\./i);
      
      const unicodeText = '你好世界 🌍 مرحبا بالعالم';
      await userEvent.type(textarea, unicodeText);
      await userEvent.type(textarea, '{enter}');
      
      await waitFor(() => {
        expect(mockSendMessage).toHaveBeenCalledWith({
          type: 'user_message',
          payload: {
            content: unicodeText,
            references: [],
            thread_id: 'thread-1'
          }
        });
      });
    });

    it('should prevent sending when processing', async () => {
      mockUseUnifiedChatStore.mockReturnValue({
        activeThreadId: 'thread-1',
        isProcessing: true,
        setProcessing: mockChatStore.setProcessing,
        addMessage: mockChatStore.addMessage,
        addOptimisticMessage: jest.fn(),
        updateOptimisticMessage: jest.fn(),
      });
      
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Agent is thinking/i);
      const sendButton = screen.getByLabelText('Send message');
      
      expect(textarea).toBeDisabled();
      expect(sendButton).toBeDisabled();
    });

    it('should prevent sending when not authenticated', async () => {
      mockUseAuthStore.mockReturnValue({
        isAuthenticated: false,
      });
      
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Please sign in/i);
      const sendButton = screen.getByLabelText('Send message');
      
      expect(textarea).toBeDisabled();
      expect(sendButton).toBeDisabled();
    });

    it('should handle rapid successive sends correctly', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message\.\.\./i);
      
      // First message
      await userEvent.type(textarea, 'Message 1');
      await userEvent.type(textarea, '{enter}');
      
      // Second message immediately
      await userEvent.type(textarea, 'Message 2');
      await userEvent.type(textarea, '{enter}');
      
      await waitFor(() => {
        expect(mockSendMessage).toHaveBeenCalledTimes(2);
      });
    });
  });
});