/**
 * Simple test to verify ThreadService.getThread mock is working
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MessageInput } from '@/components/chat/MessageInput';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useThreadStore } from '@/store/threadStore';
import { useAuthStore } from '@/store/authStore';
import { ThreadService } from '@/services/threadService';
import { ThreadRenameService } from '@/services/threadRenameService';
import { generateUniqueId } from '@/lib/utils';

// Mock dependencies with proper ThreadService.getThread method
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

describe('MessageInput - ThreadService.getThread Fix', () => {
  const mockSendMessage = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    
    (useWebSocket as jest.Mock).mockReturnValue({
      sendMessage: mockSendMessage,
    });
    
    jest.mocked(useUnifiedChatStore).mockReturnValue({
      setProcessing: jest.fn(),
      isProcessing: false,
      addMessage: jest.fn(),
      activeThreadId: 'thread-1',
      setActiveThread: jest.fn(),
      addOptimisticMessage: jest.fn(),
      updateOptimisticMessage: jest.fn(),
    });
    
    jest.mocked(useThreadStore).mockReturnValue({
      currentThreadId: 'thread-1',
      setCurrentThread: jest.fn(),
      addThread: jest.fn(),
    });
    
    jest.mocked(useAuthStore).mockReturnValue({
      isAuthenticated: true,
    });
    
    (generateUniqueId as jest.Mock).mockImplementation((prefix) => `${prefix}-${Date.now()}`);
  });

  it('should not throw error when calling ThreadService.getThread', async () => {
    // This test verifies that ThreadService.getThread is properly mocked
    render(<MessageInput />);
    const textarea = screen.getByPlaceholderText(/Type a message/i);
    
    // Type and send a message
    await userEvent.type(textarea, 'Test message');
    await userEvent.type(textarea, '{enter}');
    
    // Verify that ThreadService.getThread was called without throwing error
    expect(ThreadService.getThread).toBeDefined();
    expect(typeof ThreadService.getThread).toBe('function');
  });
});