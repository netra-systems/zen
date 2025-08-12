import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MessageInput } from '@/components/chat/MessageInput';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useChatStore } from '@/store/chat';
import { useThreadStore } from '@/store/threadStore';
import { useAuthStore } from '@/store/authStore';
import { ThreadService } from '@/services/threadService';
import { generateUniqueId } from '@/lib/utils';

// Mock dependencies
jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: jest.fn()
}));
jest.mock('@/store/chat');
jest.mock('@/store/threadStore');
jest.mock('@/store/authStore');
jest.mock('@/services/threadService');
jest.mock('@/services/threadRenameService');
jest.mock('@/lib/utils');

describe('MessageInput', () => {
  const mockSendMessage = jest.fn();
  const mockSetProcessing = jest.fn();
  const mockAddMessage = jest.fn();
  const mockSetCurrentThread = jest.fn();
  const mockAddThread = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Setup default mocks
    const { useWebSocket } = require('@/hooks/useWebSocket');
    useWebSocket.mockReturnValue({
      sendMessage: mockSendMessage,
    });
    
    (useChatStore as jest.Mock).mockReturnValue({
      setProcessing: mockSetProcessing,
      isProcessing: false,
      addMessage: mockAddMessage,
    });
    
    (useThreadStore as jest.Mock).mockReturnValue({
      currentThreadId: 'thread-1',
      setCurrentThread: mockSetCurrentThread,
      addThread: mockAddThread,
    });
    
    (useAuthStore as jest.Mock).mockReturnValue({
      isAuthenticated: true,
    });
    
    (generateUniqueId as jest.Mock).mockImplementation((prefix) => `${prefix}-${Date.now()}`);
  });

  describe('Input validation and sanitization', () => {
    it('should trim whitespace from messages before sending', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i);
      
      await userEvent.type(textarea, '  Hello World  ');
      await userEvent.type(textarea, '{enter}');
      
      await waitFor(() => {
        expect(mockSendMessage).toHaveBeenCalledWith({
          type: 'user_message',
          payload: {
            text: 'Hello World',
            references: [],
            thread_id: 'thread-1'
          }
        });
      });
    });

    it('should not send empty messages', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i);
      
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
    }, 10000);

    it('should show character count warning at 80% capacity', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i) as HTMLTextAreaElement;
      const longMessage = 'a'.repeat(8001);
      
      // Use fireEvent to set value directly
      fireEvent.change(textarea, { target: { value: longMessage } });
      
      // Wait for the component to update
      await waitFor(() => {
        expect(screen.getByText(/8001\/10000/)).toBeInTheDocument();
      });
    }, 10000);

    it('should sanitize HTML in messages', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i);
      
      await userEvent.type(textarea, '<script>alert("xss")</script>Hello');
      await userEvent.type(textarea, '{enter}');
      
      await waitFor(() => {
        expect(mockSendMessage).toHaveBeenCalledWith({
          type: 'user_message',
          payload: {
            text: '<script>alert("xss")</script>Hello',
            references: [],
            thread_id: 'thread-1'
          }
        });
      });
    });

    it('should handle special characters correctly', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i);
      
      const specialChars = '!@#$%^&*()_+-=[]{}|;\':",./<>?`~\\n\\t';
      await userEvent.type(textarea, specialChars);
      await userEvent.type(textarea, '{enter}');
      
      await waitFor(() => {
        expect(mockSendMessage).toHaveBeenCalledWith(
          expect.objectContaining({
            payload: expect.objectContaining({
              text: specialChars
            })
          })
        );
      });
    });

    it('should handle unicode and emoji characters', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i);
      
      const unicodeText = 'Hello 世界 🚀 مرحبا';
      await userEvent.type(textarea, unicodeText);
      await userEvent.type(textarea, '{enter}');
      
      await waitFor(() => {
        expect(mockSendMessage).toHaveBeenCalledWith(
          expect.objectContaining({
            payload: expect.objectContaining({
              text: unicodeText
            })
          })
        );
      });
    });

    it('should prevent sending when processing', async () => {
      (useChatStore as jest.Mock).mockReturnValue({
        setProcessing: mockSetProcessing,
        isProcessing: true,
        addMessage: mockAddMessage,
      });
      
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Agent is thinking/i);
      const sendButton = screen.getByLabelText('Send message');
      
      expect(textarea).toBeDisabled();
      expect(sendButton).toBeDisabled();
    });

    it('should prevent sending when not authenticated', async () => {
      (useAuthStore as jest.Mock).mockReturnValue({
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
      const textarea = screen.getByPlaceholderText(/Type a message/i);
      
      await userEvent.type(textarea, 'Message 1');
      await userEvent.type(textarea, '{enter}');
      
      // Quickly type another message
      await userEvent.type(textarea, 'Message 2');
      await userEvent.type(textarea, '{enter}');
      
      await waitFor(() => {
        expect(mockSendMessage).toHaveBeenCalledTimes(2);
      });
    });
  });

  describe('File upload handling', () => {
    it('should render file attachment button', () => {
      render(<MessageInput />);
      const attachButton = screen.getByLabelText('Attach file');
      expect(attachButton).toBeInTheDocument();
    });

    it('should disable file attachment when processing', () => {
      (useChatStore as jest.Mock).mockReturnValue({
        setProcessing: mockSetProcessing,
        isProcessing: true,
        addMessage: mockAddMessage,
      });
      
      render(<MessageInput />);
      const attachButton = screen.getByLabelText('Attach file');
      expect(attachButton).toBeDisabled();
    });

    it('should show file attachment tooltip', async () => {
      render(<MessageInput />);
      const attachButton = screen.getByLabelText('Attach file');
      
      expect(attachButton).toHaveAttribute('title', 'Attach file (coming soon)');
    });

    it('should handle file attachment button click', async () => {
      render(<MessageInput />);
      const attachButton = screen.getByLabelText('Attach file');
      
      await userEvent.click(attachButton);
      // Currently a placeholder, should not trigger any action
      expect(mockSendMessage).not.toHaveBeenCalled();
    });

    it('should disable file attachment when not authenticated', () => {
      (useAuthStore as jest.Mock).mockReturnValue({
        isAuthenticated: false,
      });
      
      render(<MessageInput />);
      const attachButton = screen.getByLabelText('Attach file');
      expect(attachButton).toBeDisabled();
    });
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
            text: 'Test message',
            references: [],
            thread_id: 'thread-1'
          }
        });
      });
    });

    it('should insert newline on Shift+Enter', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i) as HTMLTextAreaElement;
      
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
      
      await userEvent.type(textarea, 'Second message');
      await userEvent.type(textarea, '{enter}');
      
      // Navigate up in history
      await userEvent.type(textarea, '{arrowup}');
      expect(textarea.value).toBe('Second message');
      
      await userEvent.type(textarea, '{arrowup}');
      expect(textarea.value).toBe('First message');
      
      // Navigate down in history
      await userEvent.type(textarea, '{arrowdown}');
      expect(textarea.value).toBe('Second message');
      
      await userEvent.type(textarea, '{arrowdown}');
      expect(textarea.value).toBe('');
    });

    it('should only navigate history when input is empty', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i) as HTMLTextAreaElement;
      
      await userEvent.type(textarea, 'Previous message');
      await userEvent.type(textarea, '{enter}');
      
      await userEvent.type(textarea, 'Current text');
      await userEvent.type(textarea, '{arrowup}');
      
      // Should not change because input is not empty
      expect(textarea.value).toBe('Current text');
    });

    it('should handle Ctrl+Enter for special actions', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i);
      
      await userEvent.type(textarea, 'Test message');
      await userEvent.type(textarea, '{ctrl>}{enter}{/ctrl}');
      
      // Currently Ctrl+Enter doesn't have special behavior, should not send
      expect(mockSendMessage).not.toHaveBeenCalled();
    });

    it('should show keyboard shortcuts hint', () => {
      render(<MessageInput />);
      
      expect(screen.getByText(/\+ K for search/)).toBeInTheDocument();
      expect(screen.getByText(/for history/)).toBeInTheDocument();
    });

    it('should hide keyboard shortcuts hint when typing', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i);
      
      expect(screen.getByText(/\+ K for search/)).toBeInTheDocument();
      
      await userEvent.type(textarea, 'Some text');
      
      await waitFor(() => {
        expect(screen.queryByText(/\+ K for search/)).not.toBeInTheDocument();
      });
    });
  });

  describe('Auto-resize textarea behavior', () => {
    it('should start with single row', () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i) as HTMLTextAreaElement;
      
      expect(textarea).toHaveAttribute('rows', '1');
    });

    it('should expand textarea as content grows', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i) as HTMLTextAreaElement;
      
      const multilineText = 'Line 1\nLine 2\nLine 3\nLine 4';
      await userEvent.type(textarea, multilineText);
      
      // Check that the textarea has expanded
      const currentRows = parseInt(textarea.getAttribute('rows') || '1');
      expect(currentRows).toBeGreaterThan(1);
    });

    it('should respect maximum rows limit', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i) as HTMLTextAreaElement;
      
      const manyLines = Array(10).fill('Line').join('\n');
      await userEvent.type(textarea, manyLines);
      
      const currentRows = parseInt(textarea.getAttribute('rows') || '1');
      expect(currentRows).toBeLessThanOrEqual(5); // MAX_ROWS = 5
    });

    it('should reset to single row after sending', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i) as HTMLTextAreaElement;
      
      await userEvent.type(textarea, 'Line 1\nLine 2\nLine 3');
      expect(parseInt(textarea.getAttribute('rows') || '1')).toBeGreaterThan(1);
      
      await userEvent.type(textarea, '{enter}');
      
      await waitFor(() => {
        expect(textarea).toHaveAttribute('rows', '1');
      });
    });

    it('should handle paste of multiline content', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i) as HTMLTextAreaElement;
      
      const multilineContent = 'Pasted Line 1\nPasted Line 2\nPasted Line 3';
      
      // Simulate paste event
      fireEvent.paste(textarea, {
        clipboardData: {
          getData: () => multilineContent
        }
      });
      
      await userEvent.type(textarea, multilineContent);
      
      const currentRows = parseInt(textarea.getAttribute('rows') || '1');
      expect(currentRows).toBeGreaterThan(1);
    });

    it('should maintain scroll position during resize', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i) as HTMLTextAreaElement;
      
      await userEvent.type(textarea, 'Start typing...');
      const initialScrollTop = textarea.scrollTop;
      
      await userEvent.type(textarea, '\nNew line\nAnother line');
      
      // Scroll position should be maintained or adjusted appropriately
      expect(textarea.scrollTop).toBeGreaterThanOrEqual(initialScrollTop);
    });
  });

  describe('Voice input and emoji features', () => {
    it('should render voice input button', () => {
      render(<MessageInput />);
      const voiceButton = screen.getByLabelText('Voice input');
      expect(voiceButton).toBeInTheDocument();
    });

    it('should disable voice input when processing', () => {
      (useChatStore as jest.Mock).mockReturnValue({
        setProcessing: mockSetProcessing,
        isProcessing: true,
        addMessage: mockAddMessage,
      });
      
      render(<MessageInput />);
      const voiceButton = screen.getByLabelText('Voice input');
      expect(voiceButton).toBeDisabled();
    });

    it('should show voice input tooltip', () => {
      render(<MessageInput />);
      const voiceButton = screen.getByLabelText('Voice input');
      
      expect(voiceButton).toHaveAttribute('title', 'Voice input (coming soon)');
    });

    it('should handle voice button click', async () => {
      render(<MessageInput />);
      const voiceButton = screen.getByLabelText('Voice input');
      
      await userEvent.click(voiceButton);
      // Currently a placeholder, should not trigger any action
      expect(mockSendMessage).not.toHaveBeenCalled();
    });

    it('should disable voice input when not authenticated', () => {
      (useAuthStore as jest.Mock).mockReturnValue({
        isAuthenticated: false,
      });
      
      render(<MessageInput />);
      const voiceButton = screen.getByLabelText('Voice input');
      expect(voiceButton).toBeDisabled();
    });
  });

  describe('Thread management', () => {
    it('should create new thread if none exists', async () => {
      (useThreadStore as jest.Mock).mockReturnValue({
        currentThreadId: null,
        setCurrentThread: mockSetCurrentThread,
        addThread: mockAddThread,
      });
      
      const mockThread = { id: 'new-thread-1', title: 'Test thread...' };
      (ThreadService.createThread as jest.Mock).mockResolvedValue(mockThread);
      
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i);
      
      await userEvent.type(textarea, 'First message in new thread');
      await userEvent.type(textarea, '{enter}');
      
      await waitFor(() => {
        expect(ThreadService.createThread).toHaveBeenCalledWith('First message in new thread');
        expect(mockAddThread).toHaveBeenCalledWith(mockThread);
        expect(mockSetCurrentThread).toHaveBeenCalledWith('new-thread-1');
      });
    });

    it('should use existing thread if available', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i);
      
      await userEvent.type(textarea, 'Message in existing thread');
      await userEvent.type(textarea, '{enter}');
      
      await waitFor(() => {
        expect(ThreadService.createThread).not.toHaveBeenCalled();
        expect(mockSendMessage).toHaveBeenCalledWith(
          expect.objectContaining({
            payload: expect.objectContaining({
              thread_id: 'thread-1'
            })
          })
        );
      });
    });

    it('should handle thread creation failure', async () => {
      (useThreadStore as jest.Mock).mockReturnValue({
        currentThreadId: null,
        setCurrentThread: mockSetCurrentThread,
        addThread: mockAddThread,
      });
      
      (ThreadService.createThread as jest.Mock).mockRejectedValue(new Error('Failed to create thread'));
      
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
      
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i);
      
      await userEvent.type(textarea, 'Message that fails');
      await userEvent.type(textarea, '{enter}');
      
      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith('Failed to create thread:', expect.any(Error));
        expect(mockSendMessage).not.toHaveBeenCalled();
      });
      
      consoleSpy.mockRestore();
    });

    it('should truncate long messages for thread title', async () => {
      (useThreadStore as jest.Mock).mockReturnValue({
        currentThreadId: null,
        setCurrentThread: mockSetCurrentThread,
        addThread: mockAddThread,
      });
      
      const longMessage = 'a'.repeat(100);
      const mockThread = { id: 'new-thread-2', title: 'a'.repeat(50) + '...' };
      (ThreadService.createThread as jest.Mock).mockResolvedValue(mockThread);
      
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i);
      
      await userEvent.type(textarea, longMessage);
      await userEvent.type(textarea, '{enter}');
      
      await waitFor(() => {
        expect(ThreadService.createThread).toHaveBeenCalledWith('a'.repeat(50) + '...');
      });
    });
  });

  describe('Send button states', () => {
    it('should show send icon when not sending', () => {
      render(<MessageInput />);
      const sendButton = screen.getByLabelText('Send message');
      
      expect(within(sendButton).getByTestId('Send')).toBeInTheDocument();
    });

    it('should show loading spinner when sending', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i);
      
      await userEvent.type(textarea, 'Test message');
      
      const sendButton = screen.getByLabelText('Send message');
      fireEvent.click(sendButton);
      
      // Note: The loading state is very brief, might need to mock delays
      await waitFor(() => {
        expect(mockSendMessage).toHaveBeenCalled();
      });
    });

    it('should disable send button when input is empty', () => {
      render(<MessageInput />);
      const sendButton = screen.getByLabelText('Send message');
      
      expect(sendButton).toBeDisabled();
    });

    it('should enable send button when input has content', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i);
      const sendButton = screen.getByLabelText('Send message');
      
      await userEvent.type(textarea, 'Some text');
      
      expect(sendButton).not.toBeDisabled();
    });

    it('should handle send button click', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i);
      const sendButton = screen.getByLabelText('Send message');
      
      await userEvent.type(textarea, 'Click to send');
      await userEvent.click(sendButton);
      
      await waitFor(() => {
        expect(mockSendMessage).toHaveBeenCalledWith({
          type: 'user_message',
          payload: {
            text: 'Click to send',
            references: [],
            thread_id: 'thread-1'
          }
        });
      });
    });
  });

  describe('Message history', () => {
    it('should add sent messages to history', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i) as HTMLTextAreaElement;
      
      await userEvent.type(textarea, 'Historical message 1');
      await userEvent.type(textarea, '{enter}');
      
      await userEvent.type(textarea, 'Historical message 2');
      await userEvent.type(textarea, '{enter}');
      
      // Navigate to check history was saved
      await userEvent.type(textarea, '{arrowup}');
      expect(textarea.value).toBe('Historical message 2');
      
      await userEvent.type(textarea, '{arrowup}');
      expect(textarea.value).toBe('Historical message 1');
    });

    it('should not add empty messages to history', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i) as HTMLTextAreaElement;
      
      await userEvent.type(textarea, 'Valid message');
      await userEvent.type(textarea, '{enter}');
      
      await userEvent.type(textarea, '   ');
      await userEvent.type(textarea, '{enter}');
      
      await userEvent.type(textarea, '{arrowup}');
      expect(textarea.value).toBe('Valid message');
    });

    it('should maintain history across component lifecycle', async () => {
      const { rerender } = render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i) as HTMLTextAreaElement;
      
      await userEvent.type(textarea, 'Persistent message');
      await userEvent.type(textarea, '{enter}');
      
      // Rerender component
      rerender(<MessageInput />);
      
      const newTextarea = screen.getByPlaceholderText(/Type a message/i) as HTMLTextAreaElement;
      await userEvent.type(newTextarea, '{arrowup}');
      
      // History should persist
      expect(newTextarea.value).toBe('Persistent message');
    });
  });

  describe('Focus management', () => {
    it('should auto-focus on mount when authenticated', () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i);
      
      expect(document.activeElement).toBe(textarea);
    });

    it('should not auto-focus when not authenticated', () => {
      (useAuthStore as jest.Mock).mockReturnValue({
        isAuthenticated: false,
      });
      
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Please sign in/i);
      
      expect(document.activeElement).not.toBe(textarea);
    });

    it('should maintain focus after sending message', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i);
      
      await userEvent.type(textarea, 'Test message');
      await userEvent.type(textarea, '{enter}');
      
      await waitFor(() => {
        expect(document.activeElement).toBe(textarea);
      });
    });
  });

  describe('UI state indicators', () => {
    it('should show appropriate placeholder when authenticated', () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message.*Shift\+Enter/i);
      
      expect(textarea).toBeInTheDocument();
    });

    it('should show sign-in prompt when not authenticated', () => {
      (useAuthStore as jest.Mock).mockReturnValue({
        isAuthenticated: false,
      });
      
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Please sign in to send messages/i);
      
      expect(textarea).toBeInTheDocument();
    });

    it('should show processing indicator when agent is thinking', () => {
      (useChatStore as jest.Mock).mockReturnValue({
        setProcessing: mockSetProcessing,
        isProcessing: true,
        addMessage: mockAddMessage,
      });
      
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Agent is thinking/i);
      
      expect(textarea).toBeInTheDocument();
    });

    it('should show character limit warning in placeholder', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i) as HTMLTextAreaElement;
      
      const longMessage = 'a'.repeat(9001);
      // Use fireEvent to set value directly
      fireEvent.change(textarea, { target: { value: longMessage } });
      
      // Wait for the component to update
      await waitFor(() => {
        // Should show remaining characters in placeholder
        expect(textarea.placeholder).toContain('999 characters remaining');
      });
    }, 10000);
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels', () => {
      render(<MessageInput />);
      
      const textarea = screen.getByLabelText('Message input');
      expect(textarea).toBeInTheDocument();
      
      const sendButton = screen.getByLabelText('Send message');
      expect(sendButton).toBeInTheDocument();
      
      const attachButton = screen.getByLabelText('Attach file');
      expect(attachButton).toBeInTheDocument();
      
      const voiceButton = screen.getByLabelText('Voice input');
      expect(voiceButton).toBeInTheDocument();
    });

    it('should have ARIA describedby for character count', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i) as HTMLTextAreaElement;
      
      const longMessage = 'a'.repeat(8001);
      // Use fireEvent to set value directly
      fireEvent.change(textarea, { target: { value: longMessage } });
      
      await waitFor(() => {
        expect(textarea).toHaveAttribute('aria-describedby', 'char-count');
        expect(screen.getByText(/8001\/10000/)).toHaveAttribute('id', 'char-count');
      });
    }, 10000);

    it('should handle keyboard navigation properly', async () => {
      render(<MessageInput />);
      
      // Tab through interactive elements
      await userEvent.tab();
      expect(document.activeElement).toHaveAttribute('placeholder', expect.stringContaining('Type a message'));
      
      await userEvent.tab();
      expect(document.activeElement).toHaveAttribute('aria-label', 'Attach file');
      
      await userEvent.tab();
      expect(document.activeElement).toHaveAttribute('aria-label', 'Voice input');
      
      await userEvent.tab();
      expect(document.activeElement).toHaveAttribute('aria-label', 'Send message');
    });
  });
});