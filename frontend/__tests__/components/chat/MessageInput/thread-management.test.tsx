/**
 * MessageInput Thread Management Tests
 * Tests for thread creation and management functionality
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MessageInput } from '@/components/chat/MessageInput';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useThreadStore } from '@/store/threadStore';
import { useAuthStore } from '@/store/authStore';
import { ThreadService } from '@/services/threadService';
import { ThreadRenameService } from '@/services/threadRenameService';
import { generateUniqueId } from '@/lib/utils';

// Mock dependencies
jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: jest.fn()
}));
jest.mock('@/store/unified-chat');
jest.mock('@/store/threadStore');
jest.mock('@/store/authStore');
jest.mock('@/services/threadService', () => ({
  ThreadService: {
    listThreads: jest.fn().mockResolvedValue([]),
    createThread: jest.fn().mockResolvedValue({ 
      id: 'new-thread', 
      created_at: Math.floor(Date.now() / 1000), 
      updated_at: Math.floor(Date.now() / 1000),
      message_count: 0,
      metadata: { title: 'New Chat' }
    }),
    getThread: jest.fn().mockResolvedValue({
      id: 'test-thread',
      created_at: Math.floor(Date.now() / 1000),
      updated_at: Math.floor(Date.now() / 1000),
      message_count: 1,
      metadata: { title: 'Test Thread', renamed: false }
    }),
    deleteThread: jest.fn(),
    updateThread: jest.fn(),
    getThreadMessages: jest.fn().mockResolvedValue({ 
      messages: [], 
      thread_id: 'test', 
      total: 0, 
      limit: 50, 
      offset: 0 
    })
  }
}));
jest.mock('@/services/threadRenameService', () => ({
  ThreadRenameService: {
    autoRenameThread: jest.fn()
  }
}));
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
  
  const mockChatActions = {
    setActiveThread: jest.fn()
  };

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Setup default mocks
    (useWebSocket as jest.Mock).mockReturnValue({
      sendMessage: mockSendMessage,
    });
    
    (useUnifiedChatStore as jest.Mock).mockReturnValue({
      setProcessing: mockChatStore.setProcessing,
      isProcessing: false,
      addMessage: mockChatStore.addMessage,
      activeThreadId: 'thread-1',
      setActiveThread: mockChatActions.setActiveThread,
      addOptimisticMessage: jest.fn(),
      updateOptimisticMessage: jest.fn(),
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
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        setProcessing: mockChatStore.setProcessing,
        isProcessing: false,
        addMessage: mockChatStore.addMessage,
        activeThreadId: null,
        setActiveThread: mockChatActions.setActiveThread,
        addOptimisticMessage: jest.fn(),
        updateOptimisticMessage: jest.fn(),
      });
      
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
        expect(mockChatActions.setActiveThread).toHaveBeenCalledWith('new-thread-1');
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
            content: 'Test message',
            references: [],
            thread_id: 'thread-1'
          }
        });
      });
      
      expect(ThreadService.createThread).not.toHaveBeenCalled();
    });

    it('should handle thread creation failure', async () => {
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        setProcessing: mockChatStore.setProcessing,
        isProcessing: false,
        addMessage: mockChatStore.addMessage,
        activeThreadId: null,
        setActiveThread: mockChatActions.setActiveThread,
        addOptimisticMessage: jest.fn(),
        updateOptimisticMessage: jest.fn(),
      });
      
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
        expect(consoleSpy).toHaveBeenCalledWith('[ERROR]', 'Failed to send message:', expect.any(Error));
        expect(mockSendMessage).not.toHaveBeenCalled();
      });
      
      consoleSpy.mockRestore();
    });

    it('should truncate long messages for thread title', async () => {
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        setProcessing: mockChatStore.setProcessing,
        isProcessing: false,
        addMessage: mockChatStore.addMessage,
        activeThreadId: null,
        setActiveThread: mockChatActions.setActiveThread,
        addOptimisticMessage: jest.fn(),
        updateOptimisticMessage: jest.fn(),
      });
      
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