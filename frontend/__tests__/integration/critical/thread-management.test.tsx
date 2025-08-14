/**
 * Thread Management Integration Tests
 * Tests for thread creation, switching, and message synchronization
 */

import React from 'react';
import { render, waitFor, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

// Import stores
import { useChatStore } from '@/store/chatStore';
import { useThreadStore } from '@/store/threadStore';

// Import test utilities
import { TestProviders } from '../../test-utils/providers';

// Mock services
jest.mock('@/services/threadService', () => ({
  ThreadService: {
    createThread: jest.fn(),
    getThread: jest.fn(),
    listThreads: jest.fn(),
  }
}));

jest.mock('@/services/messageService', () => ({
  messageService: {
    sendMessage: jest.fn(),
    getMessages: jest.fn(),
    createThread: jest.fn(),
  }
}));

describe('Thread Management Integration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Reset stores
    useChatStore.setState({ messages: [], currentThread: null });
    useThreadStore.setState({ threads: [], currentThreadId: null, currentThread: null });
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('Thread Creation and Message Sync', () => {
    it('should create thread and sync with messages', async () => {
      const { ThreadService } = require('@/services/threadService');
      const { messageService } = require('@/services/messageService');
      
      const mockThread = {
        id: 'thread-456',
        title: 'New Thread',
        created_at: Date.now()
      };
      
      ThreadService.createThread.mockResolvedValue(mockThread);
      
      // Create thread through service
      const thread = await ThreadService.createThread('New Thread');
      
      // Update store
      useThreadStore.getState().addThread(thread);
      useThreadStore.getState().setCurrentThread(thread.id);
      
      // Verify thread is active
      expect(useThreadStore.getState().currentThreadId).toBe('thread-456');
      
      // Send message to thread
      const mockMessage = {
        id: 'msg-1',
        thread_id: 'thread-456',
        content: 'Test message',
        role: 'user'
      };
      
      messageService.sendMessage.mockResolvedValue(mockMessage);
      
      await messageService.sendMessage('thread-456', 'Test message');
      
      // Update chat store
      useChatStore.getState().addMessage(mockMessage);
      
      expect(useChatStore.getState().messages).toHaveLength(1);
      expect(useChatStore.getState().messages[0].thread_id).toBe('thread-456');
    });

    it('should switch threads and load messages', async () => {
      const { messageService } = require('@/services/messageService');
      
      const thread1Messages = [
        { id: 'msg-1', thread_id: 'thread-1', content: 'Thread 1 message', role: 'user' }
      ];
      
      const thread2Messages = [
        { id: 'msg-2', thread_id: 'thread-2', content: 'Thread 2 message', role: 'user' }
      ];
      
      // Mock message loading
      messageService.getMessages
        .mockResolvedValueOnce(thread1Messages)
        .mockResolvedValueOnce(thread2Messages);
      
      // Load thread 1
      const messages1 = await messageService.getMessages('thread-1');
      useChatStore.setState({ messages: messages1, currentThread: 'thread-1' });
      
      expect(useChatStore.getState().messages).toEqual(thread1Messages);
      
      // Switch to thread 2
      const messages2 = await messageService.getMessages('thread-2');
      useChatStore.setState({ messages: messages2, currentThread: 'thread-2' });
      
      expect(useChatStore.getState().messages).toEqual(thread2Messages);
      expect(useChatStore.getState().currentThread).toBe('thread-2');
    });
  });
});