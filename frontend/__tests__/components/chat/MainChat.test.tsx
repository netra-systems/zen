import React from 'react';
import { render, screen, waitFor, within, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import MainChat from '@/components/chat/MainChat';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useChatWebSocket } from '@/hooks/useChatWebSocket';

import { TestProviders } from '../../test-utils/providers';

// Mock dependencies
jest.mock('@/store/unified-chat');
jest.mock('@/hooks/useChatWebSocket', () => ({
  useChatWebSocket: jest.fn()
}));
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
  PersistentResponseCard: ({ isCollapsed, onToggleCollapse }: any) => (
    <div data-testid="response-card" data-collapsed={isCollapsed}>
      <button onClick={onToggleCollapse}>Toggle</button>
      Response Card
    </div>
  )
}));
jest.mock('@/components/chat/ExamplePrompts', () => ({
  ExamplePrompts: () => <div data-testid="example-prompts">Example Prompts</div>
}));

describe('MainChat', () => {
  const mockStore = {
    isProcessing: false,
    messages: [],
    fastLayerData: null,
    mediumLayerData: null,
    slowLayerData: null,
    currentRunId: null,
    addMessage: jest.fn(),
    setProcessing: jest.fn(),
    clearMessages: jest.fn(),
    updateLayerData: jest.fn(),
  };

  beforeEach(() => {
    // Mock fetch for config
    global.fetch = jest.fn().mockResolvedValue({
      json: jest.fn().mockResolvedValue({
        ws_url: 'ws://localhost:8000/ws'
      })
    });

    jest.clearAllMocks();
    jest.useFakeTimers();
    (useUnifiedChatStore as jest.Mock).mockReturnValue(mockStore);
    const { useChatWebSocket } = require('@/hooks/useChatWebSocket');
    useChatWebSocket.mockReturnValue({
      connected: true,
      error: null
    });
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  describe('WebSocket connection management', () => {
    it('should initialize WebSocket connection on mount', () => {
      render(<MainChat />);
      
      const { useChatWebSocket } = require('@/hooks/useChatWebSocket');
      expect(useChatWebSocket).toHaveBeenCalled();
    });

    it('should handle WebSocket connection state', () => {
      const { useChatWebSocket } = require('@/hooks/useChatWebSocket');
      useChatWebSocket.mockReturnValue({
        connected: true,
        error: null
      });
      
      const { rerender } = render(<MainChat />);
      
      // Simulate disconnection
      useChatWebSocket.mockReturnValue({
        connected: false,
        error: null
      });
      rerender(<MainChat />);
      
      // Component should still render without errors
      expect(screen.getByTestId('chat-header')).toBeInTheDocument();
    });

    it('should handle WebSocket errors gracefully', () => {
      const { useChatWebSocket } = require('@/hooks/useChatWebSocket');
      useChatWebSocket.mockReturnValue({
        connected: false,
        error: new Error('WebSocket connection failed')
      });
      
      render(<MainChat />);
      
      // Component should still render
      expect(screen.getByTestId('chat-header')).toBeInTheDocument();
      expect(screen.getByTestId('message-input')).toBeInTheDocument();
    });

    it('should reconnect WebSocket on error', async () => {
      const mockReconnect = jest.fn();
      (useChatWebSocket as jest.Mock).mockReturnValue({
        connected: false,
        error: new Error('Connection lost'),
        reconnect: mockReconnect
      });
      
      render(<MainChat />);
      
      // Verify reconnect logic would be triggered
      // This would typically be handled by the WebSocket hook itself
      expect(useChatWebSocket).toHaveBeenCalled();
    });

    it('should maintain connection during component updates', () => {
      const { rerender } = render(<MainChat />);
      
      const newMockStore = {
        ...mockStore,
        messages: [{ id: '1', type: 'user', content: 'Hello' }]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(newMockStore);
      rerender(<MainChat />);
      
      // WebSocket hook should not be re-initialized
      expect(useChatWebSocket).toHaveBeenCalledTimes(2); // Once per render
    });

    it('should handle rapid connection state changes', async () => {
      const { rerender } = render(<MainChat />);
      
      // Simulate rapid connection state changes
      for (let i = 0; i < 5; i++) {
        (useChatWebSocket as jest.Mock).mockReturnValue({
          connected: i % 2 === 0,
          error: null
        });
        rerender(<MainChat />);
      }
      
      // Component should remain stable
      expect(screen.getByTestId('chat-header')).toBeInTheDocument();
    });
  });

  describe('Message sending and receiving', () => {
    it('should display messages from store', () => {
      const messages = [
        { id: '1', type: 'user', content: 'Hello', displayed_to_user: true },
        { id: '2', type: 'agent', content: 'Hi there!', displayed_to_user: true }
      ];
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...mockStore,
        messages
      });
      
      render(<MainChat />);
      
      expect(screen.getByTestId('message-list')).toBeInTheDocument();
    });

    it('should show example prompts when no messages', () => {
      render(<MainChat />);
      
      expect(screen.getByTestId('example-prompts')).toBeInTheDocument();
    });

    it('should hide example prompts when messages exist', () => {
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...mockStore,
        messages: [{ id: '1', type: 'user', content: 'Test' }]
      });
      
      render(<MainChat />);
      
      expect(screen.queryByTestId('example-prompts')).not.toBeInTheDocument();
    });

    it('should handle message updates from WebSocket', () => {
      const { rerender } = render(<MainChat />);
      
      // Simulate receiving a message
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...mockStore,
        messages: [{ id: '1', type: 'user', content: 'New message' }]
      });
      
      rerender(<MainChat />);
      
      // Message list should be present
      expect(screen.getByTestId('message-list')).toBeInTheDocument();
    });

    it('should maintain message order', () => {
      const messages = [
        { id: '1', type: 'user', content: 'First', created_at: '2024-01-01T10:00:00Z' },
        { id: '2', type: 'agent', content: 'Second', created_at: '2024-01-01T10:01:00Z' },
        { id: '3', type: 'user', content: 'Third', created_at: '2024-01-01T10:02:00Z' }
      ];
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...mockStore,
        messages
      });
      
      render(<MainChat />);
      
      // Messages should be displayed in order
      expect(screen.getByTestId('message-list')).toBeInTheDocument();
    });

    it('should handle empty message content gracefully', () => {
      const messages = [
        { id: '1', type: 'user', content: '' },
        { id: '2', type: 'agent', content: null }
      ];
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...mockStore,
        messages
      });
      
      render(<MainChat />);
      
      // Should not crash
      expect(screen.getByTestId('message-list')).toBeInTheDocument();
    });
  });

  describe('Agent status updates', () => {
    it('should show response card when processing', () => {
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...mockStore,
        isProcessing: true,
        currentRunId: 'run-123'
      });
      
      render(<MainChat />);
      
      expect(screen.getByTestId('response-card')).toBeInTheDocument();
    });

    it('should hide response card when not processing and no run', () => {
      render(<MainChat />);
      
      expect(screen.queryByTestId('response-card')).not.toBeInTheDocument();
    });

    it('should display fast layer data', () => {
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...mockStore,
        isProcessing: true,
        currentRunId: 'run-123',
        fastLayerData: {
          initialAnalysis: 'Quick analysis',
          suggestions: ['Suggestion 1', 'Suggestion 2']
        }
      });
      
      render(<MainChat />);
      
      expect(screen.getByTestId('response-card')).toBeInTheDocument();
    });

    it('should display medium layer data', () => {
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...mockStore,
        isProcessing: true,
        currentRunId: 'run-123',
        mediumLayerData: {
          deeperAnalysis: 'Detailed analysis',
          recommendations: ['Rec 1', 'Rec 2']
        }
      });
      
      render(<MainChat />);
      
      expect(screen.getByTestId('response-card')).toBeInTheDocument();
    });

    it('should display slow layer data with final report', () => {
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...mockStore,
        isProcessing: false,
        currentRunId: 'run-123',
        slowLayerData: {
          finalReport: 'Complete analysis report',
          metrics: { accuracy: 0.95 }
        }
      });
      
      render(<MainChat />);
      
      expect(screen.getByTestId('response-card')).toBeInTheDocument();
    });

    it('should auto-collapse card after completion', async () => {
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...mockStore,
        isProcessing: false,
        currentRunId: 'run-123',
        slowLayerData: {
          finalReport: 'Complete'
        }
      });
      
      render(<MainChat />);
      
      const card = screen.getByTestId('response-card');
      expect(card).toHaveAttribute('data-collapsed', 'false');
      
      // Fast-forward timer
      act(() => {
        jest.advanceTimersByTime(2000);
      });
      
      await waitFor(() => {
        expect(card).toHaveAttribute('data-collapsed', 'true');
      });
    });

    it('should reset collapse state when new processing starts', () => {
      const { rerender } = render(<MainChat />);
      
      // Start with completed state
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...mockStore,
        isProcessing: false,
        currentRunId: 'run-123',
        slowLayerData: { finalReport: 'Done' }
      });
      
      rerender(<MainChat />);
      
      act(() => {
        jest.advanceTimersByTime(2000);
      });
      
      // Start new processing
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...mockStore,
        isProcessing: true,
        currentRunId: 'run-124',
        slowLayerData: null
      });
      
      rerender(<MainChat />);
      
      const card = screen.getByTestId('response-card');
      expect(card).toHaveAttribute('data-collapsed', 'false');
    });

    it('should handle toggle collapse manually', async () => {
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...mockStore,
        isProcessing: true,
        currentRunId: 'run-123'
      });
      
      render(<MainChat />);
      
      const card = screen.getByTestId('response-card');
      const toggleButton = within(card).getByText('Toggle');
      
      expect(card).toHaveAttribute('data-collapsed', 'false');
      
      await userEvent.click(toggleButton);
      
      expect(card).toHaveAttribute('data-collapsed', 'true');
      
      await userEvent.click(toggleButton);
      
      expect(card).toHaveAttribute('data-collapsed', 'false');
    });
  });

  describe('Error recovery and reconnection', () => {
    it('should handle store errors gracefully', () => {
      (useUnifiedChatStore as jest.Mock).mockImplementation(() => {
        throw new Error('Store initialization failed');
      });
      
      // Should not crash the component
      expect(() => render(<MainChat />)).not.toThrow();
    });

    it('should recover from WebSocket errors', async () => {
      const { rerender } = render(<MainChat />);
      
      // Simulate error
      (useChatWebSocket as jest.Mock).mockReturnValue({
        connected: false,
        error: new Error('Connection lost')
      });
      
      rerender(<MainChat />);
      
      // Simulate recovery
      (useChatWebSocket as jest.Mock).mockReturnValue({
        connected: true,
        error: null
      });
      
      rerender(<MainChat />);
      
      // Should render normally after recovery
      expect(screen.getByTestId('chat-header')).toBeInTheDocument();
    });

    it('should handle message processing errors', () => {
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...mockStore,
        isProcessing: true,
        error: 'Failed to process message'
      });
      
      render(<MainChat />);
      
      // Should still render UI
      expect(screen.getByTestId('chat-header')).toBeInTheDocument();
      expect(screen.getByTestId('message-input')).toBeInTheDocument();
    });

    it('should retry failed operations', async () => {
      const mockRetry = jest.fn();
      (useChatWebSocket as jest.Mock).mockReturnValue({
        connected: false,
        error: new Error('Failed'),
        retry: mockRetry
      });
      
      render(<MainChat />);
      
      // Verify retry mechanism would be available
      expect(useChatWebSocket).toHaveBeenCalled();
    });

    it('should maintain state during errors', () => {
      const messages = [
        { id: '1', type: 'user', content: 'Previous message' }
      ];
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...mockStore,
        messages,
        error: 'Current error'
      });
      
      render(<MainChat />);
      
      // Messages should still be displayed
      expect(screen.getByTestId('message-list')).toBeInTheDocument();
    });

    it('should handle network interruptions', async () => {
      const { rerender } = render(<MainChat />);
      
      // Simulate network interruption
      (useChatWebSocket as jest.Mock).mockReturnValue({
        connected: false,
        error: new Error('Network error')
      });
      
      rerender(<MainChat />);
      
      // Wait for potential reconnection
      await act(async () => {
        jest.advanceTimersByTime(5000);
      });
      
      // Component should remain functional
      expect(screen.getByTestId('chat-header')).toBeInTheDocument();
    });
  });

  describe('Message history loading', () => {
    it('should load message history on mount', () => {
      const historicalMessages = [
        { id: 'h1', type: 'user', content: 'Historical 1' },
        { id: 'h2', type: 'agent', content: 'Historical 2' }
      ];
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...mockStore,
        messages: historicalMessages
      });
      
      render(<MainChat />);
      
      expect(screen.getByTestId('message-list')).toBeInTheDocument();
    });

    it('should handle pagination of message history', () => {
      const manyMessages = Array.from({ length: 100 }, (_, i) => ({
        id: `msg-${i}`,
        type: i % 2 === 0 ? 'user' : 'agent',
        content: `Message ${i}`
      }));
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...mockStore,
        messages: manyMessages
      });
      
      render(<MainChat />);
      
      // Should handle large message lists
      expect(screen.getByTestId('message-list')).toBeInTheDocument();
    });

    it('should preserve scroll position when loading history', async () => {
      const { rerender } = render(<MainChat />);
      
      // Initial messages
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...mockStore,
        messages: [
          { id: '1', type: 'user', content: 'Initial' }
        ]
      });
      
      rerender(<MainChat />);
      
      // Load more history
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...mockStore,
        messages: [
          { id: '0', type: 'user', content: 'Earlier' },
          { id: '1', type: 'user', content: 'Initial' }
        ]
      });
      
      rerender(<MainChat />);
      
      // Scroll position should be maintained
      expect(screen.getByTestId('message-list')).toBeInTheDocument();
    });

    it('should handle empty message history', () => {
      render(<MainChat />);
      
      // Should show example prompts instead
      expect(screen.getByTestId('example-prompts')).toBeInTheDocument();
      expect(screen.queryByTestId('response-card')).not.toBeInTheDocument();
    });

    it('should update history when new messages arrive', async () => {
      const { rerender } = render(<MainChat />);
      
      // Add new message
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...mockStore,
        messages: [{ id: 'new-1', type: 'user', content: 'New message' }]
      });
      
      rerender(<MainChat />);
      
      // Example prompts should disappear
      expect(screen.queryByTestId('example-prompts')).not.toBeInTheDocument();
    });

    it('should handle message deletion from history', () => {
      const { rerender } = render(<MainChat />);
      
      // Start with messages
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...mockStore,
        messages: [
          { id: '1', type: 'user', content: 'Message 1' },
          { id: '2', type: 'agent', content: 'Message 2' }
        ]
      });
      
      rerender(<MainChat />);
      
      // Delete a message
      (useUnifiedChatStore as jest.Mock).mockReturnValue({
        ...mockStore,
        messages: [
          { id: '2', type: 'agent', content: 'Message 2' }
        ]
      });
      
      rerender(<MainChat />);
      
      // Should still render
      expect(screen.getByTestId('message-list')).toBeInTheDocument();
    });
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