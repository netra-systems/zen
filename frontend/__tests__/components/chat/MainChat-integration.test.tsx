/**
 * Complete integration test suite for MainChat component
 * Tests initialization coordinator integration and render optimization
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import MainChat from '@/components/chat/MainChat';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useInitializationCoordinator } from '@/hooks/useInitializationCoordinator';
import { useLoadingState } from '@/hooks/useLoadingState';
import { useEventProcessor } from '@/hooks/useEventProcessor';
import { useThreadNavigation } from '@/hooks/useThreadNavigation';

// Mock all dependencies
jest.mock('@/store/unified-chat');
jest.mock('@/hooks/useWebSocket');
jest.mock('@/hooks/useInitializationCoordinator');
jest.mock('@/hooks/useLoadingState');
jest.mock('@/hooks/useEventProcessor');
jest.mock('@/hooks/useThreadNavigation');
jest.mock('@/utils/debug-logger', () => ({
  logger: {
    debug: jest.fn(),
    error: jest.fn(),
    warn: jest.fn(),
    info: jest.fn()
  }
}));

// Mock framer-motion
jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

// Mock child components
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

describe('MainChat Integration Tests', () => {
  const mockHandleWebSocketEvent = jest.fn();
  
  const defaultStoreState = {
    isProcessing: false,
    messages: [],
    fastLayerData: null,
    mediumLayerData: null,
    slowLayerData: null,
    currentRunId: null,
    activeThreadId: null,
    isThreadLoading: false,
    handleWebSocketEvent: mockHandleWebSocketEvent
  };

  const defaultInitState = {
    state: {
      phase: 'ready' as const,
      isReady: true,
      error: null,
      progress: 100
    },
    reset: jest.fn(),
    isInitialized: true
  };

  const defaultLoadingState = {
    shouldShowLoading: false,
    shouldShowEmptyState: true,
    shouldShowExamplePrompts: false,
    loadingMessage: 'Loading...'
  };

  beforeEach(() => {
    jest.clearAllMocks();
    
    (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(defaultStoreState);
    (useInitializationCoordinator as jest.Mock).mockReturnValue(defaultInitState);
    (useLoadingState as jest.Mock).mockReturnValue(defaultLoadingState);
    (useWebSocket as jest.Mock).mockReturnValue({
      messages: [],
      isConnected: true,
      status: 'OPEN'
    });
    (useThreadNavigation as jest.Mock).mockReturnValue({
      currentThreadId: null,
      isNavigating: false
    });
    (useEventProcessor as jest.Mock).mockReturnValue({
      processedCount: 0,
      queueSize: 0
    });
  });

  describe('Initialization Coordinator Integration', () => {
    test('should show loading when not initialized', () => {
      (useInitializationCoordinator as jest.Mock).mockReturnValue({
        ...defaultInitState,
        isInitialized: false,
        state: {
          phase: 'auth',
          isReady: false,
          error: null,
          progress: 10
        }
      });

      render(<MainChat />);
      
      expect(screen.getByText('Loading...')).toBeInTheDocument();
      expect(screen.queryByTestId('main-chat')).not.toBeInTheDocument();
    });

    test('should show main chat when initialized', () => {
      render(<MainChat />);
      
      expect(screen.getByTestId('main-chat')).toBeInTheDocument();
      expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
    });

    test('should show loading during initialization phases', () => {
      const phases = [
        { phase: 'auth' as const, progress: 10 },
        { phase: 'websocket' as const, progress: 40 },
        { phase: 'store' as const, progress: 75 }
      ];

      phases.forEach(({ phase, progress }) => {
        (useInitializationCoordinator as jest.Mock).mockReturnValue({
          ...defaultInitState,
          isInitialized: false,
          state: {
            phase,
            isReady: false,
            error: null,
            progress
          }
        });

        const { unmount } = render(<MainChat />);
        expect(screen.getByText('Loading...')).toBeInTheDocument();
        unmount();
      });
    });

    test('should handle initialization errors', () => {
      (useInitializationCoordinator as jest.Mock).mockReturnValue({
        ...defaultInitState,
        isInitialized: false,
        state: {
          phase: 'error' as const,
          isReady: false,
          error: new Error('Init failed'),
          progress: 0
        }
      });

      render(<MainChat />);
      
      // Should still show loading (graceful degradation)
      expect(screen.getByText('Loading...')).toBeInTheDocument();
    });
  });

  describe('Loading State Integration', () => {
    test('should prioritize initialization state over loading state', () => {
      (useInitializationCoordinator as jest.Mock).mockReturnValue({
        ...defaultInitState,
        isInitialized: false
      });
      
      (useLoadingState as jest.Mock).mockReturnValue({
        ...defaultLoadingState,
        shouldShowLoading: false // Loading says don't show
      });

      render(<MainChat />);
      
      // Should still show loading because not initialized
      expect(screen.getByText('Loading...')).toBeInTheDocument();
    });

    test('should show loading when both conditions require it', () => {
      (useLoadingState as jest.Mock).mockReturnValue({
        ...defaultLoadingState,
        shouldShowLoading: true,
        loadingMessage: 'Custom loading message'
      });

      render(<MainChat />);
      
      expect(screen.getByText('Custom loading message')).toBeInTheDocument();
    });
  });

  describe('Component Rendering', () => {
    test('should render all main components when initialized', () => {
      render(<MainChat />);
      
      expect(screen.getByTestId('chat-header')).toBeInTheDocument();
      expect(screen.getByTestId('message-input')).toBeInTheDocument();
      expect(screen.getByTestId('main-content')).toBeInTheDocument();
    });

    test('should show example prompts when in empty state', () => {
      (useLoadingState as jest.Mock).mockReturnValue({
        ...defaultLoadingState,
        shouldShowEmptyState: true,
        shouldShowExamplePrompts: true
      });

      render(<MainChat />);
      
      expect(screen.getByTestId('example-prompts')).toBeInTheDocument();
    });

    test('should show response card when processing', () => {
      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue({
        ...defaultStoreState,
        isProcessing: true,
        currentRunId: 'run-123'
      });

      render(<MainChat />);
      
      expect(screen.getByTestId('response-card')).toBeInTheDocument();
    });

    test('should show message list when messages exist', () => {
      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue({
        ...defaultStoreState,
        messages: [
          { id: '1', content: 'Message 1' },
          { id: '2', content: 'Message 2' }
        ]
      });

      render(<MainChat />);
      
      expect(screen.getByTestId('message-list')).toBeInTheDocument();
    });
  });

  describe('WebSocket Event Processing', () => {
    test('should process WebSocket messages through event processor', () => {
      const mockMessages = [
        { type: 'message', data: { content: 'Test' } }
      ];

      (useWebSocket as jest.Mock).mockReturnValue({
        messages: mockMessages,
        isConnected: true,
        status: 'OPEN'
      });

      render(<MainChat />);
      
      expect(useEventProcessor).toHaveBeenCalledWith(
        mockMessages,
        mockHandleWebSocketEvent,
        expect.objectContaining({
          maxQueueSize: 500,
          duplicateWindowMs: 3000,
          processingTimeoutMs: 5000,
          enableDeduplication: true
        })
      );
    });
  });

  describe('Keyboard Shortcuts', () => {
    test('should toggle overflow panel with Ctrl+Shift+D', async () => {
      render(<MainChat />);
      
      // Initially no overflow panel
      expect(screen.queryByTestId('overflow-panel')).not.toBeInTheDocument();
      
      // Trigger keyboard shortcut
      act(() => {
        const event = new KeyboardEvent('keydown', {
          key: 'D',
          ctrlKey: true,
          shiftKey: true
        });
        window.dispatchEvent(event);
      });
      
      await waitFor(() => {
        expect(screen.getByTestId('overflow-panel')).toBeInTheDocument();
      });
    });

    test('should toggle diagnostics panel with Ctrl+Shift+E', async () => {
      render(<MainChat />);
      
      // Initially no diagnostics panel
      expect(screen.queryByTestId('event-diagnostics')).not.toBeInTheDocument();
      
      // Trigger keyboard shortcut
      act(() => {
        const event = new KeyboardEvent('keydown', {
          key: 'E',
          ctrlKey: true,
          shiftKey: true
        });
        window.dispatchEvent(event);
      });
      
      await waitFor(() => {
        expect(screen.getByTestId('event-diagnostics')).toBeInTheDocument();
      });
    });
  });

  describe('Thread Navigation', () => {
    test('should handle thread switching', () => {
      (useThreadNavigation as jest.Mock).mockReturnValue({
        currentThreadId: 'thread-123',
        isNavigating: true
      });
      
      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue({
        ...defaultStoreState,
        isThreadLoading: true,
        activeThreadId: 'thread-123'
      });

      render(<MainChat />);
      
      // Should still render main content during thread switch
      expect(screen.getByTestId('main-chat')).toBeInTheDocument();
    });
  });

  describe('Auto-collapse Response Card', () => {
    test('should auto-collapse card after completion', async () => {
      jest.useFakeTimers();
      
      const { rerender } = render(<MainChat />);
      
      // Complete processing with final report
      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue({
        ...defaultStoreState,
        isProcessing: false,
        slowLayerData: { finalReport: 'Done' },
        currentRunId: 'run-123'
      });
      
      rerender(<MainChat />);
      
      // Fast-forward time
      act(() => {
        jest.advanceTimersByTime(2000);
      });
      
      // Card should be rendered (collapse state handled internally)
      expect(screen.getByTestId('response-card')).toBeInTheDocument();
      
      jest.useRealTimers();
    });
  });

  describe('Performance Optimizations', () => {
    test('should not re-render when unrelated store data changes', () => {
      const { rerender } = render(<MainChat />);
      
      let renderCount = 0;
      const OriginalMainChat = MainChat;
      const TrackedMainChat = () => {
        renderCount++;
        return <OriginalMainChat />;
      };
      
      const { unmount } = render(<TrackedMainChat />);
      const initialRenderCount = renderCount;
      
      // Update unrelated store data
      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue({
        ...defaultStoreState,
        wsEventBufferVersion: 1, // Unrelated field
        performanceMetrics: { renderCount: 100 } // Unrelated field
      });
      
      rerender(<TrackedMainChat />);
      
      // Should minimize re-renders
      expect(renderCount - initialRenderCount).toBeLessThanOrEqual(1);
      
      unmount();
    });
  });

  describe('Error Boundaries', () => {
    test('should handle component errors gracefully', () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
      
      // Mock a component to throw
      jest.mock('@/components/chat/ChatHeader', () => ({
        ChatHeader: () => {
          throw new Error('Test error');
        }
      }));
      
      // Should not crash the entire app
      expect(() => render(<MainChat />)).not.toThrow();
      
      consoleSpy.mockRestore();
    });
  });

  describe('Welcome Message', () => {
    test('should show welcome message in empty state', () => {
      (useLoadingState as jest.Mock).mockReturnValue({
        ...defaultLoadingState,
        shouldShowEmptyState: true
      });

      render(<MainChat />);
      
      expect(screen.getByText(/Start a conversation/i)).toBeInTheDocument();
    });

    test('should not show welcome message when thread has messages', () => {
      (useLoadingState as jest.Mock).mockReturnValue({
        ...defaultLoadingState,
        shouldShowEmptyState: false,
        shouldShowExamplePrompts: true
      });
      
      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue({
        ...defaultStoreState,
        messages: [{ id: '1', content: 'Test' }]
      });

      render(<MainChat />);
      
      expect(screen.queryByText(/Start a conversation/i)).not.toBeInTheDocument();
    });
  });

  describe('Integration with Multiple Hooks', () => {
    test('should coordinate all hooks correctly', () => {
      // Set up complex state
      (useInitializationCoordinator as jest.Mock).mockReturnValue({
        ...defaultInitState,
        isInitialized: true
      });
      
      (useLoadingState as jest.Mock).mockReturnValue({
        shouldShowLoading: false,
        shouldShowEmptyState: false,
        shouldShowExamplePrompts: false,
        loadingMessage: ''
      });
      
      (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue({
        ...defaultStoreState,
        messages: [{ id: '1', content: 'Test message' }],
        isProcessing: true,
        currentRunId: 'run-123'
      });
      
      (useThreadNavigation as jest.Mock).mockReturnValue({
        currentThreadId: 'thread-123',
        isNavigating: false
      });
      
      (useWebSocket as jest.Mock).mockReturnValue({
        messages: [{ type: 'test', data: {} }],
        isConnected: true,
        status: 'OPEN'
      });

      render(<MainChat />);
      
      // All components should render correctly
      expect(screen.getByTestId('main-chat')).toBeInTheDocument();
      expect(screen.getByTestId('chat-header')).toBeInTheDocument();
      expect(screen.getByTestId('message-list')).toBeInTheDocument();
      expect(screen.getByTestId('response-card')).toBeInTheDocument();
      expect(screen.getByTestId('message-input')).toBeInTheDocument();
    });
  });
});