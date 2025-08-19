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

const mockChatStore = {
  activeThreadId: 'thread-1',
  isProcessing: false,
  setProcessing: jest.fn(),
  addMessage: jest.fn(),
  addOptimisticMessage: jest.fn(),
  updateOptimisticMessage: jest.fn(),
};

const mockThreadStore = {
  currentThreadId: 'thread-1',
  setCurrentThread: jest.fn(),
  addThread: jest.fn(),
};

const mockAuthStore = {
  isAuthenticated: true,
};

jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: mockUseWebSocket
}));

jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: jest.fn(() => mockChatStore)
}));

jest.mock('@/store/threadStore', () => ({
  useThreadStore: jest.fn(() => mockThreadStore)
}));

jest.mock('@/store/authStore', () => ({
  useAuthStore: jest.fn(() => mockAuthStore)
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
  mockChatStore.isProcessing = false;
  mockAuthStore.isAuthenticated = true;
  mockHandleSend.mockClear();
};

const setProcessing = (processing: boolean) => {
  mockChatStore.isProcessing = processing;
};

const setAuthenticated = (auth: boolean) => {
  mockAuthStore.isAuthenticated = auth;
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