/**
 * MessageInput Message History Tests
 * Tests for message history functionality
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MessageInput } from '@/components/chat/MessageInput';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useChatStore } from '@/store/chat';
import { useThreadStore } from '@/store/threadStore';
import { useAuthStore } from '@/store/authStore';
import { generateUniqueId } from '@/lib/utils';

// Mock dependencies
jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: jest.fn()
}));
jest.mock('@/store/chat');
jest.mock('@/store/threadStore');
jest.mock('@/store/authStore');
jest.mock('@/lib/utils');

describe('MessageInput - Message History', () => {
  const mockSendMessage = jest.fn();
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
    
    // Setup default mocks
    (useWebSocket as jest.Mock).mockReturnValue({
      sendMessage: mockSendMessage,
    });
    
    (useChatStore as jest.Mock).mockReturnValue({
      setProcessing: mockChatStore.setProcessing,
      isProcessing: false,
      addMessage: mockChatStore.addMessage,
    });
    
    (useThreadStore as jest.Mock).mockReturnValue({
      currentThreadId: 'thread-1',
      setCurrentThread: mockThreadStore.setCurrentThread,
      addThread: mockThreadStore.addThread,
    });
    
    (useAuthStore as jest.Mock).mockReturnValue({
      isAuthenticated: true,
    });
    
    (generateUniqueId as jest.Mock).mockImplementation((prefix) => `${prefix}-${Date.now()}`);
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
            text: 'First message',
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