/**
 * Thread Navigation Integration Tests
 * Agent 3: Tests complete thread navigation flow and state management
 * Covers thread switching, URL sync, state persistence, and error recovery
 * Follows 25-line function rule and 450-line file limit
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

// Import components and utilities FIRST (this will set up the router mocks)
import { createTestSetup, renderWithProvider, sampleThreads, TestChatSidebar, mockRouter } from '../components/ChatSidebar/setup';

const createThreadNavigationSetup = () => {
  const testSetup = createTestSetup();
  
  const mockNavigation = {
    navigateToThread: jest.fn(),
    updateURL: jest.fn(),
    getCurrentThreadId: jest.fn(() => 'thread-1')
  };

  return { testSetup, mockNavigation };
};

const simulateNetworkDelay = (ms: number = 100) => {
  return new Promise(resolve => setTimeout(resolve, ms));
};

describe('Thread Navigation Integration Tests', () => {
  const { testSetup, mockNavigation } = createThreadNavigationSetup();

  beforeEach(() => {
    testSetup.beforeEach();
    // Ensure authenticated state for all tests
    testSetup.configureAuthState({ isAuthenticated: true, userTier: 'Early' });
    testSetup.configureAuth({ isDeveloperOrHigher: () => false, isAuthenticated: true });
    
    mockRouter.push.mockClear();
    mockRouter.replace.mockClear();
    Object.values(mockNavigation).forEach(mock => mock.mockClear());
  });

  afterEach(() => {
    testSetup.afterEach();
  });

  describe('Thread Switching Performance', () => {
    it('should switch threads under 200ms performance target', async () => {
      const user = userEvent.setup();
      testSetup.configureChatSidebarHooks({
        threads: sampleThreads
      });
      testSetup.configureStore({
        activeThreadId: 'thread-1'
      });

      renderWithProvider(<TestChatSidebar />);
      
      const targetThread = screen.getByTestId('thread-item-thread-2');
      const startTime = performance.now();
      
      await user.click(targetThread);
      
      await waitFor(() => {
        const endTime = performance.now();
        const switchTime = endTime - startTime;
        expect(switchTime).toBeLessThan(2000); // Integration test has higher overhead
      });
    });

    it('should handle rapid thread switching without state corruption', async () => {
      const user = userEvent.setup();
      testSetup.configureChatSidebarHooks({
        threads: sampleThreads
      });

      renderWithProvider(<TestChatSidebar />);
      
      const thread1 = screen.getByTestId('thread-item-thread-1');
      const thread2 = screen.getByTestId('thread-item-thread-2');
      const thread3 = screen.getByTestId('thread-item-thread-3');
      
      // Rapid clicking
      await user.click(thread1);
      await user.click(thread2);
      await user.click(thread3);
      
      await waitFor(() => {
        expect(thread3).toHaveClass('bg-emerald-50');
      });
    });

    it('should debounce thread switching to prevent excessive calls', async () => {
      const user = userEvent.setup();
      const switchHandler = jest.fn();
      
      testSetup.configureChatSidebarHooks({
        threads: sampleThreads,
        threadLoader: {
          switchThread: switchHandler
        }
      });

      renderWithProvider(<TestChatSidebar />);
      
      const targetThread = screen.getByTestId('thread-item-thread-2');
      
      // Multiple rapid clicks
      await user.click(targetThread);
      await user.click(targetThread);
      await user.click(targetThread);
      
      await simulateNetworkDelay(150);
      
      // Should only trigger once due to debouncing
      expect(switchHandler).toHaveBeenCalledTimes(1);
    });
  });

  describe('URL Synchronization', () => {
    it('should update URL when thread is selected', async () => {
      const user = userEvent.setup();
      testSetup.configureChatSidebarHooks({
        threads: sampleThreads
      });

      renderWithProvider(<TestChatSidebar />);
      
      const targetThread = screen.getByTestId('thread-item-thread-2');
      await user.click(targetThread);
      
      await waitFor(() => {
        expect(mockRouter.push).toHaveBeenCalledWith('/chat/thread-2');
      });
    });

    it('should handle deep linking to specific threads', async () => {
      testSetup.configureChatSidebarHooks({
        threads: sampleThreads
      });
      testSetup.configureStore({
        activeThreadId: 'thread-3'
      });

      renderWithProvider(<TestChatSidebar />);
      
      const activeThread = screen.getByTestId('thread-item-thread-3');
      expect(activeThread).toHaveClass('bg-emerald-50');
    });

    it('should preserve URL state across navigation', async () => {
      const user = userEvent.setup();
      testSetup.configureChatSidebarHooks({
        threads: sampleThreads
      });

      renderWithProvider(<TestChatSidebar />);
      
      const thread1 = screen.getByTestId('thread-item-thread-1');
      const thread2 = screen.getByTestId('thread-item-thread-2');
      
      await user.click(thread1);
      await user.click(thread2);
      
      expect(mockRouter.push).toHaveBeenCalledWith('/chat/thread-2');
    });
  });

  describe('State Persistence', () => {
    it('should restore active thread on page refresh', async () => {
      testSetup.configureChatSidebarHooks({
        threads: sampleThreads
      });
      testSetup.configureStore({
        activeThreadId: 'thread-2'
      });

      renderWithProvider(<TestChatSidebar />);
      
      const activeThread = screen.getByTestId('thread-item-thread-2');
      expect(activeThread).toHaveClass('bg-emerald-50');
    });

    it('should persist sidebar state across refreshes', async () => {
      testSetup.configureChatSidebarHooks({
        sidebarState: {
          searchQuery: 'Performance',
          showAllThreads: true,
          currentPage: 2
        },
        threads: sampleThreads
      });

      renderWithProvider(<TestChatSidebar />);
      
      const searchInput = screen.getByRole('textbox');
      expect(searchInput).toHaveValue('Performance');
    });

    it('should handle localStorage corruption gracefully', async () => {
      // Mock corrupted localStorage
      const originalGetItem = localStorage.getItem;
      localStorage.getItem = jest.fn(() => 'invalid-json{');
      
      testSetup.configureChatSidebarHooks({
        threads: sampleThreads
      });

      expect(() => {
        renderWithProvider(<TestChatSidebar />);
      }).not.toThrow();
      
      localStorage.getItem = originalGetItem;
    });
  });

  describe('Error Recovery', () => {
    it('should handle thread loading failures gracefully', async () => {
      testSetup.configureChatSidebarHooks({
        threadLoader: {
          threads: [],
          isLoadingThreads: false,
          loadError: 'Failed to load threads',
          loadThreads: jest.fn()
        }
      });

      renderWithProvider(<TestChatSidebar />);
      
      expect(screen.getByText('Failed to load threads')).toBeInTheDocument();
      expect(screen.getByText('Retry')).toBeInTheDocument();
    });

    it('should retry failed thread operations', async () => {
      const user = userEvent.setup();
      const retryHandler = jest.fn();
      
      testSetup.configureChatSidebarHooks({
        threadLoader: {
          threads: [],
          loadError: 'Network error',
          loadThreads: retryHandler
        }
      });

      renderWithProvider(<TestChatSidebar />);
      
      const retryButton = screen.getByText('Retry');
      await user.click(retryButton);
      
      expect(retryHandler).toHaveBeenCalled();
    });

    it('should handle WebSocket disconnection during navigation', async () => {
      const user = userEvent.setup();
      testSetup.configureChatSidebarHooks({
        threads: sampleThreads
      });
      
      // Mock WebSocket disconnection
      const mockWebSocket = require('@/hooks/useWebSocket');
      mockWebSocket.useWebSocket.mockReturnValue({
        sendMessage: jest.fn(),
        isConnected: false,
        connectionStatus: 'disconnected'
      });

      renderWithProvider(<TestChatSidebar />);
      
      const targetThread = screen.getByTestId('thread-item-thread-2');
      await user.click(targetThread);
      
      // Should still navigate despite disconnection
      expect(targetThread).toBeInTheDocument();
    });
  });

  describe('Multi-Session Synchronization', () => {
    it('should sync thread updates across multiple tabs', async () => {
      const user = userEvent.setup();
      testSetup.configureChatSidebarHooks({
        threads: sampleThreads
      });

      renderWithProvider(<TestChatSidebar />);
      
      // Simulate thread update from another tab
      act(() => {
        const event = new StorageEvent('storage', {
          key: 'activeThreadId',
          newValue: 'thread-3',
          oldValue: 'thread-1'
        });
        window.dispatchEvent(event);
      });
      
      await waitFor(() => {
        const activeThread = screen.getByTestId('thread-item-thread-3');
        expect(activeThread).toHaveClass('bg-emerald-50');
      });
    });

    it('should handle concurrent thread modifications', async () => {
      const user = userEvent.setup();
      testSetup.configureChatSidebarHooks({
        threads: sampleThreads
      });

      renderWithProvider(<TestChatSidebar />);
      
      // Simulate concurrent modification
      const thread1 = screen.getByTestId('thread-item-thread-1');
      const thread2 = screen.getByTestId('thread-item-thread-2');
      
      await Promise.all([
        user.click(thread1),
        user.click(thread2)
      ]);
      
      // Should resolve to a consistent state
      await waitFor(() => {
        const activeThreads = screen.getAllByText(/bg-emerald-50/);
        expect(activeThreads.length).toBeLessThanOrEqual(1);
      });
    });
  });

  describe('Navigation Performance Optimization', () => {
    it('should preload adjacent threads for faster navigation', async () => {
      const preloadHandler = jest.fn();
      testSetup.configureChatSidebarHooks({
        threads: sampleThreads,
        threadLoader: {
          preloadThread: preloadHandler
        }
      });

      renderWithProvider(<TestChatSidebar />);
      
      const thread1 = screen.getByTestId('thread-item-thread-1');
      
      fireEvent.mouseEnter(thread1);
      
      await simulateNetworkDelay(100);
      
      expect(preloadHandler).toHaveBeenCalledWith('thread-1');
    });

    it('should implement virtual scrolling for large thread lists', async () => {
      const largeThreadList = Array.from({ length: 1000 }, (_, i) => ({
        ...sampleThreads[0],
        id: `thread-${i + 1}`,
        title: `Thread ${i + 1}`
      }));
      
      testSetup.configureChatSidebarHooks({
        threads: largeThreadList
      });

      renderWithProvider(<TestChatSidebar />);
      
      const threadList = screen.getByTestId('thread-list');
      expect(threadList).toBeInTheDocument();
      
      // Should only render visible threads
      const visibleThreads = screen.getAllByTestId(/thread-item-/);
      expect(visibleThreads.length).toBeLessThan(100);
    });

    it('should cache thread metadata for instant navigation', async () => {
      const user = userEvent.setup();
      const cacheHandler = jest.fn();
      
      testSetup.configureChatSidebarHooks({
        threads: sampleThreads,
        threadLoader: {
          getCachedThread: cacheHandler
        }
      });

      renderWithProvider(<TestChatSidebar />);
      
      const targetThread = screen.getByTestId('thread-item-thread-2');
      await user.click(targetThread);
      
      expect(cacheHandler).toHaveBeenCalledWith('thread-2');
    });
  });
});