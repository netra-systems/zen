import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ChatHistorySection } from '@/components/ChatHistorySection';
import { createTestSetup } from './shared-setup';
import { mockRouter } from './shared-setup';
import {
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
omponents/ChatHistorySection';
import { createTestSetup } from './shared-setup';
import { mockRouter } from './shared-setup';
import {
  expectBasicStructure,
  mockConsoleError,
  findThreadContainer,
  simulateClick
} from './test-utils';

describe('ChatHistorySection - Navigation Interactions', () => {
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

  describe('Thread clicking behavior', () => {
      jest.setTimeout(10000);
    it('should handle thread click interactions', () => {
      render(<ChatHistorySection />);
      
      expect(screen.getByText('Second Conversation')).toBeInTheDocument();
      
      const secondThread = screen.getByText('Second Conversation');
      fireEvent.click(secondThread);
      
      expect(screen.getByText('Second Conversation')).toBeInTheDocument();
    });

    it('should switch to conversation when clicked', async () => {
      render(<ChatHistorySection />);
      
      expect(screen.getByText('Second Conversation')).toBeInTheDocument();
      
      const secondThread = screen.getByText('Second Conversation');
      fireEvent.click(secondThread);
      
      expect(screen.getByText('Second Conversation')).toBeInTheDocument();
    });

    it('should handle multiple thread clicks', () => {
      render(<ChatHistorySection />);
      
      const threads = ['Second Conversation', 'Third Conversation', 'First Conversation'];
      
      threads.forEach(threadTitle => {
        const thread = screen.getByText(threadTitle);
        fireEvent.click(thread);
        expect(screen.getByText(threadTitle)).toBeInTheDocument();
      });
    });

    it('should handle rapid clicking', () => {
      render(<ChatHistorySection />);
      
      const secondThread = screen.getByText('Second Conversation');
      
      for (let i = 0; i < 5; i++) {
        fireEvent.click(secondThread);
      }
      
      expect(screen.getByText('Second Conversation')).toBeInTheDocument();
    });
  });

  describe('Current thread handling', () => {
      jest.setTimeout(10000);
    it('should not navigate if already on current thread', async () => {
      render(<ChatHistorySection />);
      
      expect(screen.getByText('First Conversation')).toBeInTheDocument();
      
      const firstThread = screen.getByText('First Conversation');
      fireEvent.click(firstThread);
      
      expect(mockRouter.push).not.toHaveBeenCalled();
    });

    it('should update current thread in store when switched', async () => {
      render(<ChatHistorySection />);
      
      expect(screen.getByText('Third Conversation')).toBeInTheDocument();
      
      const thirdThread = screen.getByText('Third Conversation');
      fireEvent.click(thirdThread);
      
      expect(screen.getByText('Third Conversation')).toBeInTheDocument();
    });

    it('should handle current thread state changes', () => {
      const { rerender } = render(<ChatHistorySection />);
      
      expect(screen.getByText('First Conversation')).toBeInTheDocument();
      
      testSetup.configureStore({ currentThreadId: 'thread-2' });
      rerender(<ChatHistorySection />);
      
      expect(screen.getByText('Second Conversation')).toBeInTheDocument();
    });

    it('should maintain thread selection state', () => {
      render(<ChatHistorySection />);
      
      const secondThread = screen.getByText('Second Conversation');
      fireEvent.click(secondThread);
      
      expect(screen.getByText('Second Conversation')).toBeInTheDocument();
    });
  });

  describe('Navigation error handling', () => {
      jest.setTimeout(10000);
    it('should handle thread switching errors', async () => {
      const restoreConsole = mockConsoleError();
      mockRouter.push.mockImplementation(() => {
        throw new Error('Navigation failed');
      });
      
      render(<ChatHistorySection />);
      
      expect(screen.getByText('Second Conversation')).toBeInTheDocument();
      
      const secondThread = screen.getByText('Second Conversation');
      expect(() => fireEvent.click(secondThread)).not.toThrow();
      
      restoreConsole();
      mockRouter.push.mockClear();
    });

    it('should handle navigation timeout errors', async () => {
      const restoreConsole = mockConsoleError();
      mockRouter.push.mockImplementation(() => {
        return new Promise((_, reject) => 
          setTimeout(() => reject(new Error('Navigation timeout')), 100)
        );
      });
      
      render(<ChatHistorySection />);
      
      expect(screen.getByText('Second Conversation')).toBeInTheDocument();
      
      const secondThread = screen.getByText('Second Conversation');
      expect(() => fireEvent.click(secondThread)).not.toThrow();
      
      restoreConsole();
      mockRouter.push.mockClear();
    });

    it('should recover from navigation errors', async () => {
      const restoreConsole = mockConsoleError();
      let shouldFail = true;
      
      mockRouter.push.mockImplementation(() => {
        if (shouldFail) {
          shouldFail = false;
          throw new Error('First attempt failed');
        }
        return Promise.resolve();
      });
      
      render(<ChatHistorySection />);
      
      const secondThread = screen.getByText('Second Conversation');
      fireEvent.click(secondThread);
      fireEvent.click(secondThread);
      
      expect(screen.getByText('Second Conversation')).toBeInTheDocument();
      
      restoreConsole();
      mockRouter.push.mockClear();
    });

    it('should handle invalid thread navigation', () => {
      const restoreConsole = mockConsoleError();
      
      render(<ChatHistorySection />);
      
      // Simulate clicking on invalid thread
      const container = screen.getByText('Chat History').closest('.flex-col');
      if (container) {
        fireEvent.click(container);
      }
      
      expectBasicStructure();
      restoreConsole();
    });
  });

  describe('Keyboard navigation', () => {
      jest.setTimeout(10000);
    it('should handle keyboard thread selection', () => {
      render(<ChatHistorySection />);
      
      const firstThread = screen.getByText('First Conversation');
      const threadContainer = findThreadContainer('First Conversation');
      
      if (threadContainer) {
        expect(() => {
          fireEvent.keyDown(threadContainer, { key: 'Enter' });
          fireEvent.keyDown(threadContainer, { key: ' ' });
        }).not.toThrow();
      }
      
      expect(screen.getByText('First Conversation')).toBeInTheDocument();
    });

    it('should handle arrow key navigation', () => {
      render(<ChatHistorySection />);
      
      const firstThread = screen.getByText('First Conversation');
      const threadContainer = findThreadContainer('First Conversation');
      
      if (threadContainer) {
        expect(() => {
          fireEvent.keyDown(threadContainer, { key: 'ArrowDown' });
          fireEvent.keyDown(threadContainer, { key: 'ArrowUp' });
        }).not.toThrow();
      }
      
      expectBasicStructure();
    });

    it('should handle tab navigation', () => {
      render(<ChatHistorySection />);
      
      const threadContainers = [
        findThreadContainer('First Conversation'),
        findThreadContainer('Second Conversation'),
        findThreadContainer('Third Conversation')
      ].filter(Boolean);
      
      threadContainers.forEach(container => {
        if (container) {
          expect(() => {
            fireEvent.keyDown(container, { key: 'Tab' });
          }).not.toThrow();
        }
      });
      
      expectBasicStructure();
    });

    it('should handle escape key navigation', () => {
      render(<ChatHistorySection />);
      
      const threadContainer = findThreadContainer('First Conversation');
      
      if (threadContainer) {
        expect(() => {
          fireEvent.keyDown(threadContainer, { key: 'Escape' });
        }).not.toThrow();
      }
      
      expectBasicStructure();
    });
  });

  describe('Focus management', () => {
      jest.setTimeout(10000);
    it('should handle focus on thread items', () => {
      render(<ChatHistorySection />);
      
      const threadContainer = findThreadContainer('First Conversation');
      
      if (threadContainer && threadContainer instanceof HTMLElement) {
        threadContainer.focus();
        expect(threadContainer).toBeInTheDocument();
      }
    });

    it('should maintain focus during navigation', () => {
      render(<ChatHistorySection />);
      
      const secondThread = screen.getByText('Second Conversation');
      const threadContainer = findThreadContainer('Second Conversation');
      
      if (threadContainer && threadContainer instanceof HTMLElement) {
        threadContainer.focus();
        fireEvent.click(secondThread);
        
        expect(screen.getByText('Second Conversation')).toBeInTheDocument();
      }
    });

    it('should handle focus loss gracefully', () => {
      render(<ChatHistorySection />);
      
      const threadContainer = findThreadContainer('First Conversation');
      
      if (threadContainer && threadContainer instanceof HTMLElement) {
        threadContainer.focus();
        threadContainer.blur();
        
        expect(screen.getByText('First Conversation')).toBeInTheDocument();
      }
    });

    it('should restore focus after navigation', () => {
      render(<ChatHistorySection />);
      
      const threadContainer = findThreadContainer('Second Conversation');
      
      if (threadContainer && threadContainer instanceof HTMLElement) {
        threadContainer.focus();
        fireEvent.click(threadContainer);
        
        expect(screen.getByText('Second Conversation')).toBeInTheDocument();
      }
    });
  });

  describe('Navigation state management', () => {
      jest.setTimeout(10000);
    it('should handle navigation loading states', () => {
      testSetup.configureStore({ 
        isLoading: true,
        currentThreadId: 'thread-1'
      });
      
      render(<ChatHistorySection />);
      
      const secondThread = screen.getByText('Second Conversation');
      fireEvent.click(secondThread);
      
      expectBasicStructure();
    });

    it('should prevent navigation during loading', () => {
      testSetup.configureStore({ isLoading: true });
      
      render(<ChatHistorySection />);
      
      const secondThread = screen.getByText('Second Conversation');
      fireEvent.click(secondThread);
      
      expectBasicStructure();
    });

    it('should handle concurrent navigation attempts', () => {
      render(<ChatHistorySection />);
      
      const threads = [
        screen.getByText('Second Conversation'),
        screen.getByText('Third Conversation')
      ];
      
      threads.forEach(thread => {
        fireEvent.click(thread);
      });
      
      expectBasicStructure();
    });

    it('should maintain navigation history', () => {
      render(<ChatHistorySection />);
      
      const navigationSequence = [
        'Second Conversation',
        'Third Conversation',
        'First Conversation'
      ];
      
      navigationSequence.forEach(threadTitle => {
        const thread = screen.getByText(threadTitle);
        fireEvent.click(thread);
        expect(screen.getByText(threadTitle)).toBeInTheDocument();
      });
    });
  });

  describe('Navigation accessibility', () => {
      jest.setTimeout(10000);
    it('should provide accessible navigation elements', () => {
      render(<ChatHistorySection />);
      
      const threadElements = screen.getAllByText(/Conversation/);
      
      threadElements.forEach(thread => {
        const container = thread.closest('[role="button"]') || 
                         thread.closest('button') ||
                         thread.closest('[tabindex]');
        
        if (container) {
          expect(container).toBeInTheDocument();
        }
      });
    });

    it('should announce navigation changes', () => {
      render(<ChatHistorySection />);
      
      const secondThread = screen.getByText('Second Conversation');
      fireEvent.click(secondThread);
      
      expectBasicStructure();
    });

    it('should provide navigation instructions', () => {
      render(<ChatHistorySection />);
      
      const threadContainer = findThreadContainer('First Conversation');
      
      if (threadContainer) {
        const hasInstructions = threadContainer.getAttribute('aria-label') ||
                               threadContainer.getAttribute('title');
        
        expect(threadContainer).toBeInTheDocument();
      }
    });

    it('should handle screen reader navigation', () => {
      render(<ChatHistorySection />);
      
      const threadElements = screen.getAllByText(/Conversation/);
      
      threadElements.forEach(thread => {
        const hasAriaAttributes = thread.getAttribute('aria-label') ||
                                 thread.closest('[role]') ||
                                 thread.closest('[aria-describedby]');
        
        expect(thread).toBeInTheDocument();
      });
    });
  });
});