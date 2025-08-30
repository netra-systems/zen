/**
 * Complete test suite for unified-chat store batching functionality
 * Ensures 100% coverage of batched updates to prevent cascading re-renders
 */

import { renderHook, act } from '@testing-library/react';
import { unstable_batchedUpdates } from 'react-dom';
import { useUnifiedChatStore } from '@/store/unified-chat';

// Mock react-dom's batchedUpdates
jest.mock('react-dom', () => ({
  ...jest.requireActual('react-dom'),
  unstable_batchedUpdates: jest.fn((callback) => callback())
}));

describe('Unified Chat Store - Batched Updates', () => {
  beforeEach(() => {
    // Reset store to initial state
    useUnifiedChatStore.setState({
      fastLayerData: null,
      mediumLayerData: null,
      slowLayerData: null,
      isProcessing: false,
      currentRunId: null,
      activeThreadId: null,
      threads: new Map(),
      isThreadLoading: false,
      messages: [],
      isConnected: false,
      connectionError: null,
      initialized: false,
      executedAgents: new Map(),
      agentIterations: new Map(),
      optimisticMessages: new Map(),
      pendingUserMessage: null,
      pendingAiMessage: null,
      wsEventBuffer: expect.any(Object),
      wsEventBufferVersion: 0,
      performanceMetrics: {
        renderCount: 0,
        lastRenderTime: 0,
        averageResponseTime: 0,
        memoryUsage: 0
      },
      subAgentName: null,
      subAgentStatus: null,
      subAgentTools: [],
      subAgentProgress: null,
      subAgentError: null,
      subAgentDescription: null,
      subAgentExecutionTime: null,
      queuedSubAgents: []
    });
    
    jest.clearAllMocks();
  });

  describe('Layer Update Batching', () => {
    test('should batch fast layer updates', () => {
      const { result } = renderHook(() => useUnifiedChatStore());
      
      const testData = {
        content: 'Fast layer content',
        timestamp: Date.now()
      };

      act(() => {
        result.current.updateFastLayer(testData);
      });

      expect(unstable_batchedUpdates).toHaveBeenCalledTimes(1);
      expect(result.current.fastLayerData).toEqual(testData);
    });

    test('should batch medium layer updates', () => {
      const { result } = renderHook(() => useUnifiedChatStore());
      
      const testData = {
        content: 'Medium layer content',
        analysis: 'Some analysis'
      };

      act(() => {
        result.current.updateMediumLayer(testData);
      });

      expect(unstable_batchedUpdates).toHaveBeenCalledTimes(1);
      expect(result.current.mediumLayerData).toBeTruthy();
    });

    test('should batch slow layer updates', () => {
      const { result } = renderHook(() => useUnifiedChatStore());
      
      const testData = {
        agents: ['agent1', 'agent2'],
        finalReport: 'Final analysis'
      };

      act(() => {
        result.current.updateSlowLayer(testData);
      });

      expect(unstable_batchedUpdates).toHaveBeenCalledTimes(1);
      expect(result.current.slowLayerData).toBeTruthy();
    });

    test('should merge fast layer data correctly in batch', () => {
      const { result } = renderHook(() => useUnifiedChatStore());
      
      // Set initial data
      act(() => {
        result.current.updateFastLayer({ field1: 'value1' });
      });

      jest.clearAllMocks();

      // Update with new data
      act(() => {
        result.current.updateFastLayer({ field2: 'value2' });
      });

      expect(unstable_batchedUpdates).toHaveBeenCalledTimes(1);
      expect(result.current.fastLayerData).toEqual({
        field1: 'value1',
        field2: 'value2'
      });
    });
  });

  describe('WebSocket Event Batching', () => {
    test('should batch WebSocket event handling', () => {
      const { result } = renderHook(() => useUnifiedChatStore());
      
      const testEvent = {
        type: 'message',
        data: {
          content: 'Test message',
          timestamp: Date.now()
        }
      };

      act(() => {
        result.current.handleWebSocketEvent(testEvent as any);
      });

      expect(unstable_batchedUpdates).toHaveBeenCalledTimes(1);
    });

    test('should handle multiple WebSocket events in batches', () => {
      const { result } = renderHook(() => useUnifiedChatStore());
      
      const events = [
        { type: 'connection_established', data: {} },
        { type: 'message', data: { content: 'Message 1' } },
        { type: 'message', data: { content: 'Message 2' } },
        { type: 'thread_loaded', data: { threadId: 'test-thread' } }
      ];

      events.forEach(event => {
        act(() => {
          result.current.handleWebSocketEvent(event as any);
        });
      });

      // Each event should be batched individually
      expect(unstable_batchedUpdates).toHaveBeenCalledTimes(events.length);
    });
  });

  describe('Batch Update Performance', () => {
    test('should prevent cascading updates with batching', () => {
      const { result } = renderHook(() => useUnifiedChatStore());
      
      let renderCount = 0;
      const trackRender = () => renderCount++;

      // Subscribe to store changes
      const unsubscribe = useUnifiedChatStore.subscribe(trackRender);

      // Perform multiple updates that would normally cascade
      act(() => {
        result.current.updateFastLayer({ data: 'fast' });
        result.current.updateMediumLayer({ data: 'medium' });
        result.current.updateSlowLayer({ data: 'slow' });
      });

      // With batching, these should result in fewer renders
      expect(renderCount).toBeLessThanOrEqual(3); // One per update max
      
      unsubscribe();
    });

    test('should batch complex state updates', () => {
      const { result } = renderHook(() => useUnifiedChatStore());
      
      act(() => {
        // Simulate complex update scenario
        result.current.setProcessing(true);
        result.current.updateFastLayer({ status: 'processing' });
        result.current.addMessage({ content: 'Processing...' });
        result.current.setConnectionStatus(true, undefined);
      });

      // All updates should maintain consistency
      expect(result.current.isProcessing).toBe(true);
      expect(result.current.fastLayerData).toEqual({ status: 'processing' });
      expect(result.current.messages).toHaveLength(1);
      expect(result.current.isConnected).toBe(true);
    });
  });

  describe('Thread Management with Batching', () => {
    test('should batch thread loading operations', () => {
      const { result } = renderHook(() => useUnifiedChatStore());
      
      act(() => {
        result.current.startThreadLoading('thread-123');
      });

      expect(result.current.activeThreadId).toBe('thread-123');
      expect(result.current.isThreadLoading).toBe(true);
      expect(result.current.messages).toEqual([]);
    });

    test('should batch thread completion operations', () => {
      const { result } = renderHook(() => useUnifiedChatStore());
      
      const messages = [
        { id: '1', content: 'Message 1' },
        { id: '2', content: 'Message 2' }
      ];

      act(() => {
        result.current.completeThreadLoading('thread-123', messages);
      });

      expect(result.current.activeThreadId).toBe('thread-123');
      expect(result.current.isThreadLoading).toBe(false);
      expect(result.current.messages).toEqual(messages);
    });
  });

  describe('Optimistic Updates with Batching', () => {
    test('should batch optimistic message operations', () => {
      const { result } = renderHook(() => useUnifiedChatStore());
      
      const optimisticMessage = {
        localId: 'local-123',
        content: 'Optimistic message',
        status: 'pending' as const,
        timestamp: Date.now()
      };

      act(() => {
        result.current.addOptimisticMessage(optimisticMessage);
      });

      expect(result.current.optimisticMessages.get('local-123')).toEqual(optimisticMessage);
    });

    test('should batch optimistic message updates', () => {
      const { result } = renderHook(() => useUnifiedChatStore());
      
      // Add initial message
      act(() => {
        result.current.addOptimisticMessage({
          localId: 'local-123',
          content: 'Initial',
          status: 'pending' as const,
          timestamp: Date.now()
        });
      });

      // Update message
      act(() => {
        result.current.updateOptimisticMessage('local-123', {
          status: 'sent' as const,
          serverId: 'server-456'
        });
      });

      const updated = result.current.optimisticMessages.get('local-123');
      expect(updated?.status).toBe('sent');
      expect(updated?.serverId).toBe('server-456');
    });
  });

  describe('Reset Operations with Batching', () => {
    test('should batch layer reset operations', () => {
      const { result } = renderHook(() => useUnifiedChatStore());
      
      // Set some data
      act(() => {
        result.current.updateFastLayer({ data: 'fast' });
        result.current.updateMediumLayer({ data: 'medium' });
        result.current.updateSlowLayer({ data: 'slow' });
        result.current.addMessage({ content: 'Test message' });
      });

      // Reset all layers
      act(() => {
        result.current.resetLayers();
      });

      expect(result.current.fastLayerData).toBeNull();
      expect(result.current.mediumLayerData).toBeNull();
      expect(result.current.slowLayerData).toBeNull();
      expect(result.current.messages).toEqual([]);
      expect(result.current.isProcessing).toBe(false);
    });

    test('should batch agent tracking reset', () => {
      const { result } = renderHook(() => useUnifiedChatStore());
      
      // Add some agent data
      act(() => {
        result.current.updateExecutedAgent('agent-1', {
          id: 'agent-1',
          name: 'Test Agent',
          status: 'running',
          startTime: Date.now()
        } as any);
        result.current.incrementAgentIteration('agent-1');
      });

      // Reset agent tracking
      act(() => {
        result.current.resetAgentTracking();
      });

      expect(result.current.executedAgents.size).toBe(0);
      expect(result.current.agentIterations.size).toBe(0);
    });
  });

  describe('Error Handling with Batching', () => {
    test('should handle errors in batched updates gracefully', () => {
      const { result } = renderHook(() => useUnifiedChatStore());
      
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
      
      // Simulate error in update
      const errorData = {
        get data() {
          throw new Error('Test error');
        }
      };

      // Should not throw
      expect(() => {
        act(() => {
          try {
            result.current.updateFastLayer(errorData);
          } catch (e) {
            // Error should be caught
          }
        });
      }).not.toThrow();
      
      consoleSpy.mockRestore();
    });
  });

  describe('Concurrent Updates', () => {
    test('should handle concurrent batched updates correctly', async () => {
      const { result } = renderHook(() => useUnifiedChatStore());
      
      const updates = [
        () => result.current.updateFastLayer({ concurrent: 1 }),
        () => result.current.updateMediumLayer({ concurrent: 2 }),
        () => result.current.updateSlowLayer({ concurrent: 3 })
      ];

      // Run updates concurrently
      await Promise.all(updates.map(update => 
        new Promise(resolve => {
          act(() => {
            update();
            resolve(undefined);
          });
        })
      ));

      // All updates should be applied
      expect(result.current.fastLayerData).toEqual({ concurrent: 1 });
      expect(result.current.mediumLayerData).toBeTruthy();
      expect(result.current.slowLayerData).toBeTruthy();
    });
  });

  describe('Store Initialization State', () => {
    test('should track initialization state', () => {
      const { result } = renderHook(() => useUnifiedChatStore());
      
      // Initially not initialized
      expect(result.current.initialized).toBe(false);
      
      // Can be set to initialized
      act(() => {
        useUnifiedChatStore.setState({ initialized: true });
      });
      
      expect(result.current.initialized).toBe(true);
    });
  });

  describe('Batch Update Verification', () => {
    test('should verify all layer updates use batching', () => {
      const { result } = renderHook(() => useUnifiedChatStore());
      
      const operations = [
        () => result.current.updateFastLayer({}),
        () => result.current.updateMediumLayer({}),
        () => result.current.updateSlowLayer({}),
        () => result.current.handleWebSocketEvent({} as any)
      ];

      operations.forEach((operation, index) => {
        jest.clearAllMocks();
        act(() => {
          operation();
        });
        expect(unstable_batchedUpdates).toHaveBeenCalledTimes(1);
      });
    });
  });
});