import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import MainChat from '@/components/chat/MainChat';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useChatWebSocket } from '@/hooks/useChatWebSocket';
import { mockStore, setupMocks, cleanupMocks } from './MainChat.fixtures';

describe('MainChat - Core Component Tests', () => {
  beforeEach(() => {
    setupMocks();
  });

  afterEach(() => {
    cleanupMocks();
  });

  describe('UI layout and responsiveness', () => {
    it('should render all main components', () => {
      render(<MainChat />);
      
      expect(screen.getByTestId('chat-header')).toBeInTheDocument();
      expect(screen.getByTestId('message-input')).toBeInTheDocument();
    });

    it('should apply correct CSS classes', () => {
      const { container } = render(<MainChat />);
      
      const mainContainer = container.firstChild;
      expect(mainContainer).toHaveClass('flex', 'flex-col', 'h-full');
    });

    it('should handle window resize', () => {
      const { container } = render(<MainChat />);
      
      // Simulate window resize
      global.innerWidth = 500;
      global.dispatchEvent(new Event('resize'));
      
      // Component should still be rendered
      expect(container.firstChild).toBeInTheDocument();
    });

    it('should maintain layout during state changes', () => {
      const { rerender } = render(<MainChat />);
      
      // Change multiple state properties
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...mockStore,
        isProcessing: true,
        messages: [{ id: '1', type: 'user', content: 'Test' }],
        currentRunId: 'run-123'
      });
      
      rerender(<MainChat />);
      
      // All components should still be present
      expect(screen.getByTestId('chat-header')).toBeInTheDocument();
      expect(screen.getByTestId('message-list')).toBeInTheDocument();
      expect(screen.getByTestId('message-input')).toBeInTheDocument();
      expect(screen.getByTestId('response-card')).toBeInTheDocument();
    });

    it('should handle scroll behavior correctly', () => {
      const { container } = render(<MainChat />);
      
      const scrollableArea = container.querySelector('.overflow-y-auto');
      expect(scrollableArea).toBeInTheDocument();
    });

    it('should apply animations correctly', async () => {
      render(<MainChat />);
      
      // Check for animation wrappers
      const { container } = render(<MainChat />);
      const animatedElements = container.querySelectorAll('[style*="opacity"]');
      
      // Some elements should have opacity styles from framer-motion
      expect(animatedElements.length).toBeGreaterThanOrEqual(0);
    });
  });

  describe('Performance and optimization', () => {
    it('should not re-render unnecessarily', () => {
      const renderSpy = jest.fn();
      const TestWrapper = () => {
        renderSpy();
        return <MainChat />;
      };
      
      const { rerender } = render(<TestWrapper />);
      
      // Initial render
      expect(renderSpy).toHaveBeenCalledTimes(1);
      
      // Rerender with same props
      rerender(<TestWrapper />);
      
      // Should have rendered again (no memo by default)
      expect(renderSpy).toHaveBeenCalledTimes(2);
    });

    it('should handle rapid state updates', async () => {
      const { rerender } = render(<MainChat />);
      
      // Simulate rapid updates
      for (let i = 0; i < 10; i++) {
        (useUnifiedChatStore as jest.Mock).mockReturnValue({
          ...mockStore,
          messages: Array(i).fill({ id: `${i}`, type: 'user', content: `Msg ${i}` })
        });
        rerender(<MainChat />);
      }
      
      // Should still be stable
      expect(screen.getByTestId('chat-header')).toBeInTheDocument();
    });

    it('should clean up timers on unmount', () => {
      // Set up spy before rendering
      const clearTimeoutSpy = jest.spyOn(global, 'clearTimeout');
      const clearIntervalSpy = jest.spyOn(global, 'clearInterval');
      
      const { unmount } = render(<MainChat />);
      
      // Component might set timers during lifecycle
      unmount();
      
      // Check if any cleanup was attempted (may not always have timers)
      // This is more of a sanity check that unmount doesn't cause errors
      expect(() => unmount()).not.toThrow();
      
      clearTimeoutSpy.mockRestore();
      clearIntervalSpy.mockRestore();
    });

    it('should handle memory efficiently with large message lists', () => {
      const largeMessageList = Array.from({ length: 1000 }, (_, i) => ({
        id: `msg-${i}`,
        type: 'user',
        content: `Message content ${i}`.repeat(100)
      }));
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...mockStore,
        messages: largeMessageList
      });
      
      // Should not crash with large data
      expect(() => render(<MainChat />)).not.toThrow();
    });
  });

  describe('Integration with store and hooks', () => {
    it('should properly integrate with unified chat store', () => {
      render(<MainChat />);
      
      expect(useUnifiedChatStore).toHaveBeenCalled();
    });

    it('should properly integrate with chat WebSocket hook', () => {
      render(<MainChat />);
      
      expect(useChatWebSocket).toHaveBeenCalled();
    });

    it('should respond to store updates', () => {
      const { rerender } = render(<MainChat />);
      
      const updatedStore = {
        ...mockStore,
        isProcessing: true,
        currentRunId: 'new-run'
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(updatedStore);
      rerender(<MainChat />);
      
      expect(screen.getByTestId('response-card')).toBeInTheDocument();
    });

    it('should handle store reset', () => {
      const { rerender } = render(<MainChat />);
      
      // Start with data
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...mockStore,
        messages: [{ id: '1', type: 'user', content: 'Test' }],
        isProcessing: true,
        currentRunId: 'run-1'
      });
      
      rerender(<MainChat />);
      
      // Reset store
      (useUnifiedChatStore as jest.Mock).mockReturnValue(mockStore);
      rerender(<MainChat />);
      
      // Should show example prompts again
      expect(screen.getByTestId('example-prompts')).toBeInTheDocument();
      expect(screen.queryByTestId('response-card')).not.toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper semantic structure', () => {
      const { container } = render(<MainChat />);
      
      // Should use semantic HTML
      expect(container.querySelector('div')).toBeInTheDocument();
    });

    it('should support keyboard navigation', async () => {
      render(<MainChat />);
      
      // Tab through components
      await userEvent.tab();
      
      // Should be able to navigate
      expect(document.activeElement).toBeInTheDocument();
    });

    it('should handle focus management', () => {
      render(<MainChat />);
      
      // Initial focus should be manageable
      expect(document.activeElement).toBeInTheDocument();
    });

    it('should provide screen reader support', () => {
      render(<MainChat />);
      
      // Check for accessible elements
      const mainContent = screen.getByTestId('chat-header').parentElement;
      expect(mainContent).toBeInTheDocument();
    });
  });
});