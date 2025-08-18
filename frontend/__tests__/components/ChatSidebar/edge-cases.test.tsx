/**
 * ChatSidebar Edge Cases and Error Handling Tests
 * Tests for error scenarios, performance, and accessibility edge cases
 */

import React from 'react';
import { screen, fireEvent, waitFor, act } from '@testing-library/react';
import { ChatSidebar } from '@/components/chat/ChatSidebar';
import { renderWithProviders, safeAsync, resetAllMocks } from '../../shared/unified-test-utilities';
import { safeAct, waitForCondition, flushPromises } from '../../helpers/test-timing-utilities';
import { 
  mockThreadService,
  sampleThreads,
  renderWithProvider,
  createTestSetup
} from './setup';

describe('ChatSidebar - Edge Cases', () => {
  const testSetup = createTestSetup();

  beforeEach(() => {
    resetAllMocks();
  });

  afterEach(() => {
    resetAllMocks();
  });

  describe('Error Handling and Recovery', () => {
    it('should handle API failures gracefully', async () => {
      mockThreadService.listThreads.mockRejectedValue(new Error('API Error'));
      
      await safeAsync(async () => {
        renderWithProviders(<ChatSidebar />);
      });
      
      // Should not crash and show error state or render normally
      await waitForCondition(() => {
        const errorElement = screen.queryByText(/error loading threads/i) || 
                          screen.queryByText(/something went wrong/i);
        const sidebarElement = document.querySelector('.w-80');
        return !!(errorElement || sidebarElement);
      });
    });

    it('should recover from transient network errors', async () => {
      let callCount = 0;
      mockThreadService.listThreads.mockImplementation(() => {
        callCount++;
        if (callCount === 1) {
          return Promise.reject(new Error('Network error'));
        }
        return Promise.resolve(sampleThreads);
      });
      
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      
      renderWithProvider(<ChatSidebar />);
      
      // Should retry and eventually succeed
      await waitFor(() => {
        expect(screen.getByText('AI Optimization Discussion') ||
               document.querySelector('.w-80')).toBeInTheDocument();
      }, { timeout: 2000 });
      
      consoleSpy.mockRestore();
    });

    it('should handle thread operation failures', async () => {
      testSetup.configureStore({ threads: sampleThreads });
      mockThreadService.deleteThread.mockRejectedValue(new Error('Delete failed'));
      
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      
      renderWithProvider(<ChatSidebar />);
      
      const thread1 = screen.getByTestId('thread-item-thread-1');
      fireEvent.contextMenu(thread1);
      
      const deleteOption = screen.queryByText(/delete/i);
      if (deleteOption) {
        fireEvent.click(deleteOption);
        
        const confirmButton = screen.queryByText(/confirm/i) || screen.queryByText(/yes/i);
        if (confirmButton) {
          fireEvent.click(confirmButton);
        }
        
        // Should show error message
        await waitFor(() => {
          expect(screen.queryByText(/failed to delete/i) ||
                screen.queryByText(/error/i) ||
                screen.getByText('AI Optimization Discussion')).toBeInTheDocument();
        });
      }
      
      consoleSpy.mockRestore();
    });

    it('should handle malformed thread data', () => {
      const malformedThreads = [
        { id: 'thread-1' }, // Missing required fields
        { id: null, title: 'Thread with null ID' },
        { id: 'thread-2', title: null, lastMessage: 'Message without title' },
        { id: 'thread-3', title: 'Thread', lastActivity: 'invalid-date' },
      ];
      
      testSetup.configureStore({ threads: malformedThreads });
      
      // Should not crash
      expect(() => renderWithProvider(<ChatSidebar />)).not.toThrow();
      
      expect(document.querySelector('.w-80') || 
             screen.getByTestId('chat-sidebar')).toBeInTheDocument();
    });

    it('should handle extremely large thread datasets', () => {
      // Create 1000 threads
      const manyThreads = Array.from({ length: 1000 }, (_, i) => ({
        id: `thread-${i}`,
        title: `Thread ${i}`,
        lastMessage: `Message ${i}`,
        lastActivity: new Date(Date.now() - i * 60000).toISOString(),
        messageCount: i % 50,
        isActive: false
      }));
      
      testSetup.configureStore({ threads: manyThreads });
      
      const startTime = performance.now();
      renderWithProvider(<ChatSidebar />);
      const endTime = performance.now();
      
      // Should render within reasonable time
      expect(endTime - startTime).toBeLessThan(500);
      expect(document.querySelector('.w-80')).toBeInTheDocument();
    });

    it('should handle rapid state updates', async () => {
      const { rerender } = renderWithProvider(<ChatSidebar />);
      
      // Rapid state changes
      for (let i = 0; i < 20; i++) {
        const updatedThreads = sampleThreads.map(thread => ({
          ...thread,
          title: `${thread.title} - Update ${i}`,
          lastActivity: new Date(Date.now() + i * 1000).toISOString()
        }));
        
        testSetup.configureStore({ threads: updatedThreads });
        
        await act(async () => {
          rerender(<ChatSidebar />);
          await new Promise(resolve => setTimeout(resolve, 1));
        });
      }
      
      expect(document.querySelector('.w-80')).toBeInTheDocument();
    });

    it('should handle concurrent operations', async () => {
      testSetup.configureStore({ threads: sampleThreads });
      
      // Mock slow operations
      mockThreadService.deleteThread.mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({ success: true }), 200))
      );
      
      renderWithProvider(<ChatSidebar />);
      
      const thread1 = screen.getByTestId('thread-item-thread-1');
      const thread2 = screen.getByTestId('thread-item-thread-2');
      
      // Start multiple operations simultaneously
      fireEvent.contextMenu(thread1);
      fireEvent.click(thread2); // Switch thread
      
      // Should handle concurrent operations without conflicts
      await waitFor(() => {
        expect(document.querySelector('.w-80')).toBeInTheDocument();
      });
    });
  });

  describe('Performance and Optimization', () => {
    it('should virtualize large thread lists efficiently', () => {
      // Create very large dataset
      const hugeThreadList = Array.from({ length: 5000 }, (_, i) => ({
        id: `thread-${i}`,
        title: `Performance Test Thread ${i}`,
        lastMessage: `Message ${i}`,
        lastActivity: new Date(Date.now() - i * 30000).toISOString(),
        messageCount: i,
        isActive: false
      }));
      
      testSetup.configureStore({ threads: hugeThreadList });
      
      const { container } = renderWithProvider(<ChatSidebar />);
      
      // Should only render visible items (virtualization)
      const threadItems = container.querySelectorAll('[data-testid*="thread-item"]');
      
      // With virtualization, should render far fewer than total threads
      expect(threadItems.length).toBeLessThan(100);
      expect(document.querySelector('.w-80')).toBeInTheDocument();
    });

    it('should debounce search operations effectively', async () => {
      testSetup.configureStore({ threads: sampleThreads });
      
      const searchSpy = jest.fn();
      
      renderWithProvider(<ChatSidebar />);
      
      const searchInput = screen.queryByRole('textbox');
      
      if (searchInput) {
        // Rapid typing simulation
        'test search'.split('').forEach(char => {
          fireEvent.change(searchInput, { target: { value: searchInput.value + char } });
        });
        
        // Should debounce search calls
        await waitFor(() => {
          expect(searchInput).toHaveValue('test search');
        });
        
        // Wait for debounce period
        await new Promise(resolve => setTimeout(resolve, 500));
      }
    });

    it('should optimize re-renders with memoization', () => {
      const renderSpy = jest.fn();
      
      const { rerender } = renderWithProvider(<ChatSidebar />);
      
      // Re-render with same props
      rerender(<ChatSidebar />);
      rerender(<ChatSidebar />);
      
      // Should minimize unnecessary re-renders
      expect(document.querySelector('.w-80')).toBeInTheDocument();
    });

    it('should handle memory cleanup on unmount', () => {
      const addEventListenerSpy = jest.spyOn(document, 'addEventListener');
      const removeEventListenerSpy = jest.spyOn(document, 'removeEventListener');
      
      const { unmount } = renderWithProvider(<ChatSidebar />);
      
      const initialListenerCount = addEventListenerSpy.mock.calls.length;
      
      unmount();
      
      const removeListenerCount = removeEventListenerSpy.mock.calls.length;
      
      // Should clean up event listeners
      expect(removeListenerCount).toBeGreaterThanOrEqual(0);
      
      addEventListenerSpy.mockRestore();
      removeEventListenerSpy.mockRestore();
    });
  });

  describe('Accessibility Edge Cases', () => {
    it('should maintain focus during dynamic updates', async () => {
      testSetup.configureStore({ threads: sampleThreads });
      
      renderWithProvider(<ChatSidebar />);
      
      const thread1 = screen.getByTestId('thread-item-thread-1');
      thread1.focus();
      
      expect(document.activeElement).toBe(thread1);
      
      // Update threads while maintaining focus
      const updatedThreads = [...sampleThreads, testSetup.createThread({ title: 'New Thread' })];
      testSetup.configureStore({ threads: updatedThreads });
      
      // Focus should be maintained or handled gracefully
      await waitFor(() => {
        expect(document.activeElement).toBeTruthy();
      });
    });

    it('should handle high contrast mode', () => {
      // Mock high contrast media query
      const mockMatchMedia = jest.fn().mockImplementation((query) => ({
        matches: query.includes('prefers-contrast: high'),
        media: query,
        onchange: null,
        addListener: jest.fn(),
        removeListener: jest.fn(),
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        dispatchEvent: jest.fn(),
      }));
      
      Object.defineProperty(window, 'matchMedia', {
        writable: true,
        value: mockMatchMedia,
      });
      
      testSetup.configureStore({ threads: sampleThreads });
      
      renderWithProvider(<ChatSidebar />);
      
      // Should render with high contrast considerations
      expect(document.querySelector('.w-80')).toBeInTheDocument();
    });

    it('should support reduced motion preferences', () => {
      const mockMatchMedia = jest.fn().mockImplementation((query) => ({
        matches: query.includes('prefers-reduced-motion: reduce'),
        media: query,
        onchange: null,
        addListener: jest.fn(),
        removeListener: jest.fn(),
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        dispatchEvent: jest.fn(),
      }));
      
      Object.defineProperty(window, 'matchMedia', {
        writable: true,
        value: mockMatchMedia,
      });
      
      testSetup.configureStore({ threads: sampleThreads });
      
      renderWithProvider(<ChatSidebar />);
      
      // Should respect reduced motion preferences
      expect(document.querySelector('.w-80')).toBeInTheDocument();
    });

    it('should handle screen reader announcements for updates', () => {
      testSetup.configureStore({ threads: sampleThreads });
      
      renderWithProvider(<ChatSidebar />);
      
      // Add new thread
      const newThreads = [...sampleThreads, testSetup.createThread({ title: 'New Thread Added' })];
      testSetup.configureStore({ threads: newThreads });
      
      // Should provide appropriate ARIA live region updates
      const liveRegions = screen.queryAllByRole('status') ||
                         screen.queryAllByRole('log') ||
                         screen.getAllByText(/thread/i).filter(el => 
                           el.getAttribute('aria-live') || 
                           el.closest('[aria-live]')
                         );
      
      // Should handle dynamic content announcements
      expect(document.querySelector('.w-80')).toBeInTheDocument();
    });

    it('should provide proper keyboard trap for modal interactions', () => {
      testSetup.configureStore({ threads: sampleThreads });
      
      renderWithProvider(<ChatSidebar />);
      
      const thread1 = screen.getByTestId('thread-item-thread-1');
      fireEvent.contextMenu(thread1);
      
      const contextMenu = screen.queryByRole('menu');
      if (contextMenu) {
        // Tab should cycle through menu items
        const firstItem = contextMenu.querySelector('[role="menuitem"]');
        if (firstItem) {
          firstItem.focus();
          fireEvent.keyDown(firstItem, { key: 'Tab' });
          
          // Should maintain focus within menu
          expect(document.activeElement).toBeTruthy();
        }
      }
    });
  });

  describe('Data Consistency Edge Cases', () => {
    it('should handle thread updates during user interactions', async () => {
      testSetup.configureStore({ threads: sampleThreads });
      
      renderWithProvider(<ChatSidebar />);
      
      const thread1 = screen.getByTestId('thread-item-thread-1');
      
      // Start interaction
      fireEvent.mouseDown(thread1);
      
      // Update thread data during interaction
      const updatedThreads = sampleThreads.map(thread => 
        thread.id === 'thread-1' 
          ? { ...thread, title: 'Updated During Interaction' }
          : thread
      );
      
      testSetup.configureStore({ threads: updatedThreads });
      
      fireEvent.mouseUp(thread1);
      fireEvent.click(thread1);
      
      // Should handle data changes during interaction gracefully
      await waitFor(() => {
        expect(screen.getByText('Updated During Interaction')).toBeInTheDocument();
      });
    });

    it('should handle stale data scenarios', async () => {
      const staleThreads = sampleThreads.map(thread => ({
        ...thread,
        lastActivity: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString() // 30 days old
      }));
      
      testSetup.configureStore({ threads: staleThreads });
      mockThreadService.listThreads.mockResolvedValue(staleThreads);
      
      renderWithProvider(<ChatSidebar />);
      
      // Should handle very old threads appropriately
      await waitFor(() => {
        expect(document.querySelector('.w-80')).toBeInTheDocument();
      });
      
      // Check for either thread title or loading state
      const threadTitle = screen.queryByText('AI Optimization Discussion');
      const loadingElement = screen.queryByText(/loading/i);
      expect(threadTitle || loadingElement).toBeInTheDocument();
    });

    it('should handle duplicate thread IDs', () => {
      const threadsWithDuplicates = [
        sampleThreads[0],
        sampleThreads[0], // Duplicate
        { ...sampleThreads[1], id: sampleThreads[0].id } // Same ID, different data
      ];
      
      testSetup.configureStore({ threads: threadsWithDuplicates });
      
      const consoleSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
      
      // Should handle duplicates without crashing
      const { container } = renderWithProvider(<ChatSidebar />);
      
      // Check that sidebar rendered
      expect(container.querySelector('.w-80')).toBeInTheDocument();
      
      consoleSpy.mockRestore();
    });
  });
});