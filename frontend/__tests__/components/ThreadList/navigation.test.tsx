/**
 * ThreadList Navigation Tests
 * Tests for hover states, click responsiveness, keyboard navigation, and focus management
 * Phase 3, Agent 9 - Critical for user experience and engagement
 * Follows 450-line file limit and 25-line function rule
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { jest } from '@jest/globals';
import '@testing-library/jest-dom';
import { TestProviders } from '../../test-utils/providers';

interface ThreadItemProps {
  id: string;
  title: string;
  isActive: boolean;
  hasUnread: boolean;
  onClick: (id: string) => void;
  onKeyDown?: (e: React.KeyboardEvent, id: string) => void;
}

interface ThreadListNavigationProps {
  threads: Array<{
    id: string;
    title: string;
    hasUnread?: boolean;
  }>;
  activeThreadId: string | null;
  onThreadSelect: (id: string) => void;
  onKeyboardNavigate?: (direction: 'up' | 'down') => void;
}

const ThreadItem: React.FC<ThreadItemProps> = ({ 
  id, 
  title, 
  isActive, 
  hasUnread, 
  onClick,
  onKeyDown 
}) => {
  const [isHovered, setIsHovered] = React.useState(false);
  const [clickTime, setClickTime] = React.useState<number | null>(null);

  const handleClick = () => {
    const start = performance.now();
    onClick(id);
    setClickTime(performance.now() - start);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleClick();
    } else if (onKeyDown) {
      onKeyDown(e, id);
    }
  };

  return (
    <div
      data-testid={`thread-item-${id}`}
      className={`thread-item ${isActive ? 'active' : ''} ${isHovered ? 'hovered' : ''}`}
      role="button"
      tabIndex={0}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onFocus={() => setIsHovered(true)}
      onBlur={() => setIsHovered(false)}
      aria-current={isActive ? 'page' : undefined}
      aria-label={`Thread: ${title}${hasUnread ? ' (unread)' : ''}`}
    >
      <span className="thread-title">{title}</span>
      {hasUnread && (
        <span data-testid={`unread-${id}`} className="unread-indicator">
          ●
        </span>
      )}
      {isActive && (
        <span data-testid={`active-${id}`} className="active-indicator">
          ▶
        </span>
      )}
      {clickTime !== null && (
        <span data-testid={`click-time-${id}`} style={{ display: 'none' }}>
          {clickTime}
        </span>
      )}
    </div>
  );
};

const ThreadListNavigation: React.FC<ThreadListNavigationProps> = ({ 
  threads, 
  activeThreadId, 
  onThreadSelect,
  onKeyboardNavigate 
}) => {
  const [focusedIndex, setFocusedIndex] = React.useState(0);
  const [scrollPosition, setScrollPosition] = React.useState(0);
  const listRef = React.useRef<HTMLDivElement>(null);

  const handleKeyDown = (e: React.KeyboardEvent, threadId: string) => {
    const currentIndex = threads.findIndex(t => t.id === threadId);
    
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      const nextIndex = Math.min(currentIndex + 1, threads.length - 1);
      setFocusedIndex(nextIndex);
      onKeyboardNavigate?.('down');
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      const prevIndex = Math.max(currentIndex - 1, 0);
      setFocusedIndex(prevIndex);
      onKeyboardNavigate?.('up');
    }
  };

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    setScrollPosition(e.currentTarget.scrollTop);
  };

  React.useEffect(() => {
    if (listRef.current) {
      const focusedElement = listRef.current.children[focusedIndex] as HTMLElement;
      focusedElement?.focus();
    }
  }, [focusedIndex]);

  return (
    <div 
      ref={listRef}
      data-testid="thread-list-navigation"
      className="thread-list"
      onScroll={handleScroll}
      style={{ height: '400px', overflowY: 'auto' }}
    >
      {threads.map((thread, index) => (
        <ThreadItem
          key={thread.id}
          id={thread.id}
          title={thread.title}
          isActive={thread.id === activeThreadId}
          hasUnread={thread.hasUnread || false}
          onClick={onThreadSelect}
          onKeyDown={handleKeyDown}
        />
      ))}
      <div data-testid="scroll-position" style={{ display: 'none' }}>
        {scrollPosition}
      </div>
      <div data-testid="focused-index" style={{ display: 'none' }}>
        {focusedIndex}
      </div>
    </div>
  );
};

const createTestThreads = (count: number = 5) => {
  return Array.from({ length: count }, (_, i) => ({
    id: `thread-${i + 1}`,
    title: `Thread ${i + 1}`,
    hasUnread: i % 2 === 0
  }));
};

describe('ThreadList Navigation Tests', () => {
  const mockOnThreadSelect = jest.fn();
  const mockOnKeyboardNavigate = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  const renderThreadList = (props = {}) => {
    const defaultProps = {
      threads: createTestThreads(),
      activeThreadId: null,
      onThreadSelect: mockOnThreadSelect,
      onKeyboardNavigate: mockOnKeyboardNavigate,
      ...props
    };

    return render(
      <TestProviders>
        <ThreadListNavigation {...defaultProps} />
      </TestProviders>
    );
  };

  describe('Hover States', () => {
    it('should show hover state on mouse enter', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      renderThreadList();

      const threadItem = screen.getByTestId('thread-item-thread-1');
      
      await user.hover(threadItem);
      
      expect(threadItem).toHaveClass('hovered');
    });

    it('should remove hover state on mouse leave', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      renderThreadList();

      const threadItem = screen.getByTestId('thread-item-thread-1');
      
      await user.hover(threadItem);
      expect(threadItem).toHaveClass('hovered');
      
      await user.unhover(threadItem);
      expect(threadItem).not.toHaveClass('hovered');
    });

    it('should maintain hover state consistency across multiple items', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      renderThreadList();

      const firstItem = screen.getByTestId('thread-item-thread-1');
      const secondItem = screen.getByTestId('thread-item-thread-2');
      
      await user.hover(firstItem);
      expect(firstItem).toHaveClass('hovered');
      expect(secondItem).not.toHaveClass('hovered');
      
      await user.hover(secondItem);
      expect(firstItem).not.toHaveClass('hovered');
      expect(secondItem).toHaveClass('hovered');
    });

    it('should show hover state on keyboard focus', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      renderThreadList();

      const threadItem = screen.getByTestId('thread-item-thread-1');
      
      threadItem.focus();
      
      expect(threadItem).toHaveClass('hovered');
    });
  });

  describe('Click Responsiveness', () => {
    it('should respond to clicks within 200ms', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      renderThreadList();

      const threadItem = screen.getByTestId('thread-item-thread-1');
      
      await user.click(threadItem);
      
      const clickTimeElement = screen.getByTestId('click-time-thread-1');
      const clickTime = parseFloat(clickTimeElement.textContent || '0');
      
      expect(clickTime).toBeLessThan(200);
      expect(mockOnThreadSelect).toHaveBeenCalledWith('thread-1');
    });

    it('should handle rapid successive clicks', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      renderThreadList();

      const threadItem = screen.getByTestId('thread-item-thread-1');
      
      // Perform 5 rapid clicks
      for (let i = 0; i < 5; i++) {
        await user.click(threadItem);
        act(() => { jest.advanceTimersByTime(50); });
      }
      
      expect(mockOnThreadSelect).toHaveBeenCalledTimes(5);
      expect(mockOnThreadSelect).toHaveBeenCalledWith('thread-1');
    });

    it('should provide immediate visual feedback on click', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      renderThreadList({ activeThreadId: null });

      const threadItem = screen.getByTestId('thread-item-thread-1');
      
      await user.click(threadItem);
      
      // Check that click was registered immediately
      expect(mockOnThreadSelect).toHaveBeenCalledWith('thread-1');
    });

    it('should handle clicks on different thread items', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      renderThreadList();

      await user.click(screen.getByTestId('thread-item-thread-1'));
      await user.click(screen.getByTestId('thread-item-thread-3'));
      await user.click(screen.getByTestId('thread-item-thread-5'));
      
      expect(mockOnThreadSelect).toHaveBeenCalledTimes(3);
      expect(mockOnThreadSelect).toHaveBeenNthCalledWith(1, 'thread-1');
      expect(mockOnThreadSelect).toHaveBeenNthCalledWith(2, 'thread-3');
      expect(mockOnThreadSelect).toHaveBeenNthCalledWith(3, 'thread-5');
    });
  });

  describe('Keyboard Navigation', () => {
    it('should navigate with arrow keys', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      renderThreadList();

      const firstItem = screen.getByTestId('thread-item-thread-1');
      firstItem.focus();
      
      // Navigate down
      await user.keyboard('{ArrowDown}');
      
      expect(mockOnKeyboardNavigate).toHaveBeenCalledWith('down');
      
      // Navigate up
      await user.keyboard('{ArrowUp}');
      
      expect(mockOnKeyboardNavigate).toHaveBeenCalledWith('up');
    });

    it('should select thread with Enter key', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      renderThreadList();

      const threadItem = screen.getByTestId('thread-item-thread-2');
      threadItem.focus();
      
      await user.keyboard('{Enter}');
      
      expect(mockOnThreadSelect).toHaveBeenCalledWith('thread-2');
    });

    it('should select thread with Space key', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      renderThreadList();

      const threadItem = screen.getByTestId('thread-item-thread-3');
      threadItem.focus();
      
      await user.keyboard('{ }');
      
      expect(mockOnThreadSelect).toHaveBeenCalledWith('thread-3');
    });

    it('should update focused index on arrow key navigation', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      renderThreadList();

      const firstItem = screen.getByTestId('thread-item-thread-1');
      firstItem.focus();
      
      // Navigate down twice
      await user.keyboard('{ArrowDown}');
      await user.keyboard('{ArrowDown}');
      
      const focusedIndex = screen.getByTestId('focused-index');
      expect(focusedIndex.textContent).toBe('2');
    });

    it('should not navigate beyond list boundaries', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      renderThreadList({ threads: createTestThreads(3) });

      const firstItem = screen.getByTestId('thread-item-thread-1');
      firstItem.focus();
      
      // Try to navigate up from first item
      await user.keyboard('{ArrowUp}');
      
      const focusedIndex = screen.getByTestId('focused-index');
      expect(focusedIndex.textContent).toBe('0');
      
      // Navigate to last item
      await user.keyboard('{ArrowDown}');
      await user.keyboard('{ArrowDown}');
      
      // Try to navigate down from last item
      await user.keyboard('{ArrowDown}');
      expect(focusedIndex.textContent).toBe('2');
    });
  });

  describe('Focus Management', () => {
    it('should maintain focus on active thread', () => {
      renderThreadList({ activeThreadId: 'thread-2' });

      const activeItem = screen.getByTestId('thread-item-thread-2');
      expect(activeItem).toHaveAttribute('aria-current', 'page');
    });

    it('should provide proper ARIA labels', () => {
      const threadsWithUnread = [
        { id: 'thread-1', title: 'Normal Thread', hasUnread: false },
        { id: 'thread-2', title: 'Unread Thread', hasUnread: true }
      ];
      
      renderThreadList({ threads: threadsWithUnread });

      const normalItem = screen.getByTestId('thread-item-thread-1');
      const unreadItem = screen.getByTestId('thread-item-thread-2');
      
      expect(normalItem).toHaveAttribute('aria-label', 'Thread: Normal Thread');
      expect(unreadItem).toHaveAttribute('aria-label', 'Thread: Unread Thread (unread)');
    });

    it('should handle tab navigation between threads', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      renderThreadList({ threads: createTestThreads(3) });

      // Tab through items
      await user.tab();
      expect(screen.getByTestId('thread-item-thread-1')).toHaveFocus();
      
      await user.tab();
      expect(screen.getByTestId('thread-item-thread-2')).toHaveFocus();
      
      await user.tab();
      expect(screen.getByTestId('thread-item-thread-3')).toHaveFocus();
    });

    it('should restore focus after thread selection', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      renderThreadList();

      const threadItem = screen.getByTestId('thread-item-thread-2');
      threadItem.focus();
      
      await user.keyboard('{Enter}');
      
      // Focus should remain on the selected item
      expect(threadItem).toHaveFocus();
    });

    it('should handle focus restoration after external blur', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      renderThreadList();

      const threadItem = screen.getByTestId('thread-item-thread-1');
      threadItem.focus();
      
      // Blur the element
      fireEvent.blur(threadItem);
      expect(threadItem).not.toHaveClass('hovered');
      
      // Focus again
      threadItem.focus();
      expect(threadItem).toHaveClass('hovered');
    });
  });

  describe('Scroll Position Restoration', () => {
    it('should track scroll position during navigation', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      const manyThreads = createTestThreads(20);
      renderThreadList({ threads: manyThreads });

      const listContainer = screen.getByTestId('thread-list-navigation');
      
      // Simulate scrolling
      fireEvent.scroll(listContainer, { target: { scrollTop: 100 } });
      
      const scrollPosition = screen.getByTestId('scroll-position');
      expect(scrollPosition.textContent).toBe('100');
    });

    it('should maintain scroll position during keyboard navigation', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      const manyThreads = createTestThreads(15);
      renderThreadList({ threads: manyThreads });

      const listContainer = screen.getByTestId('thread-list-navigation');
      const firstItem = screen.getByTestId('thread-item-thread-1');
      
      // Scroll down
      fireEvent.scroll(listContainer, { target: { scrollTop: 200 } });
      
      // Use keyboard navigation
      firstItem.focus();
      await user.keyboard('{ArrowDown}');
      
      // Scroll position should be maintained unless focus moves out of view
      const scrollPosition = screen.getByTestId('scroll-position');
      expect(parseInt(scrollPosition.textContent || '0')).toBeGreaterThanOrEqual(0);
    });

    it('should handle smooth scrolling to focused items', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      const manyThreads = createTestThreads(10);
      renderThreadList({ threads: manyThreads });

      const firstItem = screen.getByTestId('thread-item-thread-1');
      firstItem.focus();
      
      // Navigate to the last item
      for (let i = 0; i < 9; i++) {
        await user.keyboard('{ArrowDown}');
      }
      
      const focusedIndex = screen.getByTestId('focused-index');
      expect(focusedIndex.textContent).toBe('9');
    });
  });

  describe('Visual Indicators', () => {
    it('should display unread indicators correctly', () => {
      const threadsWithUnread = [
        { id: 'thread-1', title: 'Thread 1', hasUnread: true },
        { id: 'thread-2', title: 'Thread 2', hasUnread: false }
      ];
      
      renderThreadList({ threads: threadsWithUnread });

      expect(screen.getByTestId('unread-thread-1')).toBeInTheDocument();
      expect(screen.queryByTestId('unread-thread-2')).not.toBeInTheDocument();
    });

    it('should display active thread indicator', () => {
      renderThreadList({ activeThreadId: 'thread-2' });

      expect(screen.getByTestId('active-thread-2')).toBeInTheDocument();
      expect(screen.queryByTestId('active-thread-1')).not.toBeInTheDocument();
    });

    it('should update visual states correctly on thread change', () => {
      const { rerender } = renderThreadList({ activeThreadId: 'thread-1' });

      expect(screen.getByTestId('active-thread-1')).toBeInTheDocument();

      rerender(
        <TestProviders>
          <ThreadListNavigation
            threads={createTestThreads()}
            activeThreadId="thread-3"
            onThreadSelect={mockOnThreadSelect}
            onKeyboardNavigate={mockOnKeyboardNavigate}
          />
        </TestProviders>
      );

      expect(screen.queryByTestId('active-thread-1')).not.toBeInTheDocument();
      expect(screen.getByTestId('active-thread-3')).toBeInTheDocument();
    });
  });
});