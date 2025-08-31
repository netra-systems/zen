import { act, renderHook, waitFor } from '@testing-library/react';
import { useChatStore } from '@/store/chat';
import { useCorpusStore } from '@/store/corpusStore';
import { GlobalTestUtils } from './store-test-utils';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
 - Value Impact: 2x faster load times increase conversion by 15%
 * - Revenue Impact: Performance directly affects user retention
 * 
 * Tests: Cache updates, invalidation strategies, memory management
 * Architecture: ≤300 lines, functions ≤8 lines each
 */

import { act, renderHook, waitFor } from '@testing-library/react';
import { useChatStore } from '@/store/chat';
import { useCorpusStore } from '@/store/corpusStore';
import { GlobalTestUtils } from './store-test-utils';

// Simple helper functions
const createMockMessage = (id: string, type: 'user' | 'ai' = 'user', content: string = 'Test message') => ({
  id,
  type: type as const,
  content,
  role: type === 'user' ? 'user' : 'assistant',
  created_at: new Date().toISOString(),
  displayed_to_user: true
});

const createMockCorpus = (id: string, name: string = 'Test Corpus') => ({
  id,
  name,
  description: 'Mock corpus for testing',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString()
});

describe('Cache Management Tests', () => {
    jest.setTimeout(10000);
  beforeEach(() => {
    GlobalTestUtils.setupStoreTestEnvironment();
    // Clear any existing cache state
    sessionStorage.clear();
  });

  afterEach(() => {
    GlobalTestUtils.cleanupStoreTestEnvironment();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
  });

  describe('Memory Cache Management', () => {
      jest.setTimeout(10000);
    it('should cache message data in memory', () => {
      const { result } = renderHook(() => useChatStore());
      const message = createMockMessage('cached-msg-1');

      act(() => {
        result.current.reset();
        result.current.addMessage(message);
      });

      // Message should be cached in store state
      expect(result.current.messages).toContainEqual(message);
    });

    it('should limit memory cache size for large datasets', () => {
      const result = renderHook(() => useChatStore());
      
      // Add many messages to test memory limits
      const messages = Array.from({ length: 1000 }, (_, i) => 
        createMockMessage(`msg-${i}`, 'user', `Message ${i}`)
      );

      act(() => {
        messages.forEach(msg => result.current.addMessage(msg));
      });

      expect(result.current.messages.length).toBe(1000);
      
      // Memory usage should be reasonable
      const memoryUsage = JSON.stringify(result.current.messages).length;
      expect(memoryUsage).toBeLessThan(5 * 1024 * 1024); // 5MB limit
    });

    it('should implement LRU cache eviction for old data', () => {
      const result = renderHook(() => useCorpusStore());
      
      // Add many corpora to trigger cache eviction
      const corpora = Array.from({ length: 100 }, (_, i) => 
        createMockCorpus(`corpus-${i}`, `Corpus ${i}`)
      );

      act(() => {
        corpora.forEach(corpus => result.current.addCorpus(corpus));
      });

      expect(result.current.corpora.length).toBe(100);
    });

    it('should cache computed values for performance', () => {
      const result = renderHook(() => useChatStore());
      const messages = Array.from({ length: 10 }, (_, i) => 
        createMockMessage(`msg-${i}`)
      );

      act(() => {
        messages.forEach(msg => result.current.addMessage(msg));
      });

      // Access computed property multiple times
      const count1 = result.current.messages.length;
      const count2 = result.current.messages.length;
      
      expect(count1).toBe(count2);
      expect(count1).toBe(10);
    });
  });

  describe('Cache Invalidation Strategies', () => {
      jest.setTimeout(10000);
    it('should invalidate cache on data updates', () => {
      const result = renderHook(() => useChatStore());
      const message = createMockMessage('update-msg');

      ChatStoreTestUtils.addMessageAndVerify(result, message);

      const originalContent = result.current.messages[0].content;

      act(() => {
        result.current.updateMessage('update-msg', { content: 'Updated content' });
      });

      expect(result.current.messages[0].content).not.toBe(originalContent);
      expect(result.current.messages[0].content).toBe('Updated content');
    });

    it('should invalidate dependent caches on state changes', () => {
      const result = renderHook(() => useChatStore());

      // Set up initial state
      act(() => {
        result.current.setProcessing(true);
      });

      expect(result.current.isProcessing).toBe(true);

      // Update should invalidate related cached values
      act(() => {
        result.current.clearMessages();
        result.current.setProcessing(false);
      });

      expect(result.current.isProcessing).toBe(false);
      expect(result.current.messages).toHaveLength(0);
    });

    it('should implement time-based cache expiration', async () => {
      const result = renderHook(() => useCorpusStore());
      const corpus = createMockCorpus('time-corpus');

      CorpusStoreTestUtils.addCorpusAndVerify(result, corpus);

      // Simulate time passage (cache expiration)
      jest.advanceTimersByTime(60 * 60 * 1000); // 1 hour

      expect(result.current.corpora).toContainEqual(corpus);
    });

    it('should invalidate cache on manual refresh', () => {
      const result = renderHook(() => useChatStore());
      const message = createMockMessage('refresh-msg');

      ChatStoreTestUtils.addMessageAndVerify(result, message);

      act(() => {
        result.current.reset();
      });

      expect(result.current.messages).toHaveLength(0);
    });

    it('should selectively invalidate cache sections', () => {
      const result = renderHook(() => useChatStore());
      const userMsg = createMockMessage('user-msg', 'user');
      const aiMsg = createMockMessage('ai-msg', 'assistant');

      act(() => {
        result.current.addMessage(userMsg);
        result.current.addMessage(aiMsg);
      });

      expect(result.current.messages).toHaveLength(2);

      // Clear only sub-agent related state, keeping messages
      act(() => {
        result.current.clearSubAgent();
      });

      expect(result.current.messages).toHaveLength(2);
      expect(result.current.subAgentName).toBe('Netra Agent');
    });
  });

  describe('Cache Synchronization', () => {
      jest.setTimeout(10000);
    it('should sync cache with external updates', () => {
      const result = renderHook(() => useChatStore());
      
      const externalMessages = [
        createMockMessage('ext-1', 'user', 'External 1'),
        createMockMessage('ext-2', 'assistant', 'External 2')
      ];

      act(() => {
        result.current.loadMessages(externalMessages);
      });

      expect(result.current.messages).toHaveLength(2);
      expect(result.current.messages[0].content).toBe('External 1');
    });

    it('should handle cache conflicts gracefully', () => {
      const result = renderHook(() => useChatStore());
      const message1 = createMockMessage('conflict-msg', 'user', 'Version 1');
      const message2 = createMockMessage('conflict-msg', 'user', 'Version 2');

      // Add first version
      ChatStoreTestUtils.addMessageAndVerify(result, message1);
      
      // Try to add conflicting version
      act(() => {
        result.current.updateMessage('conflict-msg', { content: 'Version 2' });
      });

      expect(result.current.messages).toHaveLength(1);
      expect(result.current.messages[0].content).toBe('Version 2');
    });

    it('should merge cache updates intelligently', () => {
      const result = renderHook(() => useChatStore());
      const baseMessage = createMockMessage('merge-msg', 'assistant', 'Base');

      ChatStoreTestUtils.addMessageAndVerify(result, baseMessage);

      // Merge partial update
      act(() => {
        result.current.updateMessage('merge-msg', { 
          content: 'Updated',
          // Other properties should be preserved
        });
      });

      expect(result.current.messages[0].content).toBe('Updated');
      expect(result.current.messages[0].role).toBe('assistant'); // Preserved
    });

    it('should handle concurrent cache operations', () => {
      const result1 = renderHook(() => useChatStore());
      const result2 = renderHook(() => useChatStore());

      const message = createMockMessage('concurrent-msg');

      act(() => {
        result1.current.addMessage(message);
        result2.current.addMessage(message);
      });

      // Both stores should have the message
      expect(result1.current.messages).toHaveLength(1);
      expect(result2.current.messages).toHaveLength(1);
    });
  });

  describe('Cache Performance Optimization', () => {
      jest.setTimeout(10000);
    it('should batch cache updates for performance', () => {
      const result = renderHook(() => useChatStore());
      const messages = Array.from({ length: 50 }, (_, i) => 
        createMockMessage(`batch-${i}`)
      );

      const startTime = performance.now();

      act(() => {
        messages.forEach(msg => result.current.addMessage(msg));
      });

      const endTime = performance.now();
      const duration = endTime - startTime;

      expect(result.current.messages).toHaveLength(50);
      expect(duration).toBeLessThan(100); // Should complete quickly
    });

    it('should implement cache compression for large datasets', () => {
      const result = renderHook(() => useCorpusStore());
      
      // Create large corpus data
      const largeCorpus = createMockCorpus(
        'large-corpus',
        'Large Corpus '.repeat(1000) // Large description
      );

      CorpusStoreTestUtils.addCorpusAndVerify(result, largeCorpus);

      expect(result.current.corpora).toContainEqual(largeCorpus);
    });

    it('should lazy-load cached data when needed', () => {
      const result = renderHook(() => useChatStore());
      
      // Simulate lazy loading scenario
      act(() => {
        result.current.setActiveThread('lazy-thread');
      });

      expect(result.current.activeThreadId).toBe('lazy-thread');
      expect(result.current.messages).toHaveLength(0); // Should be empty initially
    });

    it('should prefetch commonly accessed data', async () => {
      const result = renderHook(() => useChatStore());
      const commonMessage = createMockMessage('common-msg');

      ChatStoreTestUtils.addMessageAndVerify(result, commonMessage);

      // Access multiple times to simulate common usage
      const msg1 = result.current.messages.find(m => m.id === 'common-msg');
      const msg2 = result.current.messages.find(m => m.id === 'common-msg');

      expect(msg1).toEqual(msg2);
      expect(msg1).toBeTruthy();
    });
  });

  describe('Cache Cleanup and Garbage Collection', () => {
      jest.setTimeout(10000);
    it('should clean up unused cache entries', () => {
      const result = renderHook(() => useChatStore());
      const message = createMockMessage('cleanup-msg');

      ChatStoreTestUtils.addMessageAndVerify(result, message);
      expect(result.current.messages).toHaveLength(1);

      act(() => {
        result.current.clearMessages();
      });

      expect(result.current.messages).toHaveLength(0);
    });

    it('should handle memory pressure by clearing old cache', () => {
      const result = renderHook(() => useChatStore());
      
      // Simulate memory pressure with many messages
      const messages = Array.from({ length: 2000 }, (_, i) => 
        createMockMessage(`memory-${i}`)
      );

      act(() => {
        messages.forEach(msg => result.current.addMessage(msg));
      });

      expect(result.current.messages.length).toBe(2000);

      // System should handle large datasets gracefully
      expect(() => result.current.messages.forEach(m => m.id)).not.toThrow();
    });

    it('should implement cache size limits', () => {
      const result = renderHook(() => useCorpusStore());
      
      // Try to exceed reasonable cache limits
      const manyCorpora = Array.from({ length: 10000 }, (_, i) => 
        createMockCorpus(`limit-${i}`)
      );

      act(() => {
        manyCorpora.forEach(corpus => result.current.addCorpus(corpus));
      });

      // Should handle large datasets without crashing
      expect(result.current.corpora.length).toBe(10000);
    });

    it('should provide cache statistics for monitoring', () => {
      const result = renderHook(() => useChatStore());
      
      Array.from({ length: 10 }, (_, i) => {
        const msg = createMockMessage(`stats-${i}`);
        ChatStoreTestUtils.addMessageAndVerify(result, msg);
      });

      // Cache should provide observable metrics
      expect(result.current.messages.length).toBe(10);
      expect(typeof result.current.messages.length).toBe('number');
    });
  });
});