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
      
      // Now navigate down from index 0 to index 1
      fireEvent.keyDown(textarea, { key: 'ArrowDown' });
      
      // Should show the second message (index 1)
      await waitFor(() => {
        expect(textarea.value).toBe('Second message');
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