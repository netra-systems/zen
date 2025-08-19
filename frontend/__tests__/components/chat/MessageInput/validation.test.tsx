/**
 * MessageInput Validation Tests
 * Tests for input validation, sanitization, and character limits
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MessageInput } from '@/components/chat/MessageInput';
import {
  mockSendMessage,
  setupMinimalMocks,
  resetMocks,
  setProcessing,
  setAuthenticated
} from './minimal-test-setup';
import {
  renderMessageInput,
  getTextarea,
  getSendButton,
  typeMessage,
  sendViaEnter,
  expectMessageSent
} from './test-helpers';

// Setup minimal mocks before imports
setupMinimalMocks();

describe('MessageInput - Input Validation and Sanitization', () => {
  beforeEach(() => {
    resetMocks();
  });

  describe('Input validation and sanitization', () => {
    it('should trim whitespace from messages before sending', async () => {
      renderMessageInput();
      await sendViaEnter('  Hello World  ');
      await expectMessageSent(mockSendMessage, 'Hello World');
    });

    it('should not send empty messages', async () => {
      renderMessageInput();
      await sendViaEnter('   ');
      expect(mockSendMessage).not.toHaveBeenCalled();
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
      await expectMessageSent(mockSendMessage, htmlContent);
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
      await expectMessageSent(mockSendMessage, specialChars);
    });

    it('should handle unicode and emoji characters', async () => {
      renderMessageInput();
      const unicodeText = '你好世界 🌍 مرحبا بالعالم';
      await sendViaEnter(unicodeText);
      await expectMessageSent(mockSendMessage, unicodeText);
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
        expect(mockSendMessage).toHaveBeenCalledTimes(2);
      });
    });
  });
});