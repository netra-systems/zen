import { act, renderHook } from '@testing-library/react';
import { useChatStore } from '../../store/chat';
import { Message, SubAgentStatus } from '../../types/chat';

describe('Chat Store', () => {
  beforeEach(() => {
    // Reset store to initial state before each test
    useChatStore.getState().reset();
  });

  describe('Initial State', () => {
    it('should have correct initial state', () => {
      const { result } = renderHook(() => useChatStore());
      
      expect(result.current.messages).toEqual([]);
      expect(result.current.subAgentName).toBe('Netra Agent');
      expect(result.current.subAgentStatus).toBeNull();
      expect(result.current.isProcessing).toBe(false);
    });

    it('should provide all required methods', () => {
      const { result } = renderHook(() => useChatStore());
      
      expect(typeof result.current.addMessage).toBe('function');
      expect(typeof result.current.setSubAgentName).toBe('function');
      expect(typeof result.current.setSubAgentStatus).toBe('function');
      expect(typeof result.current.setProcessing).toBe('function');
      expect(typeof result.current.reset).toBe('function');
    });
  });

  describe('Message Management', () => {
    it('should add messages correctly', () => {
      const { result } = renderHook(() => useChatStore());
      
      const message: Message = {
        id: 'msg_1',
        role: 'user',
        content: 'Hello World',
        timestamp: '2023-10-01T12:00:00Z',
        displayed_to_user: true
      };

      act(() => {
        result.current.addMessage(message);
      });

      expect(result.current.messages).toHaveLength(1);
      expect(result.current.messages[0]).toEqual(message);
    });

    it('should add multiple messages in order', () => {
      const { result } = renderHook(() => useChatStore());
      
      const messages: Message[] = [
        {
          id: 'msg_1',
          role: 'user',
          content: 'First message',
          timestamp: '2023-10-01T12:00:00Z',
          displayed_to_user: true
        },
        {
          id: 'msg_2',
          role: 'assistant',
          content: 'Second message',
          timestamp: '2023-10-01T12:01:00Z',
          displayed_to_user: true
        },
        {
          id: 'msg_3',
          role: 'user',
          content: 'Third message',
          timestamp: '2023-10-01T12:02:00Z',
          displayed_to_user: true
        }
      ];

      act(() => {
        messages.forEach(msg => result.current.addMessage(msg));
      });

      expect(result.current.messages).toHaveLength(3);
      expect(result.current.messages).toEqual(messages);
    });

    it('should handle messages with different properties', () => {
      const { result } = renderHook(() => useChatStore());
      
      const messageWithError: Message = {
        id: 'msg_error',
        role: 'assistant',
        content: 'Error message',
        timestamp: '2023-10-01T12:00:00Z',
        displayed_to_user: true,
        error: true
      };

      const messageWithSubAgent: Message = {
        id: 'msg_sub',
        role: 'assistant',
        content: 'SubAgent message',
        timestamp: '2023-10-01T12:01:00Z',
        displayed_to_user: true,
        subAgentName: 'DataAgent'
      };

      const messageWithMetadata: Message = {
        id: 'msg_meta',
        role: 'assistant',
        content: 'Message with metadata',
        timestamp: '2023-10-01T12:02:00Z',
        displayed_to_user: true,
        metadata: { tool: 'analyzer', status: 'complete' }
      };

      act(() => {
        result.current.addMessage(messageWithError);
        result.current.addMessage(messageWithSubAgent);
        result.current.addMessage(messageWithMetadata);
      });

      expect(result.current.messages).toHaveLength(3);
      expect(result.current.messages[0].error).toBe(true);
      expect(result.current.messages[1].subAgentName).toBe('DataAgent');
      expect(result.current.messages[2].metadata).toEqual({ tool: 'analyzer', status: 'complete' });
    });

    it('should maintain message immutability', () => {
      const { result } = renderHook(() => useChatStore());
      
      const originalMessage: Message = {
        id: 'msg_1',
        role: 'user',
        content: 'Original content',
        timestamp: '2023-10-01T12:00:00Z',
        displayed_to_user: true
      };

      act(() => {
        result.current.addMessage(originalMessage);
      });

      const storedMessage = result.current.messages[0];
      expect(storedMessage).not.toBe(originalMessage);
      expect(storedMessage).toEqual(originalMessage);
    });

    it('should handle rapid message additions', () => {
      const { result } = renderHook(() => useChatStore());
      
      const messages = Array.from({ length: 100 }, (_, i) => ({
        id: `msg_${i}`,
        role: i % 2 === 0 ? 'user' : 'assistant',
        content: `Message ${i}`,
        timestamp: new Date(Date.now() + i * 1000).toISOString(),
        displayed_to_user: true
      } as Message));

      act(() => {
        messages.forEach(msg => result.current.addMessage(msg));
      });

      expect(result.current.messages).toHaveLength(100);
      expect(result.current.messages[0].content).toBe('Message 0');
      expect(result.current.messages[99].content).toBe('Message 99');
    });
  });

  describe('SubAgent Management', () => {
    it('should set subAgent name correctly', () => {
      const { result } = renderHook(() => useChatStore());
      
      act(() => {
        result.current.setSubAgentName('DataAnalyzer');
      });

      expect(result.current.subAgentName).toBe('DataAnalyzer');
    });

    it('should handle empty and special subAgent names', () => {
      const { result } = renderHook(() => useChatStore());
      
      const testNames = ['', 'Agent-123', 'Agent_With_Underscore', 'Agent@Special', 'VeryLongAgentNameWithManyCharacters'];

      testNames.forEach(name => {
        act(() => {
          result.current.setSubAgentName(name);
        });
        
        expect(result.current.subAgentName).toBe(name);
      });
    });

    it('should set subAgent status correctly', () => {
      const { result } = renderHook(() => useChatStore());
      
      const status: SubAgentStatus = {
        status: 'running',
        tools: ['analyzer', 'processor']
      };

      act(() => {
        result.current.setSubAgentStatus(status);
      });

      expect(result.current.subAgentStatus).toEqual(status);
    });

    it('should handle different status types', () => {
      const { result } = renderHook(() => useChatStore());
      
      const statuses: SubAgentStatus[] = [
        { status: 'idle', tools: [] },
        { status: 'running', tools: ['tool1', 'tool2'] },
        { status: 'completed', tools: ['finalizer'] },
        { status: 'error', tools: [] },
        { status: 'pending', tools: ['initializer'] }
      ];

      statuses.forEach(status => {
        act(() => {
          result.current.setSubAgentStatus(status);
        });
        
        expect(result.current.subAgentStatus).toEqual(status);
      });
    });

    it('should handle status with empty tools array', () => {
      const { result } = renderHook(() => useChatStore());
      
      const status: SubAgentStatus = {
        status: 'running',
        tools: []
      };

      act(() => {
        result.current.setSubAgentStatus(status);
      });

      expect(result.current.subAgentStatus?.tools).toEqual([]);
    });

    it('should handle status with many tools', () => {
      const { result } = renderHook(() => useChatStore());
      
      const manyTools = Array.from({ length: 50 }, (_, i) => `tool_${i}`);
      const status: SubAgentStatus = {
        status: 'running',
        tools: manyTools
      };

      act(() => {
        result.current.setSubAgentStatus(status);
      });

      expect(result.current.subAgentStatus?.tools).toHaveLength(50);
      expect(result.current.subAgentStatus?.tools).toEqual(manyTools);
    });
  });

  describe('Processing State Management', () => {
    it('should set processing state correctly', () => {
      const { result } = renderHook(() => useChatStore());
      
      act(() => {
        result.current.setProcessing(true);
      });

      expect(result.current.isProcessing).toBe(true);

      act(() => {
        result.current.setProcessing(false);
      });

      expect(result.current.isProcessing).toBe(false);
    });

    it('should handle rapid processing state changes', () => {
      const { result } = renderHook(() => useChatStore());
      
      const changes = [true, false, true, false, true, false, true, false];

      changes.forEach(processing => {
        act(() => {
          result.current.setProcessing(processing);
        });
        
        expect(result.current.isProcessing).toBe(processing);
      });
    });
  });

  describe('Store Reset Functionality', () => {
    it('should reset all state to initial values', () => {
      const { result } = renderHook(() => useChatStore());
      
      // Modify all state values
      act(() => {
        result.current.addMessage({
          id: 'msg_1',
          role: 'user',
          content: 'Test message',
          timestamp: '2023-10-01T12:00:00Z',
          displayed_to_user: true
        });
        result.current.setSubAgentName('TestAgent');
        result.current.setSubAgentStatus({ status: 'running', tools: ['test'] });
        result.current.setProcessing(true);
      });

      // Verify state was modified
      expect(result.current.messages).toHaveLength(1);
      expect(result.current.subAgentName).toBe('TestAgent');
      expect(result.current.subAgentStatus).toEqual({ status: 'running', tools: ['test'] });
      expect(result.current.isProcessing).toBe(true);

      // Reset state
      act(() => {
        result.current.reset();
      });

      // Verify reset
      expect(result.current.messages).toEqual([]);
      expect(result.current.subAgentName).toBe('Netra Agent');
      expect(result.current.subAgentStatus).toBeNull();
      expect(result.current.isProcessing).toBe(false);
    });

    it('should handle multiple resets', () => {
      const { result } = renderHook(() => useChatStore());
      
      for (let i = 0; i < 5; i++) {
        act(() => {
          result.current.addMessage({
            id: `msg_${i}`,
            role: 'user',
            content: `Message ${i}`,
            timestamp: '2023-10-01T12:00:00Z',
            displayed_to_user: true
          });
        });

        act(() => {
          result.current.reset();
        });

        expect(result.current.messages).toEqual([]);
      }
    });
  });

  describe('Store Subscription and Updates', () => {
    it('should notify subscribers of state changes', () => {
      const subscriber = jest.fn();
      const { result } = renderHook(() => useChatStore());
      
      const unsubscribe = useChatStore.subscribe(subscriber);

      act(() => {
        result.current.addMessage({
          id: 'msg_1',
          role: 'user',
          content: 'Test',
          timestamp: '2023-10-01T12:00:00Z',
          displayed_to_user: true
        });
      });

      expect(subscriber).toHaveBeenCalled();
      unsubscribe();
    });

    it('should handle concurrent store updates', () => {
      const { result } = renderHook(() => useChatStore());
      
      act(() => {
        // Simulate concurrent updates
        result.current.addMessage({
          id: 'msg_1',
          role: 'user',
          content: 'Message 1',
          timestamp: '2023-10-01T12:00:00Z',
          displayed_to_user: true
        });
        result.current.setProcessing(true);
        result.current.setSubAgentName('ConcurrentAgent');
        result.current.setSubAgentStatus({ status: 'running', tools: ['concurrent'] });
      });

      expect(result.current.messages).toHaveLength(1);
      expect(result.current.isProcessing).toBe(true);
      expect(result.current.subAgentName).toBe('ConcurrentAgent');
      expect(result.current.subAgentStatus?.status).toBe('running');
    });
  });

  describe('Performance and Memory', () => {
    it('should handle large message arrays efficiently', () => {
      const { result } = renderHook(() => useChatStore());
      
      const startTime = performance.now();
      
      act(() => {
        for (let i = 0; i < 1000; i++) {
          result.current.addMessage({
            id: `msg_${i}`,
            role: i % 2 === 0 ? 'user' : 'assistant',
            content: `Performance test message ${i}`,
            timestamp: new Date(Date.now() + i).toISOString(),
            displayed_to_user: true
          });
        }
      });

      const endTime = performance.now();
      const executionTime = endTime - startTime;
      
      expect(result.current.messages).toHaveLength(1000);
      expect(executionTime).toBeLessThan(1000); // Should complete within 1 second
    });

    it('should not cause memory leaks with frequent updates', () => {
      const { result } = renderHook(() => useChatStore());
      
      // Simulate frequent updates that might cause memory leaks
      for (let cycle = 0; cycle < 10; cycle++) {
        act(() => {
          // Add messages
          for (let i = 0; i < 100; i++) {
            result.current.addMessage({
              id: `cycle_${cycle}_msg_${i}`,
              role: 'user',
              content: `Cycle ${cycle} Message ${i}`,
              timestamp: new Date().toISOString(),
              displayed_to_user: true
            });
          }
        });

        act(() => {
          // Reset
          result.current.reset();
        });
      }

      // Final state should be clean
      expect(result.current.messages).toEqual([]);
      expect(result.current.subAgentName).toBe('Netra Agent');
      expect(result.current.subAgentStatus).toBeNull();
      expect(result.current.isProcessing).toBe(false);
    });
  });

  describe('Type Safety and Edge Cases', () => {
    it('should handle undefined and null values gracefully', () => {
      const { result } = renderHook(() => useChatStore());
      
      act(() => {
        result.current.setSubAgentName('');
        result.current.setSubAgentStatus({ status: 'idle', tools: [] });
      });

      expect(result.current.subAgentName).toBe('');
      expect(result.current.subAgentStatus).toEqual({ status: 'idle', tools: [] });
    });

    it('should maintain state consistency across operations', () => {
      const { result } = renderHook(() => useChatStore());
      
      const operations = [
        () => result.current.setProcessing(true),
        () => result.current.setSubAgentName('ConsistencyTest'),
        () => result.current.addMessage({
          id: 'consistency_msg',
          role: 'user',
          content: 'Consistency test',
          timestamp: '2023-10-01T12:00:00Z',
          displayed_to_user: true
        }),
        () => result.current.setSubAgentStatus({ status: 'running', tools: ['consistency'] }),
        () => result.current.setProcessing(false)
      ];

      act(() => {
        operations.forEach(op => op());
      });

      // Verify final consistent state
      expect(result.current.isProcessing).toBe(false);
      expect(result.current.subAgentName).toBe('ConsistencyTest');
      expect(result.current.messages).toHaveLength(1);
      expect(result.current.subAgentStatus?.status).toBe('running');
    });
  });
});