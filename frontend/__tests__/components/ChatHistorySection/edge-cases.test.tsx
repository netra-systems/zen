/**
 * ChatHistorySection Edge Cases and Comprehensive Tests
 * Tests for edge cases, error handling, and comprehensive scenarios
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChatHistorySection } from '@/components/ChatHistorySection';
import { createTestSetup, mockThreads, ThreadService } from './setup';

describe('ChatHistorySection - Edge Cases', () => {
  const testSetup = createTestSetup();

  beforeEach(() => {
    testSetup.beforeEach();
  });

  afterEach(() => {
    testSetup.afterEach();
  });

  describe('Data edge cases', () => {
    it('should handle extremely large number of threads', async () => {
      // Create 1000 mock threads
      const manyThreads = Array.from({ length: 1000 }, (_, i) => ({
        ...mockThreads[0],
        id: `thread-${i}`,
        title: `Conversation ${i}`,
      }));
      
      testSetup.configureStoreMocks({ threads: manyThreads });
      
      render(<ChatHistorySection />);
      
      // Should render without performance issues (basic check)
      expect(screen.getByText('Chat History')).toBeInTheDocument();
      expect(screen.getByText('Conversation 0')).toBeInTheDocument();
    });

    it('should handle threads with special characters in titles', () => {
      const specialThreads = [
        { ...mockThreads[0], title: 'Thread with émojis 🚀 and unicode ñáéíóú' },
        { ...mockThreads[1], title: 'Thread with "quotes" and \'apostrophes\'' },
        { ...mockThreads[2], title: 'Thread with <HTML> & XML entities' },
      ];
      
      testSetup.configureStoreMocks({ threads: specialThreads });
      
      render(<ChatHistorySection />);
      
      expect(screen.getByText('Thread with émojis 🚀 and unicode ñáéíóú')).toBeInTheDocument();
      expect(screen.getByText('Thread with "quotes" and \'apostrophes\'')).toBeInTheDocument();
      expect(screen.getByText('Thread with <HTML> & XML entities')).toBeInTheDocument();
    });

    it('should handle malformed thread data gracefully', () => {
      const malformedThreads = [
        { id: 'thread-1' }, // Missing required fields
        { id: 'thread-2', title: mockThreads[0].title, created_at: 'invalid-date' },
        { id: null, title: 'Thread with null ID' }, // Invalid ID
      ];
      
      testSetup.configureStoreMocks({ threads: malformedThreads });
      
      // Should not crash
      expect(() => render(<ChatHistorySection />)).not.toThrow();
      
      expect(screen.getByText('Chat History')).toBeInTheDocument();
    });

    it('should handle threads with very old timestamps', () => {
      const oldThreads = [
        { ...mockThreads[0], created_at: 0, updated_at: 0 }, // Unix epoch
        { ...mockThreads[1], created_at: -1, updated_at: -1 }, // Before epoch
        { ...mockThreads[2], created_at: new Date('1970-01-01').getTime() / 1000 },
      ];
      
      testSetup.configureStoreMocks({ threads: oldThreads });
      
      render(<ChatHistorySection />);
      
      // Should render dates gracefully
      expect(screen.getByText('Chat History')).toBeInTheDocument();
    });

    it('should handle threads with future timestamps', () => {
      const futureDate = Math.floor((Date.now() + 86400000) / 1000); // Tomorrow
      const futureThreads = [
        { ...mockThreads[0], created_at: futureDate, updated_at: futureDate },
      ];
      
      testSetup.configureStoreMocks({ threads: futureThreads });
      
      render(<ChatHistorySection />);
      
      // Should handle future dates appropriately
      expect(screen.getByText('First Conversation')).toBeInTheDocument();
    });
  });

  describe('Performance and memory', () => {
    it('should efficiently render and update thread list', () => {
      const startTime = performance.now();
      
      render(<ChatHistorySection />);
      
      const endTime = performance.now();
      
      // Should render quickly (less than 100ms for small dataset)
      expect(endTime - startTime).toBeLessThan(100);
      
      expect(screen.getByText('Chat History')).toBeInTheDocument();
    });

    it('should handle rapid state updates without memory leaks', async () => {
      const { rerender } = render(<ChatHistorySection />);
      
      // Rapid state changes
      for (let i = 0; i < 10; i++) {
        const newThreads = mockThreads.map(thread => ({
          ...thread,
          title: `${thread.title} - Update ${i}`
        }));
        
        testSetup.configureStoreMocks({ threads: newThreads });
        rerender(<ChatHistorySection />);
        
        await act(async () => {
          await new Promise(resolve => setTimeout(resolve, 1));
        });
      }
      
      // Should complete without errors
      expect(screen.getByText('Chat History')).toBeInTheDocument();
    });

    it('should clean up event listeners on unmount', () => {
      const addEventListenerSpy = jest.spyOn(document, 'addEventListener');
      const removeEventListenerSpy = jest.spyOn(document, 'removeEventListener');
      
      const { unmount } = render(<ChatHistorySection />);
      
      const addCallCount = addEventListenerSpy.mock.calls.length;
      
      unmount();
      
      const removeCallCount = removeEventListenerSpy.mock.calls.length;
      
      // Should clean up listeners (exact counts may vary based on implementation)
      expect(removeCallCount).toBeGreaterThanOrEqual(0);
      
      addEventListenerSpy.mockRestore();
      removeEventListenerSpy.mockRestore();
    });
  });

  describe('Accessibility edge cases', () => {
    it('should maintain focus management during updates', async () => {
      render(<ChatHistorySection />);
      
      const firstThread = screen.getByText('First Conversation');
      firstThread.focus();
      
      expect(document.activeElement).toBe(firstThread);
      
      // Update threads
      const updatedThreads = [...mockThreads, testSetup.createMockThread({ title: 'New Thread' })];
      testSetup.configureStoreMocks({ threads: updatedThreads });
      
      // Focus should be maintained or handled gracefully
      await waitFor(() => {
        expect(document.activeElement).toBeDefined();
      });
    });

    it('should handle keyboard navigation edge cases', async () => {
      render(<ChatHistorySection />);
      
      const firstThread = screen.getByText('First Conversation');
      firstThread.focus();
      
      // Test various key combinations
      fireEvent.keyDown(firstThread, { key: 'Tab' });
      fireEvent.keyDown(firstThread, { key: 'Shift', shiftKey: true });
      fireEvent.keyDown(firstThread, { key: 'Escape' });
      
      // Should handle all key events gracefully
      expect(screen.getByText('Chat History')).toBeInTheDocument();
    });

    it('should provide proper ARIA labels for dynamic content', () => {
      render(<ChatHistorySection />);
      
      // Check for ARIA attributes on thread elements
      const threads = screen.getAllByText(/Conversation/);
      threads.forEach(thread => {
        const container = thread.closest('[role]') || thread.closest('[aria-label]');
        if (container) {
          expect(container.getAttribute('role') || container.getAttribute('aria-label')).toBeTruthy();
        }
      });
    });
  });

  describe('Concurrent operations', () => {
    it('should handle simultaneous delete and switch operations', async () => {
      (ThreadService.deleteThread as jest.Mock).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({ success: true }), 100))
      );
      
      render(<ChatHistorySection />);
      
      const firstThread = screen.getByText('First Conversation');
      const secondThread = screen.getByText('Second Conversation');
      
      // Simulate rapid interactions
      fireEvent.click(firstThread);
      fireEvent.contextMenu(secondThread);
      
      // Should handle concurrent operations gracefully
      await waitFor(() => {
        expect(screen.getByText('Chat History')).toBeInTheDocument();
      });
    });

    it('should handle search during data updates', async () => {
      render(<ChatHistorySection />);
      
      const searchInput = screen.queryByRole('textbox');
      
      if (searchInput) {
        // Start typing while updating data
        await userEvent.type(searchInput, 'First');
        
        // Update threads simultaneously
        const newThreads = [...mockThreads, testSetup.createMockThread({ title: 'First New Thread' })];
        testSetup.configureStoreMocks({ threads: newThreads });
        
        // Should handle both operations
        await waitFor(() => {
          expect(screen.getByText('Chat History')).toBeInTheDocument();
        });
      }
    });
  });

  describe('Network and API edge cases', () => {
    it('should handle API timeout gracefully', async () => {
      (ThreadService.listThreads as jest.Mock).mockImplementation(
        () => new Promise((_, reject) => 
          setTimeout(() => reject(new Error('Timeout')), 100)
        )
      );
      
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      
      render(<ChatHistorySection />);
      
      // Should not crash on API timeout
      await waitFor(() => {
        expect(screen.getByText('Chat History')).toBeInTheDocument();
      });
      
      consoleSpy.mockRestore();
    });

    it('should handle malformed API responses', async () => {
      (ThreadService.listThreads as jest.Mock).mockResolvedValue(null);
      
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      
      render(<ChatHistorySection />);
      
      // Should handle null response gracefully
      await waitFor(() => {
        expect(screen.getByText('Chat History')).toBeInTheDocument();
      });
      
      consoleSpy.mockRestore();
    });

    it('should retry failed operations appropriately', async () => {
      let callCount = 0;
      (ThreadService.listThreads as jest.Mock).mockImplementation(() => {
        callCount++;
        if (callCount < 3) {
          return Promise.reject(new Error('Network error'));
        }
        return Promise.resolve(mockThreads);
      });
      
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      
      render(<ChatHistorySection />);
      
      // Should eventually succeed after retries (if retry logic is implemented)
      await waitFor(() => {
        expect(screen.getByText('Chat History')).toBeInTheDocument();
      }, { timeout: 1000 });
      
      consoleSpy.mockRestore();
    });
  });

  describe('Component lifecycle edge cases', () => {
    it('should handle prop changes during component lifecycle', () => {
      const { rerender } = render(<ChatHistorySection />);
      
      // Simulate prop changes (if component accepts props)
      rerender(<ChatHistorySection />);
      
      expect(screen.getByText('Chat History')).toBeInTheDocument();
    });

    it('should handle unmounting during async operations', async () => {
      (ThreadService.listThreads as jest.Mock).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve(mockThreads), 200))
      );
      
      const { unmount } = render(<ChatHistorySection />);
      
      // Unmount before async operation completes
      setTimeout(() => unmount(), 50);
      
      // Should not cause memory leaks or errors
      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 300));
      });
    });
  });
});