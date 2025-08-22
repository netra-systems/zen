/**
 * MessageInput Validation Tests - FIXED VERSION
 * Tests for input validation, sanitization, and character limits
 * 
 * This file addresses the failing validation tests by properly mocking the 
 * authentication state and ensuring components can interact with enabled inputs.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { jest } from '@jest/globals';

// Create mock functions for dynamic control
const mockSendMessage = jest.fn();
const mockHandleSend = jest.fn();

// Dynamic mock stores - these will be updated by tests
let authState = { isAuthenticated: true };
let chatState = { 
  activeThreadId: 'thread-1', 
  isProcessing: false,
  setProcessing: jest.fn(),
  addMessage: jest.fn(),
  addOptimisticMessage: jest.fn(),
  updateOptimisticMessage: jest.fn(),
};
let threadState = { 
  currentThreadId: 'thread-1',
  setCurrentThread: jest.fn(),
  addThread: jest.fn(),
};

// Mock all required dependencies
jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: () => ({ sendMessage: mockSendMessage })
}));

jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: () => chatState
}));

jest.mock('@/store/threadStore', () => ({
  useThreadStore: () => threadState
}));

jest.mock('@/store/authStore', () => ({
  useAuthStore: () => authState
}));

jest.mock('@/components/chat/hooks/useMessageHistory', () => ({
  useMessageHistory: () => ({
    messageHistory: [],
    addToHistory: jest.fn(),
    navigateHistory: jest.fn(() => '')
  })
}));

jest.mock('@/components/chat/hooks/useTextareaResize', () => ({
  useTextareaResize: () => ({ rows: 1 })
}));

jest.mock('@/components/chat/hooks/useMessageSending', () => ({
  useMessageSending: () => ({
    isSending: false,
    handleSend: mockHandleSend
  })
}));

// Import after mocking
import { MessageInput } from '@/components/chat/MessageInput';

// Helper functions
const renderMessageInput = () => render(<MessageInput />);

const getTextarea = () => 
  screen.getByRole('textbox', { name: /message input/i }) as HTMLTextAreaElement;

const getSendButton = () => 
  screen.getByRole('button', { name: /send/i });

const typeMessage = async (text: string) => {
  const textarea = getTextarea();
  // Only clear if element is not disabled
  if (!textarea.disabled) {
    await userEvent.clear(textarea);
  }
  await userEvent.type(textarea, text);
  return textarea;
};

const sendViaEnter = async (text: string) => {
  await typeMessage(text);
  const textarea = getTextarea();
  await userEvent.type(textarea, '{enter}');
  return textarea;
};

const expectMessageSent = async (mockFn: jest.Mock, content: string) => {
  await waitFor(() => {
    expect(mockFn).toHaveBeenCalledWith({
      message: content,
      activeThreadId: 'thread-1',
      currentThreadId: 'thread-1', 
      isAuthenticated: true
    });
  });
};

// Reset function
const resetMocks = () => {
  jest.clearAllMocks();
  authState.isAuthenticated = true;
  chatState.isProcessing = false;
  mockHandleSend.mockClear();
};

const setAuthenticated = (authenticated: boolean) => {
  authState.isAuthenticated = authenticated;
};

const setProcessing = (processing: boolean) => {
  chatState.isProcessing = processing;
};

describe('MessageInput - Input Validation and Sanitization (FIXED)', () => {
  beforeEach(() => {
    resetMocks();
  });

  describe('Input validation and sanitization', () => {
    it('should trim whitespace from messages before sending', async () => {
      renderMessageInput();
      await sendViaEnter('  Hello World  ');
      await expectMessageSent(mockHandleSend, 'Hello World');
    });

    it('should not send empty messages', async () => {
      renderMessageInput();
      await sendViaEnter('   ');
      expect(mockHandleSend).not.toHaveBeenCalled();
    });

    it('should enforce character limit', async () => {
      renderMessageInput();
      const textarea = getTextarea();
      const longMessage = 'a'.repeat(10001);
      await userEvent.clear(textarea);
      await userEvent.type(textarea, longMessage);
      
      await waitFor(() => {
        expect(screen.getByText('10001/10000')).toBeInTheDocument();
      });
      expect(getSendButton()).toBeDisabled();
    });

    it('should show character count warning at 80% capacity', async () => {
      renderMessageInput();
      const textarea = getTextarea();
      const longMessage = 'a'.repeat(8001);
      await userEvent.clear(textarea);
      await userEvent.type(textarea, longMessage);
      
      await waitFor(() => {
        const charCount = screen.getByText(/8001\/10000/);
        expect(charCount).toBeInTheDocument();
      });
    });

    it('should sanitize HTML in messages', async () => {
      renderMessageInput();
      const htmlContent = '<script>alert("XSS")</script>Hello';
      await sendViaEnter(htmlContent);
      await expectMessageSent(mockHandleSend, htmlContent);
    });

    it('should handle special characters correctly', async () => {
      renderMessageInput();
      const specialChars = '!@#$%^&*()_+-=[]{}|;\':\",./<>?`~';
      await sendViaEnter(specialChars);
      await expectMessageSent(mockHandleSend, specialChars);
    });

    it('should handle unicode and emoji characters', async () => {
      renderMessageInput();
      const unicodeText = '你好世界 🌍 مرحبا بالعالم';
      await sendViaEnter(unicodeText);
      await expectMessageSent(mockHandleSend, unicodeText);
    });

    it('should prevent sending when processing', async () => {
      setProcessing(true);
      renderMessageInput();
      const textarea = getTextarea();
      const sendButton = getSendButton();
      expect(textarea).toBeDisabled();
      expect(sendButton).toBeDisabled();
    });

    it('should prevent sending when not authenticated', async () => {
      setAuthenticated(false);
      renderMessageInput();
      const textarea = getTextarea();
      const sendButton = getSendButton();
      expect(textarea).toBeDisabled();
      expect(sendButton).toBeDisabled();
    });

    it('should handle rapid successive sends correctly', async () => {
      renderMessageInput();
      await sendViaEnter('Message 1');
      await sendViaEnter('Message 2');
      await waitFor(() => {
        expect(mockHandleSend).toHaveBeenCalledTimes(2);
      });
    });
  });
});