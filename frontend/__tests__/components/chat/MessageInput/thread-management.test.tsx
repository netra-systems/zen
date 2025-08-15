/**
 * MessageInput Thread Management Tests
 * Tests for thread creation and management functionality
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
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
jest.mock('@/lib/utils');

describe('MessageInput - Thread Management', () => {
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

  describe('Thread management', () => {
    it('should create new thread if none exists', async () => {
      (useThreadStore as jest.Mock).mockReturnValue({
        currentThreadId: null,
        setCurrentThread: mockThreadStore.setCurrentThread,
        addThread: mockThreadStore.addThread,
      });
      
      (ThreadService.createThread as jest.Mock).mockResolvedValue({
        id: 'new-thread-1',
        title: 'Test message...',
      });
      
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i);
      
      await userEvent.type(textarea, 'Test message');
      await userEvent.type(textarea, '{enter}');
      
      await waitFor(() => {
        expect(ThreadService.createThread).toHaveBeenCalledWith('Test message');
        expect(mockThreadStore.addThread).toHaveBeenCalled();
        expect(mockThreadStore.setCurrentThread).toHaveBeenCalledWith('new-thread-1');
      });
    });

    it('should use existing thread if available', async () => {
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
      
      expect(ThreadService.createThread).not.toHaveBeenCalled();
    });

    it('should handle thread creation failure', async () => {
      (useThreadStore as jest.Mock).mockReturnValue({
        currentThreadId: null,
        setCurrentThread: mockThreadStore.setCurrentThread,
        addThread: mockThreadStore.addThread,
      });
      
      (ThreadService.createThread as jest.Mock).mockRejectedValue(new Error('Failed to create thread'));
      
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
      
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i);
      
      await userEvent.type(textarea, 'Test message');
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
        setCurrentThread: mockThreadStore.setCurrentThread,
        addThread: mockThreadStore.addThread,
      });
      
      const longMessage = 'a'.repeat(100);
      const expectedTitle = 'a'.repeat(50) + '...';
      
      (ThreadService.createThread as jest.Mock).mockResolvedValue({
        id: 'new-thread-1',
        title: expectedTitle,
      });
      
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i);
      
      await userEvent.type(textarea, longMessage);
      await userEvent.type(textarea, '{enter}');
      
      await waitFor(() => {
        expect(ThreadService.createThread).toHaveBeenCalledWith(expectedTitle);
      }, { timeout: 10000 });
    }, 10000);
  });
});