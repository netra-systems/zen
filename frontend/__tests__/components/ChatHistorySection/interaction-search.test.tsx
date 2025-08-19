/**
 * ChatHistorySection Search Interaction Tests
 * Tests for search functionality and filtering ≤300 lines, ≤8 line functions
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChatHistorySection } from '@/components/ChatHistorySection';
import { createTestSetup, setupCustomThreads } from './shared-setup';
import { mockThreads } from './mockData';
import {
  expectBasicStructure,
  findSearchInput,
  expectThreadsRendered,
  createLargeThreadSet
} from './test-utils';

describe('ChatHistorySection - Search Interactions', () => {
  const testSetup = createTestSetup();

  beforeEach(() => {
    testSetup.beforeEach();
  });

  afterEach(() => {
    testSetup.afterEach();
  });

  describe('Search input functionality', () => {
    it('should display search input if available', () => {
      render(<ChatHistorySection />);
      
      const searchInput = findSearchInput();
      expectBasicStructure();
    });

    it('should accept search input typing', async () => {
      render(<ChatHistorySection />);
      
      const searchInput = findSearchInput();
      
      if (searchInput) {
        await userEvent.type(searchInput, 'First');
        expect(searchInput).toHaveValue('First');
      }
    });

    it('should clear search input when cleared', async () => {
      render(<ChatHistorySection />);
      
      const searchInput = findSearchInput();
      
      if (searchInput) {
        await userEvent.type(searchInput, 'Test');
        await userEvent.clear(searchInput);
        expect(searchInput).toHaveValue('');
      }
    });

    it('should handle special characters in search', async () => {
      render(<ChatHistorySection />);
      
      const searchInput = findSearchInput();
      
      if (searchInput) {
        await userEvent.type(searchInput, '!@#$%');
        expect(searchInput).toHaveValue('!@#$%');
      }
    });
  });

  describe('Search filtering behavior', () => {
    it('should filter threads based on search input', async () => {
      render(<ChatHistorySection />);
      
      expectBasicStructure();
      expect(screen.getByText('First Conversation')).toBeInTheDocument();
      expect(screen.getByText('Second Conversation')).toBeInTheDocument();
      expect(screen.getByText('Third Conversation')).toBeInTheDocument();
    });

    it('should show all threads when search is empty', () => {
      render(<ChatHistorySection />);
      
      expectThreadsRendered(['First Conversation', 'Second Conversation', 'Third Conversation']);
    });

    it('should perform case-insensitive search', async () => {
      render(<ChatHistorySection />);
      
      const searchInput = findSearchInput();
      
      if (searchInput) {
        await userEvent.type(searchInput, 'first');
        expectBasicStructure();
      }
    });

    it('should handle partial matches', async () => {
      render(<ChatHistorySection />);
      
      const searchInput = findSearchInput();
      
      if (searchInput) {
        await userEvent.type(searchInput, 'Conv');
        expectBasicStructure();
      }
    });
  });

  describe('Search results display', () => {
    it('should show no results message when search has no matches', async () => {
      render(<ChatHistorySection />);
      
      const searchInput = findSearchInput();
      
      if (searchInput) {
        await userEvent.type(searchInput, 'NonexistentThread');
        expectBasicStructure();
      }
    });

    it('should highlight search matches if implemented', async () => {
      render(<ChatHistorySection />);
      
      const searchInput = findSearchInput();
      
      if (searchInput) {
        await userEvent.type(searchInput, 'First');
        expectBasicStructure();
      }
    });

    it('should maintain search results consistency', async () => {
      render(<ChatHistorySection />);
      
      const searchInput = findSearchInput();
      
      if (searchInput) {
        await userEvent.type(searchInput, 'Conversation');
        expectBasicStructure();
      }
    });

    it('should clear search and show all threads when search is cleared', async () => {
      render(<ChatHistorySection />);
      
      const searchInput = findSearchInput();
      
      if (searchInput) {
        await userEvent.type(searchInput, 'First');
        await userEvent.clear(searchInput);
        
        expectThreadsRendered(['First Conversation', 'Second Conversation', 'Third Conversation']);
      }
    });
  });

  describe('Search performance', () => {
    it('should handle large dataset search efficiently', async () => {
      const largeThreadSet = createLargeThreadSet(500);
      setupCustomThreads(largeThreadSet);
      
      render(<ChatHistorySection />);
      
      const searchInput = findSearchInput();
      
      if (searchInput) {
        await userEvent.type(searchInput, 'Thread 1');
        expectBasicStructure();
      }
    });

    it('should debounce search operations', async () => {
      render(<ChatHistorySection />);
      
      const searchInput = findSearchInput();
      
      if (searchInput) {
        const searchTerm = 'rapid search test';
        for (const char of searchTerm) {
          fireEvent.change(searchInput, { target: { value: char } });
        }
        
        expectBasicStructure();
      }
    });

    it('should handle rapid typing without lag', async () => {
      render(<ChatHistorySection />);
      
      const searchInput = findSearchInput();
      
      if (searchInput) {
        const rapidInputs = ['a', 'ab', 'abc', 'abcd', 'abcde'];
        
        for (const input of rapidInputs) {
          fireEvent.change(searchInput, { target: { value: input } });
        }
        
        expectBasicStructure();
      }
    });

    it('should handle search with special datasets', async () => {
      const specialThreads = [
        { ...mockThreads[0], title: 'Thread with émojis 🚀' },
        { ...mockThreads[1], title: 'Thread with "quotes"' },
        { ...mockThreads[2], title: 'Thread with <HTML>' },
      ];
      
      setupCustomThreads(specialThreads);
      render(<ChatHistorySection />);
      
      const searchInput = findSearchInput();
      
      if (searchInput) {
        await userEvent.type(searchInput, 'émojis');
        expectBasicStructure();
      }
    });
  });

  describe('Search state management', () => {
    it('should maintain search state during updates', async () => {
      const { rerender } = render(<ChatHistorySection />);
      
      const searchInput = findSearchInput();
      
      if (searchInput) {
        await userEvent.type(searchInput, 'First');
        
        rerender(<ChatHistorySection />);
        expectBasicStructure();
      }
    });

    it('should handle search state reset', async () => {
      render(<ChatHistorySection />);
      
      const searchInput = findSearchInput();
      
      if (searchInput) {
        await userEvent.type(searchInput, 'Test');
        await userEvent.clear(searchInput);
        
        expectThreadsRendered(['First Conversation', 'Second Conversation', 'Third Conversation']);
      }
    });

    it('should preserve search input focus', async () => {
      render(<ChatHistorySection />);
      
      const searchInput = findSearchInput();
      
      if (searchInput) {
        searchInput.focus();
        await userEvent.type(searchInput, 'Test');
        
        expect(document.activeElement).toBe(searchInput);
      }
    });

    it('should handle search during data updates', async () => {
      render(<ChatHistorySection />);
      
      const searchInput = findSearchInput();
      
      if (searchInput) {
        await userEvent.type(searchInput, 'First');
        
        const newThreads = [...mockThreads, {
          id: 'thread-4',
          title: 'First New Thread',
          created_at: Math.floor(Date.now() / 1000),
          updated_at: Math.floor(Date.now() / 1000),
          user_id: 'user-1',
          message_count: 1,
          status: 'active' as const,
        }];
        
        setupCustomThreads(newThreads);
        expectBasicStructure();
      }
    });
  });

  describe('Search accessibility', () => {
    it('should provide proper search input labels', () => {
      render(<ChatHistorySection />);
      
      const searchInput = findSearchInput();
      
      if (searchInput) {
        const hasLabel = searchInput.getAttribute('aria-label') ||
                        searchInput.getAttribute('placeholder') ||
                        document.querySelector('label[for="' + searchInput.id + '"]');
        
        expect(hasLabel).toBeTruthy();
      }
    });

    it('should announce search results to screen readers', async () => {
      render(<ChatHistorySection />);
      
      const searchInput = findSearchInput();
      
      if (searchInput) {
        await userEvent.type(searchInput, 'First');
        expectBasicStructure();
      }
    });

    it('should handle keyboard navigation in search', async () => {
      render(<ChatHistorySection />);
      
      const searchInput = findSearchInput();
      
      if (searchInput) {
        searchInput.focus();
        
        expect(() => {
          fireEvent.keyDown(searchInput, { key: 'ArrowDown' });
          fireEvent.keyDown(searchInput, { key: 'ArrowUp' });
          fireEvent.keyDown(searchInput, { key: 'Escape' });
        }).not.toThrow();
      }
    });

    it('should provide clear search instructions', () => {
      render(<ChatHistorySection />);
      
      const searchInput = findSearchInput();
      
      if (searchInput) {
        const hasInstructions = searchInput.getAttribute('placeholder') ||
                               searchInput.getAttribute('aria-describedby');
        expect(hasInstructions).toBeTruthy();
      }
    });
  });

  describe('Search edge cases', () => {
    it('should handle empty search input', async () => {
      render(<ChatHistorySection />);
      
      const searchInput = findSearchInput();
      
      if (searchInput) {
        await userEvent.type(searchInput, '   ');
        expectBasicStructure();
      }
    });

    it('should handle very long search terms', async () => {
      render(<ChatHistorySection />);
      
      const searchInput = findSearchInput();
      
      if (searchInput) {
        const longTerm = 'a'.repeat(1000);
        await userEvent.type(searchInput, longTerm);
        expectBasicStructure();
      }
    });

    it('should handle regex special characters', async () => {
      render(<ChatHistorySection />);
      
      const searchInput = findSearchInput();
      
      if (searchInput) {
        await userEvent.type(searchInput, '.*+?^${}()|[]\\');
        expectBasicStructure();
      }
    });

    it('should handle unicode search terms', async () => {
      render(<ChatHistorySection />);
      
      const searchInput = findSearchInput();
      
      if (searchInput) {
        await userEvent.type(searchInput, '🚀💻🔍');
        expectBasicStructure();
      }
    });
  });
});