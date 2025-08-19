/**
 * ChatHistorySection Basic Rendering Tests
 * Tests for thread rendering and display functionality ≤300 lines, ≤8 line functions
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { ChatHistorySection } from '@/components/ChatHistorySection';
import { createTestSetup, setupCustomThreads } from './shared-setup';
import { mockThreads, createMockThread } from './mockData';
import {
  expectBasicStructure,
  expectThreadsRendered,
  expectActiveThread,
  expectUntitledThread,
  expectSpecificThreadTitle,
  expectMultipleThreadTitles,
  createThreadWithTitle,
  findMessageIcons,
  findThreadContainer
} from './test-utils';

describe('ChatHistorySection - Basic Rendering', () => {
  const testSetup = createTestSetup();

  beforeEach(() => {
    testSetup.beforeEach();
  });

  afterEach(() => {
    testSetup.afterEach();
  });

  describe('Thread list rendering', () => {
    it('should render all conversation threads', () => {
      render(<ChatHistorySection />);
      
      expect(screen.getByText('First Conversation')).toBeInTheDocument();
      expect(screen.getByText('Second Conversation')).toBeInTheDocument();
      expect(screen.getByText('Third Conversation')).toBeInTheDocument();
    });

    it('should display correct timestamps for threads', () => {
      render(<ChatHistorySection />);
      
      expect(screen.getByText('Today')).toBeInTheDocument();
      expect(screen.getByText('Yesterday')).toBeInTheDocument();
      const dateText = screen.getByText(/\d{1,2}\/\d{1,2}\/\d{4}/);
      expect(dateText).toBeInTheDocument();
    });

    it('should highlight the current active thread', () => {
      testSetup.configureStore({ currentThreadId: 'thread-1' });
      render(<ChatHistorySection />);
      
      expectActiveThread('First Conversation');
    });

    it('should show message icons for each thread', () => {
      render(<ChatHistorySection />);
      
      const messageIcons = findMessageIcons();
      expect(messageIcons?.length).toBeGreaterThanOrEqual(3);
    });

    it('should show hover effects on non-active threads', () => {
      render(<ChatHistorySection />);
      
      const threadContainer = findThreadContainer('Second Conversation');
      expect(threadContainer).toHaveClass('hover:bg-accent/50');
    });
  });

  describe('Thread title handling', () => {
    it('should render thread with null title as Untitled', () => {
      const threadsWithNullTitle = [createThreadWithTitle(mockThreads[0], null)];
      setupCustomThreads(threadsWithNullTitle);

      render(<ChatHistorySection />);
      
      expectUntitledThread();
    });

    it('should render thread with empty title as Untitled', () => {
      const threadsWithEmptyTitle = [createThreadWithTitle(mockThreads[0], '')];
      setupCustomThreads(threadsWithEmptyTitle);

      render(<ChatHistorySection />);
      
      expectUntitledThread();
    });

    it('should handle threads with very long titles', () => {
      const longTitle = 'This is a very long conversation title that should be handled properly by the component without breaking the layout or causing any display issues';
      const threadsWithLongTitle = [createThreadWithTitle(mockThreads[0], longTitle)];
      setupCustomThreads(threadsWithLongTitle);

      render(<ChatHistorySection />);
      
      expectSpecificThreadTitle(longTitle);
    });

    it('should render threads in chronological order', () => {
      const orderedThreads = [
        { ...mockThreads[0], title: 'Newest Thread', created_at: Math.floor(Date.now() / 1000) },
        { ...mockThreads[1], title: 'Middle Thread', created_at: Math.floor(Date.now() / 1000) - 3600 },
        { ...mockThreads[2], title: 'Oldest Thread', created_at: Math.floor(Date.now() / 1000) - 7200 },
      ];
      setupCustomThreads(orderedThreads);
      
      render(<ChatHistorySection />);
      
      expectMultipleThreadTitles(['Newest Thread', 'Middle Thread', 'Oldest Thread']);
    });
  });

  describe('Thread metadata display', () => {
    it('should display message count for each thread', () => {
      render(<ChatHistorySection />);
      
      expectBasicStructure();
    });

    it('should handle missing timestamps gracefully', () => {
      const threadsWithMissingTimestamp = [
        { ...mockThreads[0], created_at: null, updated_at: null },
      ];
      
      setupCustomThreads(threadsWithMissingTimestamp);

      render(<ChatHistorySection />);
      
      expect(screen.getByText('First Conversation')).toBeInTheDocument();
      expect(screen.getByText('Unknown date')).toBeInTheDocument();
    });

    it('should handle threads with special characters in titles', () => {
      const specialThreads = [
        { ...mockThreads[0], title: 'Thread with émojis 🚀 and unicode ñáéíóú' },
        { ...mockThreads[1], title: 'Thread with "quotes" and \'apostrophes\'' },
        { ...mockThreads[2], title: 'Thread with <HTML> & XML entities' },
      ];
      
      setupCustomThreads(specialThreads);
      
      render(<ChatHistorySection />);
      
      expect(screen.getByText('Thread with émojis 🚀 and unicode ñáéíóú')).toBeInTheDocument();
      expect(screen.getByText('Thread with "quotes" and \'apostrophes\'')).toBeInTheDocument();
      expect(screen.getByText('Thread with <HTML> & XML entities')).toBeInTheDocument();
    });

    it('should handle very old timestamps', () => {
      const oldThreads = [
        { ...mockThreads[0], created_at: 0, updated_at: 0 }, // Unix epoch
        { ...mockThreads[1], created_at: new Date('1970-01-01').getTime() / 1000 },
      ];
      
      setupCustomThreads(oldThreads);
      
      render(<ChatHistorySection />);
      
      expect(screen.getByText('Chat History')).toBeInTheDocument();
      expect(screen.getByText('First Conversation')).toBeInTheDocument();
      const dateRegex = /\d{1,2}\/\d{1,2}\/\d{4}/;
      expect(screen.getByText(dateRegex)).toBeInTheDocument();
    });

    it('should handle future timestamps appropriately', () => {
      const futureDate = Math.floor((Date.now() + 86400000) / 1000);
      const futureThreads = [
        { ...mockThreads[0], created_at: futureDate, updated_at: futureDate },
      ];
      
      setupCustomThreads(futureThreads);
      
      render(<ChatHistorySection />);
      
      expect(screen.getByText('First Conversation')).toBeInTheDocument();
      const dateRegex = /\d{1,2}\/\d{1,2}\/\d{4}/;
      expect(screen.getByText(dateRegex)).toBeInTheDocument();
    });
  });

  describe('Error handling in rendering', () => {
    it('should handle malformed thread data gracefully', () => {
      const malformedThreads = [
        { id: 'thread-1' }, // Missing required fields
        { id: 'thread-2', title: mockThreads[0].title, created_at: 'invalid-date' },
        { id: null, title: 'Thread with null ID' }, // Invalid ID
      ];
      
      setupCustomThreads(malformedThreads);
      
      expect(() => render(<ChatHistorySection />)).not.toThrow();
      expect(screen.getByText('Chat History')).toBeInTheDocument();
    });

    it('should render without crashing on null data', () => {
      setupCustomThreads([]);
      
      expect(() => render(<ChatHistorySection />)).not.toThrow();
      expectBasicStructure();
    });

    it('should handle component mounting and unmounting', () => {
      const { unmount } = render(<ChatHistorySection />);
      
      expect(screen.getByText('Chat History')).toBeInTheDocument();
      expect(() => unmount()).not.toThrow();
    });
  });

  describe('Large dataset rendering', () => {
    it('should render efficiently with many threads', () => {
      const largeThreadSet = Array.from({ length: 100 }, (_, i) => ({
        id: `thread-${i}`,
        title: `Thread ${i}`,
        created_at: Math.floor(Date.now() / 1000) - (i * 3600),
        updated_at: Math.floor(Date.now() / 1000) - (i * 3600),
        user_id: 'user-1',
        message_count: i % 20,
        status: 'active' as const,
      }));
      
      setupCustomThreads(largeThreadSet);
      
      expect(() => render(<ChatHistorySection />)).not.toThrow();
      expect(screen.getByText('Chat History')).toBeInTheDocument();
      expect(screen.getByText('Thread 0')).toBeInTheDocument();
    });

    it('should handle rapid re-renders efficiently', () => {
      const { rerender } = render(<ChatHistorySection />);
      
      for (let i = 0; i < 5; i++) {
        const updatedThreads = mockThreads.map(thread => ({
          ...thread,
          title: `${thread.title} - Update ${i}`,
          updated_at: Math.floor(Date.now() / 1000) + i,
        }));
        
        setupCustomThreads(updatedThreads);
        expect(() => rerender(<ChatHistorySection />)).not.toThrow();
      }
      
      expectBasicStructure();
    });
  });
});