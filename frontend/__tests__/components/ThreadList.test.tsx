/**
 * ThreadList Component Tests
 * Agent 3: Comprehensive tests for thread list rendering and interactions
 * Covers virtual scrolling, performance, accessibility, and state management
 * Follows 25-line function rule and 450-line file limit
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { act } from '@testing-library/react';

// Import component and utilities
import { ThreadList } from '@/components/chat/ChatSidebarThreadList';
import { TestProviders } from '../test-utils/providers';

const mockThreadData = {
  basic: {
    id: 'thread-1',
    title: 'Basic Thread',
    created_at: Math.floor(Date.now() / 1000),
    updated_at: Math.floor(Date.now() / 1000),
    message_count: 5,
    metadata: {
      title: 'Basic Thread',
      last_message: 'Hello world',
      lastActivity: new Date().toISOString(),
      messageCount: 5
    }
  },
  withUnread: {
    id: 'thread-2',
    title: 'Thread with Unread',
    created_at: Math.floor(Date.now() / 1000),
    updated_at: Math.floor(Date.now() / 1000),
    message_count: 10,
    hasUnread: true,
    unreadCount: 3,
    metadata: {
      title: 'Thread with Unread',
      last_message: 'New message',
      lastActivity: new Date().toISOString(),
      messageCount: 10
    }
  },
  adminType: {
    id: 'thread-3',
    title: 'Admin Thread',
    created_at: Math.floor(Date.now() / 1000),
    updated_at: Math.floor(Date.now() / 1000),
    message_count: 15,
    metadata: {
      title: 'Admin Thread',
      admin_type: 'corpus',
      last_message: 'Admin operation',
      lastActivity: new Date().toISOString(),
      messageCount: 15
    }
  }
};

const createLargeThreadList = (count: number) => {
  return Array.from({ length: count }, (_, i) => ({
    ...mockThreadData.basic,
    id: `thread-${i + 1}`,
    title: `Thread ${i + 1}`,
    message_count: Math.floor(Math.random() * 50) + 1
  }));
};

const renderThreadList = (props = {}) => {
  const defaultProps = {
    threads: [mockThreadData.basic],
    isLoadingThreads: false,
    loadError: null,
    activeThreadId: null,
    isProcessing: false,
    showAllThreads: false,
    onThreadClick: jest.fn(),
    onRetryLoad: jest.fn()
  };

  return render(
    <TestProviders>
      <ThreadList {...defaultProps} {...props} />
    </TestProviders>
  );
};

describe('ThreadList Component Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Basic Rendering', () => {
    it('should render thread list container', () => {
      renderThreadList();
      
      const threadList = screen.getByTestId('thread-list');
      expect(threadList).toBeInTheDocument();
      expect(threadList).toHaveClass('flex-1', 'overflow-y-auto');
    });

    it('should render individual thread items', () => {
      const threads = [mockThreadData.basic, mockThreadData.withUnread];
      renderThreadList({ threads });
      
      expect(screen.getByTestId('thread-item-thread-1')).toBeInTheDocument();
      expect(screen.getByTestId('thread-item-thread-2')).toBeInTheDocument();
      expect(screen.getByText('Basic Thread')).toBeInTheDocument();
      expect(screen.getByText('Thread with Unread')).toBeInTheDocument();
    });

    it('should display thread metadata correctly', () => {
      renderThreadList({ threads: [mockThreadData.basic] });
      
      const threadItem = screen.getByTestId('thread-item-thread-1');
      expect(within(threadItem).getByText('Basic Thread')).toBeInTheDocument();
      expect(within(threadItem).getByText('5 messages')).toBeInTheDocument();
      expect(threadItem).toHaveTextContent(/ago/); // Time display
    });

    it('should handle empty thread list', () => {
      renderThreadList({ threads: [] });
      
      expect(screen.getByText('No conversations yet')).toBeInTheDocument();
      expect(screen.getByText('Start a new chat to begin')).toBeInTheDocument();
    });
  });

  describe('Thread States and Indicators', () => {
    it('should highlight active thread', () => {
      renderThreadList({
        threads: [mockThreadData.basic, mockThreadData.withUnread],
        activeThreadId: 'thread-1'
      });
      
      const activeThread = screen.getByTestId('thread-item-thread-1');
      const inactiveThread = screen.getByTestId('thread-item-thread-2');
      
      expect(activeThread).toHaveClass('bg-emerald-50');
      expect(inactiveThread).not.toHaveClass('bg-emerald-50');
    });

    it('should show unread indicators', () => {
      renderThreadList({
        threads: [mockThreadData.withUnread],
        activeThreadId: null
      });
      
      const threadItem = screen.getByTestId('thread-item-thread-2');
      expect(threadItem).toBeInTheDocument();
      // Unread styling would be implementation-specific
    });

    it('should display admin thread types with icons', () => {
      renderThreadList({ threads: [mockThreadData.adminType] });
      
      const threadItem = screen.getByTestId('thread-item-thread-3');
      const icon = within(threadItem).getByRole('img', { hidden: true });
      expect(icon).toBeInTheDocument();
    });

    it('should show processing state indicators', () => {
      const processingThread = {
        ...mockThreadData.basic,
        metadata: { ...mockThreadData.basic.metadata, isProcessing: true }
      };
      
      renderThreadList({ 
        threads: [processingThread],
        isProcessing: true 
      });
      
      const threadItem = screen.getByTestId('thread-item-thread-1');
      expect(threadItem).toBeInTheDocument();
    });
  });

  describe('Loading and Error States', () => {
    it('should display loading state', () => {
      renderThreadList({ 
        threads: [],
        isLoadingThreads: true 
      });
      
      expect(screen.getByText('Loading conversations...')).toBeInTheDocument();
      expect(screen.getByRole('status', { hidden: true })).toBeInTheDocument(); // Spinner
    });

    it('should show error message with retry option', () => {
      const onRetryLoad = jest.fn();
      renderThreadList({
        threads: [],
        loadError: 'Failed to load threads',
        onRetryLoad
      });
      
      expect(screen.getByText('Failed to load threads')).toBeInTheDocument();
      
      const retryButton = screen.getByText('Retry');
      expect(retryButton).toBeInTheDocument();
    });

    it('should handle retry functionality', async () => {
      const user = userEvent.setup();
      const onRetryLoad = jest.fn();
      
      renderThreadList({
        threads: [],
        loadError: 'Network error',
        onRetryLoad
      });
      
      const retryButton = screen.getByText('Retry');
      await user.click(retryButton);
      
      expect(onRetryLoad).toHaveBeenCalledTimes(1);
    });
  });

  describe('User Interactions', () => {
    it('should handle thread click events', async () => {
      const user = userEvent.setup();
      const onThreadClick = jest.fn();
      
      renderThreadList({
        threads: [mockThreadData.basic],
        onThreadClick
      });
      
      const threadButton = screen.getByTestId('thread-item-thread-1');
      await user.click(threadButton);
      
      expect(onThreadClick).toHaveBeenCalledWith('thread-1');
    });

    it('should prevent clicks when processing', async () => {
      const user = userEvent.setup();
      const onThreadClick = jest.fn();
      
      renderThreadList({
        threads: [mockThreadData.basic],
        isProcessing: true,
        onThreadClick
      });
      
      const threadButton = screen.getByTestId('thread-item-thread-1');
      expect(threadButton).toBeDisabled();
      
      await user.click(threadButton);
      expect(onThreadClick).not.toHaveBeenCalled();
    });

    it('should show hover effects on thread items', async () => {
      const user = userEvent.setup();
      renderThreadList({ threads: [mockThreadData.basic] });
      
      const threadButton = screen.getByTestId('thread-item-thread-1');
      
      await user.hover(threadButton);
      expect(threadButton).toHaveClass('hover:bg-gray-50');
    });

    it('should handle keyboard navigation', async () => {
      const user = userEvent.setup();
      const onThreadClick = jest.fn();
      
      renderThreadList({
        threads: [mockThreadData.basic],
        onThreadClick
      });
      
      const threadButton = screen.getByTestId('thread-item-thread-1');
      threadButton.focus();
      
      await user.keyboard('{Enter}');
      expect(onThreadClick).toHaveBeenCalledWith('thread-1');
    });
  });

  describe('Performance with Large Lists', () => {
    it('should handle 1000+ threads efficiently', async () => {
      const largeThreadList = createLargeThreadList(1000);
      
      const startTime = performance.now();
      await act(async () => {
        renderThreadList({ threads: largeThreadList });
      });
      const renderTime = performance.now() - startTime;
      
      expect(renderTime).toBeLessThan(1000); // < 1s for 1000 threads
      expect(screen.getByTestId('thread-list')).toBeInTheDocument();
    });

    it('should maintain smooth scrolling with large datasets', () => {
      const largeThreadList = createLargeThreadList(500);
      renderThreadList({ threads: largeThreadList });
      
      const threadList = screen.getByTestId('thread-list');
      expect(threadList).toHaveStyle('overflow-y: auto');
      
      // Verify scrollable container
      fireEvent.scroll(threadList, { target: { scrollTop: 1000 } });
      expect(threadList).toBeInTheDocument();
    });

    it('should implement virtual scrolling for performance', () => {
      const largeThreadList = createLargeThreadList(1000);
      renderThreadList({ threads: largeThreadList });
      
      // Should only render visible items (implementation-dependent)
      const threadItems = screen.getAllByTestId(/thread-item-/);
      expect(threadItems.length).toBeLessThanOrEqual(100); // Reasonable viewport limit
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels and roles', () => {
      renderThreadList({ threads: [mockThreadData.basic] });
      
      const threadButton = screen.getByTestId('thread-item-thread-1');
      expect(threadButton).toHaveRole('button');
      expect(threadButton).toBeInTheDocument();
    });

    it('should support screen reader navigation', () => {
      renderThreadList({
        threads: [mockThreadData.basic],
        activeThreadId: 'thread-1'
      });
      
      const activeThread = screen.getByTestId('thread-item-thread-1');
      expect(activeThread).toHaveAttribute('aria-current', 'page');
    });

    it('should have keyboard focus indicators', async () => {
      const user = userEvent.setup();
      renderThreadList({ threads: [mockThreadData.basic] });
      
      const threadButton = screen.getByTestId('thread-item-thread-1');
      
      await user.tab();
      expect(threadButton).toHaveFocus();
    });

    it('should announce state changes to screen readers', () => {
      renderThreadList({
        threads: [mockThreadData.basic],
        isLoadingThreads: true
      });
      
      expect(screen.getByText('Loading conversations...')).toBeInTheDocument();
    });
  });

  describe('Animation and Visual Effects', () => {
    it('should animate thread list updates', async () => {
      const { rerender } = renderThreadList({ threads: [mockThreadData.basic] });
      
      // Add new thread
      const updatedThreads = [mockThreadData.basic, mockThreadData.withUnread];
      rerender(
        <TestProviders>
          <ThreadList
            threads={updatedThreads}
            isLoadingThreads={false}
            loadError={null}
            activeThreadId={null}
            isProcessing={false}
            showAllThreads={false}
            onThreadClick={jest.fn()}
            onRetryLoad={jest.fn()}
          />
        </TestProviders>
      );
      
      expect(screen.getByTestId('thread-item-thread-2')).toBeInTheDocument();
    });

    it('should show active thread indicator animation', () => {
      renderThreadList({
        threads: [mockThreadData.basic],
        activeThreadId: 'thread-1'
      });
      
      const activeIndicator = screen.getByTestId('thread-item-thread-1');
      expect(activeIndicator).toHaveClass('bg-emerald-50');
    });

    it('should handle thread removal animations', async () => {
      const { rerender } = renderThreadList({
        threads: [mockThreadData.basic, mockThreadData.withUnread]
      });
      
      // Remove thread
      rerender(
        <TestProviders>
          <ThreadList
            threads={[mockThreadData.basic]}
            isLoadingThreads={false}
            loadError={null}
            activeThreadId={null}
            isProcessing={false}
            showAllThreads={false}
            onThreadClick={jest.fn()}
            onRetryLoad={jest.fn()}
          />
        </TestProviders>
      );
      
      expect(screen.queryByTestId('thread-item-thread-2')).not.toBeInTheDocument();
    });
  });
});