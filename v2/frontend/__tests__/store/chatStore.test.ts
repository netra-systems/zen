import { act, renderHook } from '@testing-library/react';
import { useChatStore } from '@/store/chat';
import { Message } from '@/types/chat';

describe('useChatStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    const { result } = renderHook(() => useChatStore());
    act(() => {
      result.current.clearMessages();
      result.current.setProcessing(false);
    });
  });

  describe('Message Management', () => {
    it('should add a message to the store', () => {
      const { result } = renderHook(() => useChatStore());
      
      const newMessage: Message = {
        id: 'msg-1',
        role: 'user',
        content: 'Hello, world!',
        timestamp: new Date().toISOString(),
        displayed_to_user: true,
      };

      act(() => {
        result.current.addMessage(newMessage);
      });

      expect(result.current.messages).toHaveLength(1);
      expect(result.current.messages[0]).toEqual(newMessage);
    });

    it('should add multiple messages in correct order', () => {
      const { result } = renderHook(() => useChatStore());
      
      const messages: Message[] = [
        {
          id: 'msg-1',
          role: 'user',
          content: 'First message',
          timestamp: new Date().toISOString(),
          displayed_to_user: true,
        },
        {
          id: 'msg-2',
          role: 'assistant',
          content: 'Second message',
          timestamp: new Date().toISOString(),
          displayed_to_user: true,
        },
      ];

      act(() => {
        messages.forEach(msg => result.current.addMessage(msg));
      });

      expect(result.current.messages).toHaveLength(2);
      expect(result.current.messages[0].id).toBe('msg-1');
      expect(result.current.messages[1].id).toBe('msg-2');
    });

    it('should update an existing message', () => {
      const { result } = renderHook(() => useChatStore());
      
      const originalMessage: Message = {
        id: 'msg-1',
        role: 'assistant',
        content: 'Processing...',
        timestamp: new Date().toISOString(),
        displayed_to_user: true,
      };

      act(() => {
        result.current.addMessage(originalMessage);
      });

      const updatedContent = 'Here is the result!';
      
      act(() => {
        result.current.updateMessage('msg-1', { content: updatedContent });
      });

      expect(result.current.messages[0].content).toBe(updatedContent);
      expect(result.current.messages[0].id).toBe('msg-1'); // ID should remain the same
    });

    it('should clear all messages', () => {
      const { result } = renderHook(() => useChatStore());
      
      act(() => {
        result.current.addMessage({
          id: 'msg-1',
          role: 'user',
          content: 'Test',
          timestamp: new Date().toISOString(),
          displayed_to_user: true,
        });
        result.current.addMessage({
          id: 'msg-2',
          role: 'assistant',
          content: 'Response',
          timestamp: new Date().toISOString(),
          displayed_to_user: true,
        });
      });

      expect(result.current.messages).toHaveLength(2);

      act(() => {
        result.current.clearMessages();
      });

      expect(result.current.messages).toHaveLength(0);
    });
  });

  describe('Processing State', () => {
    it('should update processing state', () => {
      const { result } = renderHook(() => useChatStore());
      
      expect(result.current.isProcessing).toBe(false);

      act(() => {
        result.current.setProcessing(true);
      });

      expect(result.current.isProcessing).toBe(true);

      act(() => {
        result.current.setProcessing(false);
      });

      expect(result.current.isProcessing).toBe(false);
    });
  });

  describe('Sub-Agent State', () => {
    it('should update sub-agent information', () => {
      const { result } = renderHook(() => useChatStore());
      
      const subAgentName = 'DataSubAgent';
      const subAgentStatus = 'Analyzing data...';

      act(() => {
        result.current.setSubAgent(subAgentName, subAgentStatus);
      });

      expect(result.current.currentSubAgent).toBe(subAgentName);
      expect(result.current.subAgentStatus).toBe(subAgentStatus);
    });

    it('should clear sub-agent information', () => {
      const { result } = renderHook(() => useChatStore());
      
      act(() => {
        result.current.setSubAgent('TestAgent', 'Working...');
      });

      expect(result.current.currentSubAgent).toBe('TestAgent');

      act(() => {
        result.current.clearSubAgent();
      });

      expect(result.current.currentSubAgent).toBe(null);
      expect(result.current.subAgentStatus).toBe(null);
    });
  });

  describe('Thread Management', () => {
    it('should set active thread', () => {
      const { result } = renderHook(() => useChatStore());
      
      const threadId = 'thread-123';

      act(() => {
        result.current.setActiveThread(threadId);
      });

      expect(result.current.activeThreadId).toBe(threadId);
    });

    it('should load messages for a thread', () => {
      const { result } = renderHook(() => useChatStore());
      
      const threadMessages: Message[] = [
        {
          id: 'msg-1',
          role: 'user',
          content: 'Thread message 1',
          timestamp: new Date().toISOString(),
          displayed_to_user: true,
        },
        {
          id: 'msg-2',
          role: 'assistant',
          content: 'Thread message 2',
          timestamp: new Date().toISOString(),
          displayed_to_user: true,
        },
      ];

      act(() => {
        result.current.loadThreadMessages(threadMessages);
      });

      expect(result.current.messages).toEqual(threadMessages);
    });
  });

  describe('Error Handling', () => {
    it('should add error message', () => {
      const { result } = renderHook(() => useChatStore());
      
      const errorMessage = 'Something went wrong!';

      act(() => {
        result.current.addErrorMessage(errorMessage);
      });

      expect(result.current.messages).toHaveLength(1);
      expect(result.current.messages[0].role).toBe('system');
      expect(result.current.messages[0].content).toContain(errorMessage);
      expect(result.current.messages[0].error).toBe(true);
    });
  });
});