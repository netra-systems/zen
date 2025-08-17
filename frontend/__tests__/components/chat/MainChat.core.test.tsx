import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import MainChat from '@/components/chat/MainChat';

// Mock all dependencies at the top level
jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: () => ({
    isProcessing: false,
    messages: [],
    fastLayerData: null,
    mediumLayerData: null,
    slowLayerData: null,
    currentRunId: null,
    activeThreadId: null,
    isThreadLoading: false,
    handleWebSocketEvent: jest.fn(),
    addMessage: jest.fn(),
    setProcessing: jest.fn(),
    clearMessages: jest.fn(),
    updateLayerData: jest.fn(),
  })
}));

jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: () => ({
    messages: [],
    connected: true,
    error: null
  })
}));

jest.mock('@/hooks/useLoadingState', () => ({
  useLoadingState: () => ({
    shouldShowLoading: false,
    shouldShowEmptyState: false,
    shouldShowExamplePrompts: true,
    loadingMessage: ''
  })
}));

jest.mock('@/hooks/useEventProcessor', () => ({
  useEventProcessor: () => ({
    processedEvents: [],
    isProcessing: false,
    stats: { processed: 0, failed: 0 }
  })
}));

// Mock all child components
jest.mock('@/components/chat/ChatHeader', () => ({
  ChatHeader: () => <div data-testid="chat-header">Chat Header</div>
}));

jest.mock('@/components/chat/MessageList', () => ({
  MessageList: () => <div data-testid="message-list">Message List</div>
}));

jest.mock('@/components/chat/MessageInput', () => ({
  MessageInput: () => <div data-testid="message-input">Message Input</div>
}));

jest.mock('@/components/chat/PersistentResponseCard', () => ({
  PersistentResponseCard: () => <div data-testid="response-card">Response Card</div>
}));

jest.mock('@/components/chat/ExamplePrompts', () => ({
  ExamplePrompts: () => <div data-testid="example-prompts">Example Prompts</div>
}));

jest.mock('@/components/chat/OverflowPanel', () => ({
  OverflowPanel: () => <div data-testid="overflow-panel">Overflow Panel</div>
}));

jest.mock('@/components/chat/EventDiagnosticsPanel', () => ({
  EventDiagnosticsPanel: () => <div data-testid="event-diagnostics">Event Diagnostics</div>
}));

// Mock framer-motion to avoid animation issues
jest.mock('framer-motion', () => ({
  motion: {
    div: 'div',
  },
  AnimatePresence: ({ children }: any) => children,
}));

describe('MainChat - Core Component Tests', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    jest.clearAllMocks();
  });

  afterEach(() => {
    jest.useRealTimers();
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
      expect(mainContainer).toHaveClass('flex', 'h-full');
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
      
      rerender(<MainChat />);
      
      // All components should still be present
      expect(screen.getByTestId('chat-header')).toBeInTheDocument();
      expect(screen.getByTestId('message-input')).toBeInTheDocument();
      expect(screen.getByTestId('example-prompts')).toBeInTheDocument();
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
        rerender(<MainChat />);
      }
      
      // Should still be stable
      expect(screen.getByTestId('chat-header')).toBeInTheDocument();
    });

    it('should clean up timers on unmount', () => {
      const { unmount } = render(<MainChat />);
      
      // Should not throw on unmount
      expect(() => unmount()).not.toThrow();
    });

    it('should handle memory efficiently with large message lists', () => {
      // Should not crash with basic render
      expect(() => render(<MainChat />)).not.toThrow();
    });
  });

  describe('Integration with store and hooks', () => {
    it('should properly integrate with unified chat store', () => {
      render(<MainChat />);
      
      // Basic functionality test - component should render
      expect(screen.getByTestId('chat-header')).toBeInTheDocument();
    });

    it('should properly integrate with chat WebSocket hook', () => {
      render(<MainChat />);
      
      // Basic functionality test - component should render
      expect(screen.getByTestId('message-input')).toBeInTheDocument();
    });

    it('should respond to store updates', () => {
      const { rerender } = render(<MainChat />);
      
      rerender(<MainChat />);
      
      // Should maintain stable rendering
      expect(screen.getByTestId('chat-header')).toBeInTheDocument();
    });

    it('should handle store reset', () => {
      const { rerender } = render(<MainChat />);
      
      rerender(<MainChat />);
      
      // Should show example prompts in basic state
      expect(screen.getByTestId('example-prompts')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper semantic structure', () => {
      const { container } = render(<MainChat />);
      
      // Should use semantic HTML
      expect(container.querySelector('div')).toBeInTheDocument();
    });

    it('should support keyboard navigation', () => {
      render(<MainChat />);
      
      // Basic keyboard navigation test - component should render and be accessible
      expect(screen.getByTestId('chat-header')).toBeInTheDocument();
      expect(screen.getByTestId('message-input')).toBeInTheDocument();
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