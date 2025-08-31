/**
 * Comprehensive OptimisticMessageManager Pipeline Tests
 * 
 * Tests the complete optimistic update system including:
 * 1. Optimistic message creation and lifecycle
 * 2. Backend reconciliation and matching
 * 3. Failure detection and retry mechanisms
 * 4. State management and cleanup
 * 5. Subscription and notification system
 * 6. Performance and memory management
 */

import { OptimisticMessageManager, optimisticMessageManager } from '@/services/optimistic-updates';
import type { ChatMessage } from '@/types/unified';
import { generateUniqueId } from '@/lib/utils';
import { logger } from '@/lib/logger';

// Mock dependencies
jest.mock('@/lib/utils');
jest.mock('@/lib/logger');

describe('OptimisticMessageManager Pipeline Tests', () => {
      setupAntiHang();
    jest.setTimeout(10000);
  let manager: OptimisticMessageManager;
  
  beforeEach(() => {
    // Create fresh instance for each test to avoid state pollution
    manager = new OptimisticMessageManager();
    
    // Setup mock implementations
    (generateUniqueId as jest.Mock).mockImplementation((prefix) => `${prefix}-${Date.now()}-${Math.random()}`);
    
    // Mock current time for consistent testing
    jest.spyOn(Date, 'now').mockReturnValue(1234567890000);
  });

  afterEach(() => {
    jest.restoreAllMocks();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
      cleanupAntiHang();
  });

  describe('Optimistic Message Creation Pipeline', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should create optimistic user message with correct properties', () => {
      const content = 'Test user message';
      const threadId = 'thread-123';

      const message = manager.addOptimisticUserMessage(content, threadId);

      expect(message).toEqual({
        id: expect.stringMatching(/^msg-/),
        content,
        role: 'user',
        timestamp: 1234567890000,
        isOptimistic: true,
        status: 'pending',
        localId: expect.stringMatching(/^opt-user-/),
        threadId
      });

      const state = manager.getState();
      expect(state.messages.has(message.localId)).toBe(true);
      expect(state.pendingUserMessage?.localId).toBe(message.localId);
    });

    it('should create optimistic AI message with correct properties', () => {
      const threadId = 'thread-456';

      const message = manager.addOptimisticAiMessage(threadId);

      expect(message).toEqual({
        id: expect.stringMatching(/^msg-/),
        content: '',
        role: 'assistant',
        timestamp: 1234567890000,
        isOptimistic: true,
        status: 'processing',
        localId: expect.stringMatching(/^opt-ai-/),
        threadId
      });

      const state = manager.getState();
      expect(state.messages.has(message.localId)).toBe(true);
      expect(state.pendingAiMessage?.localId).toBe(message.localId);
    });

    it('should handle message creation without thread ID', () => {
      const userMessage = manager.addOptimisticUserMessage('Test message');
      const aiMessage = manager.addOptimisticAiMessage();

      expect(userMessage.threadId).toBeUndefined();
      expect(aiMessage.threadId).toBeUndefined();
    });

    it('should assign unique IDs to each message', () => {
      const message1 = manager.addOptimisticUserMessage('Message 1');
      const message2 = manager.addOptimisticUserMessage('Message 2');
      const message3 = manager.addOptimisticAiMessage();

      expect(message1.id).not.toBe(message2.id);
      expect(message1.localId).not.toBe(message2.localId);
      expect(message2.id).not.toBe(message3.id);
      expect(message2.localId).not.toBe(message3.localId);
    });
  });

  describe('Message Update and Lifecycle Pipeline', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should update message properties correctly', () => {
      const message = manager.addOptimisticUserMessage('Original content');
      
      manager.updateOptimisticMessage(message.localId, {
        content: 'Updated content',
        status: 'confirmed'
      });

      const state = manager.getState();
      const updatedMessage = state.messages.get(message.localId);
      
      expect(updatedMessage?.content).toBe('Updated content');
      expect(updatedMessage?.status).toBe('confirmed');
      expect(updatedMessage?.id).toBe(message.id); // Should preserve original properties
    });

    it('should update pending references when message is updated', () => {
      const userMessage = manager.addOptimisticUserMessage('User message');
      const aiMessage = manager.addOptimisticAiMessage();

      manager.updateOptimisticMessage(userMessage.localId, { status: 'confirmed' });
      manager.updateOptimisticMessage(aiMessage.localId, { content: 'AI response' });

      const state = manager.getState();
      expect(state.pendingUserMessage?.status).toBe('confirmed');
      expect(state.pendingAiMessage?.content).toBe('AI response');
    });

    it('should ignore updates for non-existent messages', () => {
      const initialState = manager.getState();
      
      manager.updateOptimisticMessage('non-existent-id', { content: 'New content' });
      
      const finalState = manager.getState();
      expect(finalState).toEqual(initialState);
    });

    it('should handle partial updates correctly', () => {
      const message = manager.addOptimisticUserMessage('Test message');
      
      manager.updateOptimisticMessage(message.localId, { status: 'confirmed' });

      const state = manager.getState();
      const updatedMessage = state.messages.get(message.localId);
      
      // Should preserve all original properties except updated ones
      expect(updatedMessage?.content).toBe('Test message');
      expect(updatedMessage?.role).toBe('user');
      expect(updatedMessage?.status).toBe('confirmed');
    });
  });

  describe('Backend Reconciliation Pipeline', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should reconcile matching messages correctly', () => {
      const optimisticMsg = manager.addOptimisticUserMessage('Test message', 'thread-123');
      
      const backendMessages: ChatMessage[] = [
        {
          id: 'backend-msg-1',
          content: 'Test message',
          role: 'user',
          timestamp: 1234567890000,
          thread_id: 'thread-123'
        }
      ];

      const result = manager.reconcileWithBackend(backendMessages);

      expect(result.confirmed).toHaveLength(1);
      expect(result.confirmed[0].id).toBe('backend-msg-1');
      expect(result.confirmed[0].status).toBe('confirmed');
      expect(result.failed).toHaveLength(0);

      const state = manager.getState();
      expect(state.pendingUserMessage).toBeNull();
    });

    it('should match messages with slight timestamp variations', () => {
      const optimisticMsg = manager.addOptimisticUserMessage('Test message');
      
      const backendMessages: ChatMessage[] = [
        {
          id: 'backend-msg-1',
          content: 'Test message',
          role: 'user',
          timestamp: 1234567892000, // 2 seconds difference
        }
      ];

      const result = manager.reconcileWithBackend(backendMessages);

      expect(result.confirmed).toHaveLength(1);
      expect(result.failed).toHaveLength(0);
    });

    it('should not match messages with large timestamp differences', () => {
      const optimisticMsg = manager.addOptimisticUserMessage('Test message');
      
      const backendMessages: ChatMessage[] = [
        {
          id: 'backend-msg-1',
          content: 'Test message',
          role: 'user',
          timestamp: 1234567890000 + 10000, // 10 seconds difference (too large)
        }
      ];

      const result = manager.reconcileWithBackend(backendMessages);

      expect(result.confirmed).toHaveLength(0);
    });

    it('should match by content and role regardless of other properties', () => {
      const optimisticMsg = manager.addOptimisticUserMessage('Unique test message');
      
      const backendMessages: ChatMessage[] = [
        {
          id: 'different-id',
          content: 'Unique test message',
          role: 'user',
          timestamp: 1234567890000,
          thread_id: 'different-thread'
        }
      ];

      const result = manager.reconcileWithBackend(backendMessages);

      expect(result.confirmed).toHaveLength(1);
      expect(result.confirmed[0].thread_id).toBe('different-thread'); // Should use backend data
    });

    it('should handle multiple message reconciliation', () => {
      const userMsg = manager.addOptimisticUserMessage('User message');
      const aiMsg = manager.addOptimisticAiMessage();
      manager.updateOptimisticMessage(aiMsg.localId, { content: 'AI response' });

      const backendMessages: ChatMessage[] = [
        {
          id: 'backend-user',
          content: 'User message',
          role: 'user',
          timestamp: 1234567890000,
        },
        {
          id: 'backend-ai',
          content: 'AI response',
          role: 'assistant',
          timestamp: 1234567890100,
        }
      ];

      const result = manager.reconcileWithBackend(backendMessages);

      expect(result.confirmed).toHaveLength(2);
      expect(result.failed).toHaveLength(0);

      const state = manager.getState();
      expect(state.pendingUserMessage).toBeNull();
      expect(state.pendingAiMessage).toBeNull();
    });
  });

  describe('Failure Detection and Retry Pipeline', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should mark old pending messages as failed', () => {
      const oldTimestamp = Date.now() - 35000; // 35 seconds ago
      jest.spyOn(Date, 'now').mockReturnValue(oldTimestamp);
      
      const message = manager.addOptimisticUserMessage('Old message');
      
      // Restore current time
      jest.spyOn(Date, 'now').mockReturnValue(oldTimestamp + 35000);

      const result = manager.reconcileWithBackend([]); // No backend messages

      expect(result.failed).toHaveLength(1);
      expect(result.failed[0].status).toBe('failed');
      expect(result.failed[0].localId).toBe(message.localId);

      const state = manager.getState();
      expect(state.retryQueue).toContain(message.localId);
    });

    it('should not mark recent messages as failed', () => {
      const recentTimestamp = Date.now() - 10000; // 10 seconds ago
      jest.spyOn(Date, 'now').mockReturnValue(recentTimestamp);
      
      const message = manager.addOptimisticUserMessage('Recent message');
      
      // Restore current time
      jest.spyOn(Date, 'now').mockReturnValue(recentTimestamp + 10000);

      const result = manager.reconcileWithBackend([]);

      expect(result.failed).toHaveLength(0);
    });

    it('should handle retry logic correctly', async () => {
      const message = manager.addOptimisticUserMessage('Test message');
      manager.updateOptimisticMessage(message.localId, { status: 'failed' });

      await expect(manager.retryMessage(message.localId)).resolves.toBeUndefined();

      const state = manager.getState();
      const retriedMessage = state.messages.get(message.localId);
      expect(retriedMessage?.status).toBe('pending');
    });

    it('should prevent retry of non-failed messages', async () => {
      const message = manager.addOptimisticUserMessage('Test message');
      
      await expect(manager.retryMessage(message.localId)).resolves.toBeUndefined();
      
      // Status should remain unchanged
      const state = manager.getState();
      const sameMessage = state.messages.get(message.localId);
      expect(sameMessage?.status).toBe('pending');
    });

    it('should enforce maximum retry attempts', async () => {
      const message = manager.addOptimisticUserMessage('Test message');
      manager.updateOptimisticMessage(message.localId, { status: 'failed' });

      // Simulate 3 retry attempts (max retries)
      for (let i = 0; i < 3; i++) {
        await manager.retryMessage(message.localId);
        manager.updateOptimisticMessage(message.localId, { status: 'failed' });
      }

      // 4th retry should fail
      await expect(manager.retryMessage(message.localId))
        .rejects.toBe('Max retries exceeded');
    });

    it('should call retry function when provided', async () => {
      const retryFn = jest.fn().mockResolvedValue(undefined);
      const message = manager.addOptimisticUserMessage('Test message');
      
      manager.updateOptimisticMessage(message.localId, { 
        status: 'failed',
        retry: retryFn 
      });

      await manager.retryMessage(message.localId);

      expect(retryFn).toHaveBeenCalled();
    });
  });

  describe('Subscription and Notification Pipeline', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should notify subscribers on state changes', () => {
      const mockCallback = jest.fn();
      const unsubscribe = manager.subscribe(mockCallback);

      manager.addOptimisticUserMessage('Test message');

      expect(mockCallback).toHaveBeenCalledWith(expect.objectContaining({
        messages: expect.any(Map),
        pendingUserMessage: expect.any(Object)
      }));

      unsubscribe();
    });

    it('should handle multiple subscribers', () => {
      const callback1 = jest.fn();
      const callback2 = jest.fn();
      
      const unsub1 = manager.subscribe(callback1);
      const unsub2 = manager.subscribe(callback2);

      manager.addOptimisticUserMessage('Test message');

      expect(callback1).toHaveBeenCalled();
      expect(callback2).toHaveBeenCalled();

      unsub1();
      unsub2();
    });

    it('should remove subscribers correctly', () => {
      const callback = jest.fn();
      const unsubscribe = manager.subscribe(callback);

      unsubscribe();
      manager.addOptimisticUserMessage('Test message');

      expect(callback).not.toHaveBeenCalled();
    });

    it('should handle subscriber callback errors gracefully', () => {
      const errorCallback = jest.fn().mockImplementation(() => {
        throw new Error('Subscriber error');
      });
      const normalCallback = jest.fn();

      manager.subscribe(errorCallback);
      manager.subscribe(normalCallback);

      manager.addOptimisticUserMessage('Test message');

      expect(logger.error).toHaveBeenCalledWith(
        'OptimisticMessageManager callback error:',
        expect.any(Error)
      );
      expect(normalCallback).toHaveBeenCalled(); // Should still call other callbacks
    });
  });

  describe('Utility Methods and Queries', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should return messages in chronological order', () => {
      jest.spyOn(Date, 'now')
        .mockReturnValueOnce(1000)
        .mockReturnValueOnce(2000)
        .mockReturnValueOnce(3000);

      const msg1 = manager.addOptimisticUserMessage('First message');
      const msg2 = manager.addOptimisticUserMessage('Second message');
      const msg3 = manager.addOptimisticAiMessage();

      const messages = manager.getOptimisticMessages();

      expect(messages).toHaveLength(3);
      expect(messages[0].timestamp).toBe(1000);
      expect(messages[1].timestamp).toBe(2000);
      expect(messages[2].timestamp).toBe(3000);
    });

    it('should filter pending messages correctly', () => {
      const userMsg = manager.addOptimisticUserMessage('User message');
      const aiMsg = manager.addOptimisticAiMessage();
      const confirmedMsg = manager.addOptimisticUserMessage('Confirmed message');
      
      manager.updateOptimisticMessage(confirmedMsg.localId, { status: 'confirmed' });

      const pendingMessages = manager.getPendingMessages();

      expect(pendingMessages).toHaveLength(2);
      expect(pendingMessages.some(m => m.localId === userMsg.localId)).toBe(true);
      expect(pendingMessages.some(m => m.localId === aiMsg.localId)).toBe(true);
      expect(pendingMessages.some(m => m.localId === confirmedMsg.localId)).toBe(false);
    });

    it('should filter failed messages correctly', () => {
      const normalMsg = manager.addOptimisticUserMessage('Normal message');
      const failedMsg = manager.addOptimisticUserMessage('Failed message');
      
      manager.updateOptimisticMessage(failedMsg.localId, { status: 'failed' });

      const failedMessages = manager.getFailedMessages();

      expect(failedMessages).toHaveLength(1);
      expect(failedMessages[0].localId).toBe(failedMsg.localId);
    });

    it('should clear all optimistic data correctly', () => {
      manager.addOptimisticUserMessage('User message');
      manager.addOptimisticAiMessage();

      const stateBefore = manager.getState();
      expect(stateBefore.messages.size).toBe(2);
      expect(stateBefore.pendingUserMessage).not.toBeNull();
      expect(stateBefore.pendingAiMessage).not.toBeNull();

      manager.clearAllOptimisticMessages();

      const stateAfter = manager.getState();
      expect(stateAfter.messages.size).toBe(0);
      expect(stateAfter.pendingUserMessage).toBeNull();
      expect(stateAfter.pendingAiMessage).toBeNull();
      expect(stateAfter.retryQueue).toHaveLength(0);
    });
  });

  describe('Performance and Memory Management', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle large numbers of messages efficiently', () => {
      const messageCount = 1000;
      const startTime = performance.now();

      for (let i = 0; i < messageCount; i++) {
        manager.addOptimisticUserMessage(`Message ${i}`);
      }

      const endTime = performance.now();
      expect(endTime - startTime).toBeLessThan(1000); // Should complete within 1 second

      const messages = manager.getOptimisticMessages();
      expect(messages).toHaveLength(messageCount);
    });

    it('should efficiently update multiple messages', () => {
      const messages = [];
      for (let i = 0; i < 100; i++) {
        messages.push(manager.addOptimisticUserMessage(`Message ${i}`));
      }

      const startTime = performance.now();
      
      messages.forEach(msg => {
        manager.updateOptimisticMessage(msg.localId, { status: 'confirmed' });
      });

      const endTime = performance.now();
      expect(endTime - startTime).toBeLessThan(100); // Should be very fast
    });

    it('should handle concurrent reconciliation efficiently', () => {
      // Add many optimistic messages
      for (let i = 0; i < 100; i++) {
        manager.addOptimisticUserMessage(`Message ${i}`);
      }

      // Create backend messages to reconcile against
      const backendMessages: ChatMessage[] = Array.from({ length: 50 }, (_, i) => ({
        id: `backend-${i}`,
        content: `Message ${i}`,
        role: 'user' as const,
        timestamp: Date.now(),
      }));

      const startTime = performance.now();
      const result = manager.reconcileWithBackend(backendMessages);
      const endTime = performance.now();

      expect(endTime - startTime).toBeLessThan(100);
      expect(result.confirmed).toHaveLength(50);
    });
  });

  describe('Singleton Instance Behavior', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should maintain state across imports', () => {
      // Test that the singleton instance behaves consistently
      optimisticMessageManager.addOptimisticUserMessage('Singleton test');
      
      const messages1 = optimisticMessageManager.getOptimisticMessages();
      const messages2 = optimisticMessageManager.getOptimisticMessages();
      
      expect(messages1).toHaveLength(1);
      expect(messages2).toHaveLength(1);
      expect(messages1[0].localId).toBe(messages2[0].localId);
    });

    it('should support independent instances for testing', () => {
      const instance1 = new OptimisticMessageManager();
      const instance2 = new OptimisticMessageManager();

      instance1.addOptimisticUserMessage('Instance 1 message');
      instance2.addOptimisticUserMessage('Instance 2 message');

      expect(instance1.getOptimisticMessages()).toHaveLength(1);
      expect(instance2.getOptimisticMessages()).toHaveLength(1);
      expect(instance1.getOptimisticMessages()[0].content).not.toBe(
        instance2.getOptimisticMessages()[0].content
      );
    });
  });

  describe('Edge Cases and Error Handling', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle reconciliation with empty backend response', () => {
      manager.addOptimisticUserMessage('Test message');
      
      const result = manager.reconcileWithBackend([]);
      
      expect(result.confirmed).toHaveLength(0);
      expect(result.failed).toHaveLength(0); // Should not fail immediately
    });

    it('should handle reconciliation with malformed backend messages', () => {
      manager.addOptimisticUserMessage('Test message');
      
      const malformedMessages = [
        { id: 'bad-1' }, // Missing required fields
        { content: 'No role', role: undefined }, // Invalid data
        null, // Null entry
      ] as any[];

      expect(() => {
        manager.reconcileWithBackend(malformedMessages);
      }).not.toThrow();
    });

    it('should handle rapid state changes without race conditions', async () => {
      const message = manager.addOptimisticUserMessage('Test message');
      
      // Simulate rapid concurrent updates
      const promises = [
        Promise.resolve(manager.updateOptimisticMessage(message.localId, { status: 'confirmed' })),
        Promise.resolve(manager.updateOptimisticMessage(message.localId, { content: 'Updated' })),
        Promise.resolve(manager.updateOptimisticMessage(message.localId, { status: 'failed' })),
      ];

      await Promise.all(promises);

      const state = manager.getState();
      const finalMessage = state.messages.get(message.localId);
      expect(finalMessage).toBeDefined();
      expect(finalMessage?.status).toBe('failed'); // Last update should win
    });
  });
});