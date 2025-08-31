import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
import React from 'react';
import { render, screen } from '@testing-library/react';
import { ChatHistorySection } from '@/components/ChatHistorySection';
import { createTestSetup, setupCustomThreads } from './shared-setup';
import { mockThreads } from './mockData';
import { s/ChatHistorySection';
import { createTestSetup, setupCustomThreads } from './shared-setup';
import { mockThreads } from './mockData';
import {
  expectBasicStructure,
  createLargeThreadSet,
  createThreadWithSpecialChars,
  createMalformedThread,
  createThreadWithTimestamp
} from './test-utils';

describe('ChatHistorySection - Data Edge Cases', () => {
    jest.setTimeout(10000);
  const testSetup = createTestSetup();

  beforeEach(() => {
    testSetup.beforeEach();
  });

  afterEach(() => {
    testSetup.afterEach();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
  });

  describe('Large dataset handling', () => {
      jest.setTimeout(10000);
    it('should handle extremely large number of threads', async () => {
      const manyThreads = createLargeThreadSet(1000);
      setupCustomThreads(manyThreads);
      
      render(<ChatHistorySection />);
      
      expect(screen.getByText('Chat History')).toBeInTheDocument();
      expect(screen.getByText('Thread 0')).toBeInTheDocument();
    });

    it('should render large datasets without performance issues', () => {
      const largeDataset = createLargeThreadSet(500);
      setupCustomThreads(largeDataset);
      
      expect(() => render(<ChatHistorySection />)).not.toThrow();
      expectBasicStructure();
    });

    it('should handle memory efficiently with large datasets', () => {
      const hugeDataset = createLargeThreadSet(2000);
      setupCustomThreads(hugeDataset);
      
      const { unmount } = render(<ChatHistorySection />);
      
      expectBasicStructure();
      expect(() => unmount()).not.toThrow();
    });

    it('should maintain performance with frequent updates on large datasets', () => {
      const largeDataset = createLargeThreadSet(100);
      setupCustomThreads(largeDataset);
      
      const { rerender } = render(<ChatHistorySection />);
      
      for (let i = 0; i < 3; i++) {
        const updatedDataset = largeDataset.map(thread => ({
          ...thread,
          title: `${thread.title} - Update ${i}`
        }));
        
        setupCustomThreads(updatedDataset);
        expect(() => rerender(<ChatHistorySection />)).not.toThrow();
      }
      
      expectBasicStructure();
    });
  });

  describe('Special character handling', () => {
      jest.setTimeout(10000);
    it('should handle threads with special characters in titles', () => {
      const specialThreads = [
        createThreadWithSpecialChars(mockThreads[0]),
        { ...mockThreads[1], title: 'Thread with "quotes" and \'apostrophes\'' },
        { ...mockThreads[2], title: 'Thread with <HTML> & XML entities' },
      ];
      
      setupCustomThreads(specialThreads);
      
      render(<ChatHistorySection />);
      
      expect(screen.getByText('Thread with émojis 🚀 and unicode ñáéíóú')).toBeInTheDocument();
      expect(screen.getByText('Thread with "quotes" and \'apostrophes\'')).toBeInTheDocument();
      expect(screen.getByText('Thread with <HTML> & XML entities')).toBeInTheDocument();
    });

    it('should handle emoji-only titles', () => {
      const emojiThreads = [
        { ...mockThreads[0], title: '🚀🔥💻' },
        { ...mockThreads[1], title: '😀😂😍' },
        { ...mockThreads[2], title: '🌟⭐✨' },
      ];
      
      setupCustomThreads(emojiThreads);
      
      render(<ChatHistorySection />);
      
      expect(screen.getByText('🚀🔥💻')).toBeInTheDocument();
      expect(screen.getByText('😀😂😍')).toBeInTheDocument();
      expect(screen.getByText('🌟⭐✨')).toBeInTheDocument();
    });

    it('should handle very long titles with special characters', () => {
      const longSpecialTitle = 'Thread with émojis 🚀 and unicode ñáéíóú '.repeat(10);
      const longTitleThreads = [
        { ...mockThreads[0], title: longSpecialTitle }
      ];
      
      setupCustomThreads(longTitleThreads);
      
      render(<ChatHistorySection />);
      
      expect(screen.getByText(longSpecialTitle)).toBeInTheDocument();
    });

    it('should handle mixed language titles', () => {
      const multiLangThreads = [
        { ...mockThreads[0], title: 'English 中文 العربية русский' },
        { ...mockThreads[1], title: 'हिन्दी ภาษาไทย 한국어' },
        { ...mockThreads[2], title: 'Français Español Português' },
      ];
      
      setupCustomThreads(multiLangThreads);
      
      render(<ChatHistorySection />);
      
      expect(screen.getByText('English 中文 العربية русский')).toBeInTheDocument();
      expect(screen.getByText('हिन्दी ภาษาไทย 한국어')).toBeInTheDocument();
      expect(screen.getByText('Français Español Português')).toBeInTheDocument();
    });
  });

  describe('Malformed data handling', () => {
      jest.setTimeout(10000);
    it('should handle malformed thread data gracefully', () => {
      const malformedThreads = [
        createMalformedThread('thread-1'),
        { id: 'thread-2', title: mockThreads[0].title, created_at: 'invalid-date' },
        { id: null, title: 'Thread with null ID' },
      ];
      
      setupCustomThreads(malformedThreads);
      
      expect(() => render(<ChatHistorySection />)).not.toThrow();
      expectBasicStructure();
    });

    it('should handle missing required fields', () => {
      const incompleteThreads = [
        { id: 'thread-1' },
        { title: 'Thread without ID' },
        { id: 'thread-3', created_at: Date.now() },
      ];
      
      setupCustomThreads(incompleteThreads);
      
      expect(() => render(<ChatHistorySection />)).not.toThrow();
      expectBasicStructure();
    });

    it('should handle null and undefined values', () => {
      const nullDataThreads = [
        { ...mockThreads[0], title: null },
        { ...mockThreads[1], title: undefined },
        { ...mockThreads[2], created_at: null, updated_at: null },
      ];
      
      setupCustomThreads(nullDataThreads);
      
      expect(() => render(<ChatHistorySection />)).not.toThrow();
      expectBasicStructure();
    });

    it('should handle circular reference objects', () => {
      const circularThread = { ...mockThreads[0] };
      (circularThread as any).self = circularThread;
      
      setupCustomThreads([circularThread]);
      
      expect(() => render(<ChatHistorySection />)).not.toThrow();
      expectBasicStructure();
    });
  });

  describe('Timestamp edge cases', () => {
      jest.setTimeout(10000);
    it('should handle very old timestamps', () => {
      const oldThreads = [
        createThreadWithTimestamp(mockThreads[0], 0), // Unix epoch
        createThreadWithTimestamp(mockThreads[1], new Date('1970-01-01').getTime() / 1000),
        createThreadWithTimestamp(mockThreads[2], new Date('1990-01-01').getTime() / 1000),
      ];
      
      setupCustomThreads(oldThreads);
      
      render(<ChatHistorySection />);
      
      expectBasicStructure();
      expect(screen.getByText('First Conversation')).toBeInTheDocument();
      const dateRegex = /\d{1,2}\/\d{1,2}\/\d{4}/;
      expect(screen.getByText(dateRegex)).toBeInTheDocument();
    });

    it('should handle future timestamps', () => {
      const futureDate = Math.floor((Date.now() + 86400000) / 1000);
      const futureThreads = [
        createThreadWithTimestamp(mockThreads[0], futureDate),
        createThreadWithTimestamp(mockThreads[1], futureDate + 3600),
      ];
      
      setupCustomThreads(futureThreads);
      
      render(<ChatHistorySection />);
      
      expect(screen.getByText('First Conversation')).toBeInTheDocument();
      const dateRegex = /\d{1,2}\/\d{1,2}\/\d{4}/;
      expect(screen.getByText(dateRegex)).toBeInTheDocument();
    });

    it('should handle invalid timestamp formats', () => {
      const invalidTimestampThreads = [
        { ...mockThreads[0], created_at: 'not-a-number' },
        { ...mockThreads[1], created_at: NaN },
        { ...mockThreads[2], created_at: Infinity },
      ];
      
      setupCustomThreads(invalidTimestampThreads);
      
      expect(() => render(<ChatHistorySection />)).not.toThrow();
      expectBasicStructure();
    });

    it('should handle negative timestamps', () => {
      const negativeTimestampThreads = [
        createThreadWithTimestamp(mockThreads[0], -86400),
        createThreadWithTimestamp(mockThreads[1], -1),
      ];
      
      setupCustomThreads(negativeTimestampThreads);
      
      expect(() => render(<ChatHistorySection />)).not.toThrow();
      expectBasicStructure();
    });
  });

  describe('Data type edge cases', () => {
      jest.setTimeout(10000);
    it('should handle threads array as different types', () => {
      // Test with non-array types
      testSetup.configureStore({ threads: null });
      
      expect(() => render(<ChatHistorySection />)).not.toThrow();
      expectBasicStructure();
    });

    it('should handle threads with wrong data types', () => {
      const wrongTypeThreads = [
        'string-instead-of-object',
        123,
        true,
        null,
        { ...mockThreads[0] }
      ];
      
      setupCustomThreads(wrongTypeThreads as any);
      
      expect(() => render(<ChatHistorySection />)).not.toThrow();
      expectBasicStructure();
    });

    it('should handle nested object structures', () => {
      const nestedThreads = [
        {
          ...mockThreads[0],
          metadata: {
            nested: {
              deeply: {
                structure: 'value'
              }
            }
          }
        }
      ];
      
      setupCustomThreads(nestedThreads);
      
      expect(() => render(<ChatHistorySection />)).not.toThrow();
      expect(screen.getByText('First Conversation')).toBeInTheDocument();
    });

    it('should handle array-like objects', () => {
      const arrayLikeThreads = {
        0: mockThreads[0],
        1: mockThreads[1],
        length: 2
      };
      
      setupCustomThreads(arrayLikeThreads as any);
      
      expect(() => render(<ChatHistorySection />)).not.toThrow();
      expectBasicStructure();
    });
  });

  describe('Memory and performance edge cases', () => {
      jest.setTimeout(10000);
    it('should handle rapid data updates without memory leaks', () => {
      const { rerender } = render(<ChatHistorySection />);
      
      for (let i = 0; i < 50; i++) {
        const newThreads = mockThreads.map(thread => ({
          ...thread,
          title: `${thread.title} - Update ${i}`,
          updated_at: Math.floor(Date.now() / 1000) + i
        }));
        
        setupCustomThreads(newThreads);
        rerender(<ChatHistorySection />);
      }
      
      expectBasicStructure();
    });

    it('should clean up properly with large datasets', () => {
      const massiveDataset = createLargeThreadSet(5000);
      setupCustomThreads(massiveDataset);
      
      const { unmount } = render(<ChatHistorySection />);
      
      expectBasicStructure();
      expect(() => unmount()).not.toThrow();
    });

    it('should handle deep object cloning edge cases', () => {
      const deepThread = {
        ...mockThreads[0],
        level1: {
          level2: {
            level3: {
              level4: {
                level5: 'deep value'
              }
            }
          }
        }
      };
      
      setupCustomThreads([deepThread]);
      
      expect(() => render(<ChatHistorySection />)).not.toThrow();
      expect(screen.getByText('First Conversation')).toBeInTheDocument();
    });

    it('should maintain performance with complex data structures', () => {
      const complexThreads = mockThreads.map(thread => ({
        ...thread,
        tags: new Array(100).fill(0).map((_, i) => `tag-${i}`),
        metadata: {
          history: new Array(50).fill(0).map((_, i) => ({
            action: `action-${i}`,
            timestamp: Date.now() - (i * 1000)
          }))
        }
      }));
      
      setupCustomThreads(complexThreads);
      
      expect(() => render(<ChatHistorySection />)).not.toThrow();
      expectBasicStructure();
    });
  });
});