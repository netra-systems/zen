/**
 * Comprehensive useMessageSending Hook Pipeline Tests
 * 
 * Tests the complete message sending pipeline including:
 * 1. Message validation and preprocessing
 * 2. Thread creation and management
 * 3. Optimistic update orchestration
 * 4. WebSocket message dispatch
 * 5. Error handling and retry mechanisms
 * 6. State synchronization across stores
 */

import { renderHook, act } from '@testing-library/react';
import { useMessageSending } from '@/components/chat/hooks/useMessageSending';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useThreadStore } from '@/store/threadStore';
import { ThreadService } from '@/services/threadService';
import { ThreadRenameService } from '@/services/threadRenameService';
import { optimisticMessageManager } from '@/services/optimistic-updates';
import { generateUniqueId } from '@/lib/utils';
import { logger } from '@/lib/logger';

// Mock all dependencies
jest.mock('@/hooks/useWebSocket');
jest.mock('@/store/unified-chat');
jest.mock('@/store/threadStore');
jest.mock('@/services/threadService');
jest.mock('@/services/threadRenameService');
jest.mock('@/services/optimistic-updates');
jest.mock('@/lib/utils');
jest.mock('@/lib/logger');

describe('useMessageSending Pipeline Tests', () => {
  const mockSendMessage = jest.fn();
  const mockAddMessage = jest.fn();
  const mockSetActiveThread = jest.fn();
  const mockSetProcessing = jest.fn();
  const mockAddOptimisticMessage = jest.fn();
  const mockUpdateOptimisticMessage = jest.fn();
  const mockSetCurrentThread = jest.fn();
  const mockAddThread = jest.fn();
  const mockAddOptimisticUserMessage = jest.fn();
  const mockAddOptimisticAiMessage = jest.fn();
  const mockGetFailedMessages = jest.fn();
  const mockRetryMessage = jest.fn();

  const mockThread = {
    id: 'thread-123',
    title: 'Test Thread',
    metadata: { renamed: false, title: 'New Chat' }
  };

  const mockOptimisticUser = {
    id: 'msg-user-123',
    role: 'user',
    content: 'Test message',
    localId: 'opt-user-123',
    isOptimistic: true,
    status: 'pending',
    timestamp: Date.now()
  };

  const mockOptimisticAi = {
    id: 'msg-ai-123',
    role: 'assistant',
    content: '',
    localId: 'opt-ai-123',
    isOptimistic: true,
    status: 'processing',
    timestamp: Date.now()
  };

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Setup default mocks
    (useWebSocket as jest.Mock).mockReturnValue({
      sendMessage: mockSendMessage
    });

    (useUnifiedChatStore as jest.Mock).mockReturnValue({
      addMessage: mockAddMessage,
      setActiveThread: mockSetActiveThread,
      setProcessing: mockSetProcessing,
      addOptimisticMessage: mockAddOptimisticMessage,
      updateOptimisticMessage: mockUpdateOptimisticMessage,
      messages: []
    });

    (useThreadStore as jest.Mock).mockReturnValue({
      setCurrentThread: mockSetCurrentThread,
      addThread: mockAddThread
    });

    (ThreadService.createThread as jest.Mock).mockResolvedValue(mockThread);
    (ThreadService.getThread as jest.Mock).mockResolvedValue(mockThread);
    (ThreadRenameService.autoRenameThread as jest.Mock).mockResolvedValue(undefined);

    (optimisticMessageManager.addOptimisticUserMessage as jest.Mock).mockReturnValue(mockOptimisticUser);
    (optimisticMessageManager.addOptimisticAiMessage as jest.Mock).mockReturnValue(mockOptimisticAi);
    (optimisticMessageManager.getFailedMessages as jest.Mock).mockReturnValue([]);
    (optimisticMessageManager.retryMessage as jest.Mock).mockResolvedValue(undefined);

    (generateUniqueId as jest.Mock).mockImplementation((prefix) => `${prefix}-${Date.now()}`);

    Date.now = jest.fn(() => 1234567890000);
  });

  describe('Message Validation Pipeline', () => {
    it('should validate message requirements correctly', async () => {
      const { result } = renderHook(() => useMessageSending());

      const validParams = {
        message: 'Valid message',
        isAuthenticated: true,
        activeThreadId: 'thread-123',
        currentThreadId: 'thread-123'
      };

      await act(async () => {
        await result.current.handleSend(validParams);
      });

      expect(mockSendMessage).toHaveBeenCalled();
      expect(mockAddOptimisticMessage).toHaveBeenCalledTimes(2); // User + AI
    });

    it('should reject unauthenticated requests', async () => {
      const { result } = renderHook(() => useMessageSending());

      const invalidParams = {
        message: 'Valid message',
        isAuthenticated: false,
        activeThreadId: 'thread-123',
        currentThreadId: 'thread-123'
      };

      await act(async () => {
        await result.current.handleSend(invalidParams);
      });

      expect(mockSendMessage).not.toHaveBeenCalled();
      expect(mockAddOptimisticMessage).not.toHaveBeenCalled();
    });

    it('should reject empty messages', async () => {
      const { result } = renderHook(() => useMessageSending());

      const invalidParams = {
        message: '   ',
        isAuthenticated: true,
        activeThreadId: 'thread-123',
        currentThreadId: 'thread-123'
      };

      await act(async () => {
        await result.current.handleSend(invalidParams);
      });

      expect(mockSendMessage).not.toHaveBeenCalled();
    });

    it('should reject messages over character limit', async () => {
      const { result } = renderHook(() => useMessageSending());

      const invalidParams = {
        message: 'a'.repeat(2001),
        isAuthenticated: true,
        activeThreadId: 'thread-123',
        currentThreadId: 'thread-123'
      };

      await act(async () => {
        await result.current.handleSend(invalidParams);
      });

      expect(mockSendMessage).not.toHaveBeenCalled();
    });

    it('should reject concurrent sends', async () => {
      const { result } = renderHook(() => useMessageSending());

      const validParams = {
        message: 'Valid message',
        isAuthenticated: true,
        activeThreadId: 'thread-123',
        currentThreadId: 'thread-123'
      };

      // Start first send
      act(() => {
        result.current.handleSend(validParams);
      });

      expect(result.current.isSending).toBe(true);

      // Try second send while first is in progress
      await act(async () => {
        await result.current.handleSend(validParams);
      });

      // Should only have sent once
      expect(mockSendMessage).toHaveBeenCalledTimes(1);
    });
  });

  describe('Thread Management Pipeline', () => {
    it('should use existing active thread', async () => {
      const { result } = renderHook(() => useMessageSending());

      const params = {
        message: 'Test message',
        isAuthenticated: true,
        activeThreadId: 'existing-thread',
        currentThreadId: null
      };

      await act(async () => {
        await result.current.handleSend(params);
      });

      expect(ThreadService.createThread).not.toHaveBeenCalled();
      expect(mockSendMessage).toHaveBeenCalledWith({
        type: 'user_message',
        payload: {
          content: 'Test message',
          references: [],
          thread_id: 'existing-thread'
        }
      });
    });

    it('should use existing current thread when no active thread', async () => {
      const { result } = renderHook(() => useMessageSending());

      const params = {
        message: 'Test message',
        isAuthenticated: true,
        activeThreadId: null,
        currentThreadId: 'current-thread'
      };

      await act(async () => {
        await result.current.handleSend(params);
      });

      expect(ThreadService.createThread).not.toHaveBeenCalled();
      expect(mockSendMessage).toHaveBeenCalledWith({
        type: 'user_message',
        payload: {
          content: 'Test message',
          references: [],
          thread_id: 'current-thread'
        }
      });
    });

    it('should create new thread when none exists', async () => {
      const { result } = renderHook(() => useMessageSending());

      const params = {
        message: 'First message in new thread',
        isAuthenticated: true,
        activeThreadId: null,
        currentThreadId: null
      };

      await act(async () => {
        await result.current.handleSend(params);
      });

      expect(ThreadService.createThread).toHaveBeenCalledWith('First message in new thread');
      expect(mockAddThread).toHaveBeenCalledWith(mockThread);
      expect(mockSetCurrentThread).toHaveBeenCalledWith('thread-123');
      expect(mockSetActiveThread).toHaveBeenCalledWith('thread-123');
    });

    it('should truncate long thread titles', async () => {
      const { result } = renderHook(() => useMessageSending());

      const longMessage = 'a'.repeat(100);
      const expectedTitle = 'a'.repeat(50) + '...';

      const params = {
        message: longMessage,
        isAuthenticated: true,
        activeThreadId: null,
        currentThreadId: null
      };

      await act(async () => {
        await result.current.handleSend(params);
      });

      expect(ThreadService.createThread).toHaveBeenCalledWith(expectedTitle);
    });
  });

  describe('WebSocket Message Dispatch Pipeline', () => {
    it('should use start_agent for first message in thread', async () => {
      const { result } = renderHook(() => useMessageSending());

      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...useUnifiedChatStore(),
        messages: [] // No existing messages
      });

      const params = {
        message: 'First message',
        isAuthenticated: true,
        activeThreadId: 'thread-123',
        currentThreadId: 'thread-123'
      };

      await act(async () => {
        await result.current.handleSend(params);
      });

      expect(mockSendMessage).toHaveBeenCalledWith({
        type: 'start_agent',
        payload: {
          user_request: 'First message',
          thread_id: 'thread-123',
          context: {},
          settings: {}
        }
      });
    });

    it('should use user_message for subsequent messages', async () => {
      const { result } = renderHook(() => useMessageSending());

      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...useUnifiedChatStore(),
        messages: [
          { id: 'msg-1', role: 'user', thread_id: 'thread-123', content: 'Previous message' }
        ]
      });

      const params = {
        message: 'Follow up message',
        isAuthenticated: true,
        activeThreadId: 'thread-123',
        currentThreadId: 'thread-123'
      };

      await act(async () => {
        await result.current.handleSend(params);
      });

      expect(mockSendMessage).toHaveBeenCalledWith({
        type: 'user_message',
        payload: {
          content: 'Follow up message',
          references: [],
          thread_id: 'thread-123'
        }
      });
    });

    it('should use start_agent for new thread even with null thread_id', async () => {
      const { result } = renderHook(() => useMessageSending());

      const params = {
        message: 'First message',
        isAuthenticated: true,
        activeThreadId: null,
        currentThreadId: null
      };

      await act(async () => {
        await result.current.handleSend(params);
      });

      expect(mockSendMessage).toHaveBeenCalledWith({
        type: 'start_agent',
        payload: {
          user_request: 'First message',
          thread_id: 'thread-123', // Created thread ID
          context: {},
          settings: {}
        }
      });
    });
  });

  describe('Optimistic Update Pipeline', () => {
    it('should add both user and AI optimistic messages', async () => {
      const { result } = renderHook(() => useMessageSending());

      const params = {
        message: 'Test message',
        isAuthenticated: true,
        activeThreadId: 'thread-123',
        currentThreadId: 'thread-123'
      };

      await act(async () => {
        await result.current.handleSend(params);
      });

      expect(optimisticMessageManager.addOptimisticUserMessage).toHaveBeenCalledWith(
        'Test message',
        'thread-123'
      );
      expect(optimisticMessageManager.addOptimisticAiMessage).toHaveBeenCalledWith('thread-123');
      expect(mockAddOptimisticMessage).toHaveBeenCalledWith(mockOptimisticUser);
      expect(mockAddOptimisticMessage).toHaveBeenCalledWith(mockOptimisticAi);
    });

    it('should handle optimistic message creation failure', async () => {
      const { result } = renderHook(() => useMessageSending());

      (optimisticMessageManager.addOptimisticUserMessage as jest.Mock).mockImplementation(() => {
        throw new Error('Optimistic creation failed');
      });

      const params = {
        message: 'Test message',
        isAuthenticated: true,
        activeThreadId: 'thread-123',
        currentThreadId: 'thread-123'
      };

      await act(async () => {
        await result.current.handleSend(params);
      });

      expect(logger.error).toHaveBeenCalled();
      expect(result.current.isSending).toBe(false);
    });
  });

  describe('Thread Auto-Rename Pipeline', () => {
    it('should auto-rename thread on first message', async () => {
      const { result } = renderHook(() => useMessageSending());

      const params = {
        message: 'First message for renaming',
        isAuthenticated: true,
        activeThreadId: 'thread-123',
        currentThreadId: 'thread-123'
      };

      await act(async () => {
        await result.current.handleSend(params);
      });

      expect(ThreadService.getThread).toHaveBeenCalledWith('thread-123');
      expect(ThreadRenameService.autoRenameThread).toHaveBeenCalledWith(
        'thread-123',
        'First message for renaming'
      );
    });

    it('should not rename already renamed threads', async () => {
      const { result } = renderHook(() => useMessageSending());

      (ThreadService.getThread as jest.Mock).mockResolvedValue({
        ...mockThread,
        metadata: { renamed: true, title: 'Custom Title' }
      });

      const params = {
        message: 'Message in renamed thread',
        isAuthenticated: true,
        activeThreadId: 'thread-123',
        currentThreadId: 'thread-123'
      };

      await act(async () => {
        await result.current.handleSend(params);
      });

      expect(ThreadRenameService.autoRenameThread).not.toHaveBeenCalled();
    });

    it('should handle thread rename failure gracefully', async () => {
      const { result } = renderHook(() => useMessageSending());

      (ThreadRenameService.autoRenameThread as jest.Mock).mockRejectedValue(
        new Error('Rename failed')
      );

      const params = {
        message: 'Test message',
        isAuthenticated: true,
        activeThreadId: 'thread-123',
        currentThreadId: 'thread-123'
      };

      await act(async () => {
        await result.current.handleSend(params);
      });

      // Should still complete successfully
      expect(mockSetProcessing).toHaveBeenCalledWith(true);
      expect(result.current.isSending).toBe(false);
    });
  });

  describe('Error Handling Pipeline', () => {
    it('should handle thread creation failure', async () => {
      const { result } = renderHook(() => useMessageSending());

      (ThreadService.createThread as jest.Mock).mockRejectedValue(
        new Error('Thread creation failed')
      );

      const params = {
        message: 'Test message',
        isAuthenticated: true,
        activeThreadId: null,
        currentThreadId: null
      };

      await act(async () => {
        await result.current.handleSend(params);
      });

      expect(logger.error).toHaveBeenCalledWith('Failed to send message:', expect.any(Error));
      expect(result.current.isSending).toBe(false);
    });

    it('should handle WebSocket send failure', async () => {
      const { result } = renderHook(() => useMessageSending());

      (mockSendMessage as jest.Mock).mockImplementation(() => {
        throw new Error('WebSocket send failed');
      });

      const params = {
        message: 'Test message',
        isAuthenticated: true,
        activeThreadId: 'thread-123',
        currentThreadId: 'thread-123'
      };

      await act(async () => {
        await result.current.handleSend(params);
      });

      expect(logger.error).toHaveBeenCalled();
      expect(result.current.isSending).toBe(false);
    });

    it('should mark failed messages for retry', async () => {
      const { result } = renderHook(() => useMessageSending());

      const failedMessage = {
        localId: 'failed-msg-123',
        content: 'Failed message',
        status: 'failed'
      };

      (optimisticMessageManager.getFailedMessages as jest.Mock).mockReturnValue([failedMessage]);
      (mockSendMessage as jest.Mock).mockImplementation(() => {
        throw new Error('Send failed');
      });

      const params = {
        message: 'Test message',
        isAuthenticated: true,
        activeThreadId: 'thread-123',
        currentThreadId: 'thread-123'
      };

      await act(async () => {
        await result.current.handleSend(params);
      });

      expect(mockUpdateOptimisticMessage).toHaveBeenCalledWith(
        'failed-msg-123',
        expect.objectContaining({
          status: 'failed',
          retry: expect.any(Function)
        })
      );
    });
  });

  describe('Retry Mechanism Pipeline', () => {
    it('should provide retry functionality for failed messages', async () => {
      const { result } = renderHook(() => useMessageSending());

      const failedMessage = {
        localId: 'failed-msg-123',
        content: 'Failed message',
        status: 'failed'
      };

      (optimisticMessageManager.getFailedMessages as jest.Mock).mockReturnValue([failedMessage]);
      (mockSendMessage as jest.Mock).mockImplementationOnce(() => {
        throw new Error('Initial send failed');
      }).mockImplementationOnce(() => {
        // Retry succeeds
      });

      const params = {
        message: 'Test message',
        isAuthenticated: true,
        activeThreadId: 'thread-123',
        currentThreadId: 'thread-123'
      };

      // Initial send fails
      await act(async () => {
        await result.current.handleSend(params);
      });

      // Get the retry function
      const retryCall = (mockUpdateOptimisticMessage as jest.Mock).mock.calls.find(
        call => call[0] === 'failed-msg-123'
      );
      expect(retryCall).toBeTruthy();
      
      const retryFunction = retryCall[1].retry;
      expect(retryFunction).toBeInstanceOf(Function);

      // Execute retry
      await act(async () => {
        await retryFunction();
      });

      expect(optimisticMessageManager.retryMessage).toHaveBeenCalledWith('failed-msg-123');
    });

    it('should handle retry failure', async () => {
      const { result } = renderHook(() => useMessageSending());

      const failedMessage = {
        localId: 'failed-msg-123',
        content: 'Failed message',
        status: 'failed'
      };

      (optimisticMessageManager.getFailedMessages as jest.Mock).mockReturnValue([failedMessage]);
      (optimisticMessageManager.retryMessage as jest.Mock).mockRejectedValue(
        new Error('Retry failed')
      );
      (mockSendMessage as jest.Mock).mockImplementation(() => {
        throw new Error('Send failed');
      });

      const params = {
        message: 'Test message',
        isAuthenticated: true,
        activeThreadId: 'thread-123',
        currentThreadId: 'thread-123'
      };

      await act(async () => {
        await result.current.handleSend(params);
      });

      const retryCall = (mockUpdateOptimisticMessage as jest.Mock).mock.calls.find(
        call => call[0] === 'failed-msg-123'
      );
      const retryFunction = retryCall[1].retry;

      await act(async () => {
        await retryFunction();
      });

      expect(logger.error).toHaveBeenCalledWith('Retry failed:', expect.any(Error));
    });
  });

  describe('State Management Integration', () => {
    it('should properly manage sending state throughout pipeline', async () => {
      const { result } = renderHook(() => useMessageSending());

      const params = {
        message: 'Test message',
        isAuthenticated: true,
        activeThreadId: 'thread-123',
        currentThreadId: 'thread-123'
      };

      expect(result.current.isSending).toBe(false);

      const sendPromise = act(async () => {
        await result.current.handleSend(params);
      });

      // Should be sending during execution
      expect(result.current.isSending).toBe(true);

      await sendPromise;

      // Should not be sending after completion
      expect(result.current.isSending).toBe(false);
    });

    it('should set processing state after successful send', async () => {
      const { result } = renderHook(() => useMessageSending());

      const params = {
        message: 'Test message',
        isAuthenticated: true,
        activeThreadId: 'thread-123',
        currentThreadId: 'thread-123'
      };

      await act(async () => {
        await result.current.handleSend(params);
      });

      expect(mockSetProcessing).toHaveBeenCalledWith(true);
    });

    it('should provide reset functionality', () => {
      const { result } = renderHook(() => useMessageSending());

      act(() => {
        result.current.reset();
      });

      expect(result.current.isSending).toBe(false);
    });
  });

  describe('Edge Cases', () => {
    it('should handle rapid consecutive send attempts', async () => {
      const { result } = renderHook(() => useMessageSending());

      const params = {
        message: 'Test message',
        isAuthenticated: true,
        activeThreadId: 'thread-123',
        currentThreadId: 'thread-123'
      };

      // Start multiple sends rapidly
      const promises = [
        result.current.handleSend(params),
        result.current.handleSend(params),
        result.current.handleSend(params)
      ];

      await act(async () => {
        await Promise.all(promises);
      });

      // Should only send once due to isSending guard
      expect(mockSendMessage).toHaveBeenCalledTimes(1);
    });

    it('should handle missing thread service', async () => {
      const { result } = renderHook(() => useMessageSending());

      (ThreadService.createThread as jest.Mock).mockImplementation(() => {
        throw new Error('ThreadService unavailable');
      });

      const params = {
        message: 'Test message',
        isAuthenticated: true,
        activeThreadId: null,
        currentThreadId: null
      };

      await act(async () => {
        await result.current.handleSend(params);
      });

      expect(logger.error).toHaveBeenCalled();
      expect(result.current.isSending).toBe(false);
    });
  });
});