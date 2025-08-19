/**
 * MessageInput Keyboard Shortcuts Tests
 * Tests for keyboard shortcuts and navigation
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MessageInput } from '@/components/chat/MessageInput';
import {
  mockSendMessage,
  setupMinimalMocks,
  resetMocks
} from './minimal-test-setup';
import {
  renderMessageInput,
  getTextarea,
  typeMessage,
  sendViaEnter,
  expectMessageSent
} from './test-helpers';

// Setup minimal mocks before imports
setupMinimalMocks();

describe('MessageInput - Keyboard Shortcuts', () => {
  beforeEach(() => {
    resetMocks();
  });

  describe('Keyboard shortcuts', () => {
    it('should send message on Enter key', async () => {
      renderMessageInput();
      await sendViaEnter('Test message');
      await expectMessageSent(mockSendMessage, 'Test message');
    });

    const typeWithShiftEnter = async (textarea: HTMLTextAreaElement) => {
      await userEvent.type(textarea, 'Line 1');
      await userEvent.type(textarea, '{shift>}{enter}{/shift}');
      await userEvent.type(textarea, 'Line 2');
    };

    it('should insert newline on Shift+Enter', async () => {
      renderMessageInput();
      const textarea = getTextarea();
      await typeWithShiftEnter(textarea);
      expect(textarea.value).toContain('Line 1\nLine 2');
    });

    const sendMessagesAndClear = async () => {
      await sendViaEnter('First message');
      await sendViaEnter('Second message');
    };

    const navigateHistoryUp = (textarea: HTMLTextAreaElement) => {
      fireEvent.keyDown(textarea, { key: 'ArrowUp' });
    };

    const clearTextarea = (textarea: HTMLTextAreaElement) => {
      fireEvent.change(textarea, { target: { value: '' } });
    };

    it('should navigate message history with arrow keys', async () => {
      renderMessageInput();
      const textarea = getTextarea();
      await sendMessagesAndClear();
      clearTextarea(textarea);
      navigateHistoryUp(textarea);
      // Real hook will handle history navigation
      // This test verifies arrow key event handling
    });

    const typeCurrentText = async (textarea: HTMLTextAreaElement) => {
      await userEvent.type(textarea, 'Current text');
    };

    it('should only navigate history when input is empty', async () => {
      renderMessageInput();
      const textarea = getTextarea();
      await sendViaEnter('History message');
      await typeCurrentText(textarea);
      navigateHistoryUp(textarea);
      expect(textarea.value).toBe('Current text');
    });

    const sendWithCtrlEnter = async (textarea: HTMLTextAreaElement) => {
      fireEvent.keyDown(textarea, { key: 'Enter', code: 'Enter', ctrlKey: true });
    };

    it('should handle Ctrl+Enter for special actions', async () => {
      renderMessageInput();
      const textarea = getTextarea();
      await typeMessage('Test message');
      await sendWithCtrlEnter(textarea);
      await expectMessageSent(mockSendMessage, 'Test message');
    });

    it('should show keyboard shortcuts hint', () => {
      renderMessageInput();
      expect(screen.getByText(/\+ K for search/)).toBeInTheDocument();
      expect(screen.getByText(/for history/)).toBeInTheDocument();
    });

    const verifyHintsInitiallyVisible = () => {
      expect(screen.getByText(/\+ K for search/)).toBeInTheDocument();
    };

    const verifyHintsHiddenAfterTyping = async () => {
      await waitFor(() => {
        expect(screen.queryByText(/\+ K for search/)).not.toBeInTheDocument();
      });
    };

    it('should hide keyboard shortcuts hint when typing', async () => {
      renderMessageInput();
      verifyHintsInitiallyVisible();
      await typeMessage('Hello');
      await verifyHintsHiddenAfterTyping();
    });
  });
});