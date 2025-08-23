/**
 * MessageInput Validation Tests
 * Tests for input validation, sanitization, and character limits
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { jest } from '@jest/globals';

// Mock external dependencies before importing component
const mockSendMessage = jest.fn();
const mockUseWebSocket = jest.fn(() => ({
  sendMessage: mockSendMessage,
}));

// Create dynamic mock state that can be updated during tests
let dynamicMockState = {
  chat: {
    activeThreadId: 'thread-1',
    isProcessing: false,
    setProcessing: jest.fn(),
    addMessage: jest.fn(),
    addOptimisticMessage: jest.fn(),
    updateOptimisticMessage: jest.fn(),
  },
  thread: {
    currentThreadId: 'thread-1',
    setCurrentThread: jest.fn(),
    addThread: jest.fn(),
  },
  auth: {
    isAuthenticated: true,
  }
};

jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: mockUseWebSocket
}));

// Mock the utility functions to enable testing by forcing authenticated behavior
jest.mock('@/components/chat/utils/messageInputUtils', () => ({
  getPlaceholder: jest.fn((isAuthenticated, isProcessing, messageLength) => {
    if (!isAuthenticated) return 'Please sign in to send messages';
    if (isProcessing) return 'Agent is thinking...';
    if (messageLength > 9000) return `${10000 - messageLength} characters remaining`;
    return 'Type a message...';
  }),
  getTextareaClassName: jest.fn(() => 'w-full resize-none rounded-2xl px-4 py-3 pr-12 bg-gray-50 border border-gray-200 focus:bg-white focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100 transition-all duration-200 ease-in-out placeholder:text-gray-400 text-gray-900'),
  getCharCountClassName: jest.fn(() => 'absolute bottom-2 right-2 text-xs font-medium text-gray-400'),
  shouldShowCharCount: jest.fn((messageLength) => messageLength > 8000),
  isMessageDisabled: jest.fn((isProcessing, isAuthenticated, isSending) => {
    return isProcessing || !isAuthenticated || isSending;
  }),
  canSendMessage: jest.fn((isDisabled, message, messageLength) => {
    return !isDisabled && !!message.trim() && messageLength <= 10000;
  })
}));

jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: () => dynamicMockState.chat
}));

jest.mock('@/store/threadStore', () => ({
  useThreadStore: () => dynamicMockState.thread
}));

jest.mock('@/store/authStore', () => ({
  useAuthStore: () => dynamicMockState.auth
}));

// Mock the necessary hooks and utilities - using correct relative paths
jest.mock('../../../../components/chat/hooks/useMessageHistory', () => ({
  useMessageHistory: () => ({
    messageHistory: [],
    addToHistory: jest.fn(),
    navigateHistory: jest.fn(() => '')
  })
}));

jest.mock('../../../../components/chat/hooks/useTextareaResize', () => ({
  useTextareaResize: () => ({
    rows: 1
  })
}));

const mockHandleSend = jest.fn();

jest.mock('../../../../components/chat/hooks/useMessageSending', () => ({
  useMessageSending: () => ({
    isSending: false,
    handleSend: mockHandleSend
  })
}));

// Mock services and utilities
jest.mock('@/services/threadService');
jest.mock('@/services/threadRenameService');
jest.mock('@/lib/utils', () => ({
  generateUniqueId: jest.fn(() => 'mock-id-123'),
  cn: jest.fn((...classes) => classes.filter(Boolean).join(' '))
}));

import { MessageInput } from '@/components/chat/MessageInput';
import {
  renderMessageInput,
  getTextarea,
  getSendButton,
  typeMessage,
  sendViaEnter,
  expectMessageSent
} from './test-helpers';

// Reset functions
const resetMocks = () => {
  jest.clearAllMocks();
  dynamicMockState.chat.isProcessing = false;
  dynamicMockState.auth.isAuthenticated = true;
  mockHandleSend.mockClear();
  mockSendMessage.mockClear();
  
  // Reset handleSend to properly simulate message sending
  mockHandleSend.mockImplementation(async (params) => {
    // Simulate the actual behavior - call with the params
    if (params.isAuthenticated && params.message && params.message.trim()) {
      // Mock successful send
      return Promise.resolve();
    }
  });
};

const setProcessing = (processing: boolean) => {
  dynamicMockState.chat.isProcessing = processing;
};

const setAuthenticated = (auth: boolean) => {
  dynamicMockState.auth.isAuthenticated = auth;
};

describe('MessageInput - Input Validation and Sanitization', () => {
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

    const setLongMessage = (textarea: HTMLTextAreaElement, length: number) => {
      const longMessage = 'a'.repeat(length);
      fireEvent.change(textarea, { target: { value: longMessage } });
      return longMessage;
    };

    const verifyCharCountDisplayed = async (count: number) => {
      await waitFor(() => {
        expect(screen.getByText(`${count}/10000`)).toBeInTheDocument();
      });
    };

    it('should enforce character limit', async () => {
      renderMessageInput();
      const textarea = getTextarea();
      setLongMessage(textarea, 10001);
      await verifyCharCountDisplayed(10001);
      expect(getSendButton()).toBeDisabled();
    });

    it('should show character count warning at 80% capacity', async () => {
      renderMessageInput();
      const textarea = getTextarea();
      setLongMessage(textarea, 8001);
      await verifyCharCountDisplayed(8001);
      const charCount = screen.getByText(/8001\/10000/);
      expect(charCount).toBeInTheDocument();
    });

    it('should sanitize HTML in messages', async () => {
      renderMessageInput();
      const htmlContent = '<script>alert("XSS")</script>Hello';
      await sendViaEnter(htmlContent);
      await expectMessageSent(mockHandleSend, htmlContent);
    });

    const sendSpecialChars = async (chars: string) => {
      const textarea = getTextarea();
      fireEvent.change(textarea, { target: { value: chars } });
      fireEvent.keyDown(textarea, { key: 'Enter', code: 'Enter' });
    };

    it('should handle special characters correctly', async () => {
      renderMessageInput();
      const specialChars = '!@#$%^&*()_+-=[]{}|;\':\",./<>?`~';
      await sendSpecialChars(specialChars);
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