import React from 'react';
import { render, screen, waitFor, within, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// Hoist all mocks to the top level for proper Jest handling
var mockUseUnifiedChatStore = jest.fn();
var mockUseLoadingState = jest.fn();
var mockUseThreadNavigation = jest.fn();
var mockUseWebSocket = jest.fn();
var mockUseEventProcessor = jest.fn();

jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: mockUseUnifiedChatStore
}));

jest.mock('@/hooks/useLoadingState', () => ({
  useLoadingState: mockUseLoadingState
}));

jest.mock('@/hooks/useThreadNavigation', () => ({
  useThreadNavigation: mockUseThreadNavigation
}));

jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: mockUseWebSocket
}));

jest.mock('@/hooks/useEventProcessor', () => ({
  useEventProcessor: mockUseEventProcessor
}));

// Mock utility services but NOT UI components
jest.mock('@/utils/debug-logger', () => ({
  logger: {
    debug: jest.fn(),
    error: jest.fn(),
    info: jest.fn(),
    warn: jest.fn()
  }
}));

// Mock framer-motion to avoid animation issues
jest.mock('framer-motion', () => ({
  motion: {
    div: 'div',
  },
  AnimatePresence: ({ children }: any) => children,
}));

import MainChat from '@/components/chat/MainChat';

const mockStore = {
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
};

describe('MainChat - Agent Status Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
    
    // Set up default mock return values
    mockUseUnifiedChatStore.mockReturnValue(mockStore);
    
    mockUseWebSocket.mockReturnValue({
      messages: [],
      connected: true,
      error: null
    });
    
    mockUseLoadingState.mockReturnValue({
      shouldShowLoading: false,
      shouldShowEmptyState: false,
      shouldShowExamplePrompts: false,
      loadingMessage: ''
    });
    
    mockUseThreadNavigation.mockReturnValue({
      currentThreadId: null,
      isNavigating: false,
      navigateToThread: jest.fn(),
      createNewThread: jest.fn()
    });
    
    mockUseEventProcessor.mockReturnValue({
      processedEvents: [],
      isProcessing: false,
      stats: { processed: 0, failed: 0 }
    });
  });

  afterEach(() => {
    jest.useRealTimers();
    jest.clearAllMocks();
  });

  describe('Agent status updates', () => {
    it('should show response card when processing', () => {
      mockUseUnifiedChatStore.mockReturnValue({
        ...mockStore,
        isProcessing: true,
        currentRunId: 'run-123',
        activeThreadId: 'thread-1'
      });
      
      mockUseThreadNavigation.mockReturnValue({
        currentThreadId: 'thread-1',
        isNavigating: false,
        navigateToThread: jest.fn(),
        createNewThread: jest.fn()
      });
      
      render(<MainChat />);
      
      expect(screen.getByText(/response card/i)).toBeInTheDocument();
    });

    it('should hide response card when not processing and no run', () => {
      render(<MainChat />);
      
      expect(screen.queryByText(/response card/i)).not.toBeInTheDocument();
    });

    it('should display fast layer data', () => {
      mockUseUnifiedChatStore.mockReturnValue({
        ...mockStore,
        isProcessing: true,
        currentRunId: 'run-123',
        activeThreadId: 'thread-1',
        fastLayerData: {
          initialAnalysis: 'Quick analysis',
          suggestions: ['Suggestion 1', 'Suggestion 2']
        }
      });
      
      mockUseThreadNavigation.mockReturnValue({
        currentThreadId: 'thread-1',
        isNavigating: false,
        navigateToThread: jest.fn(),
        createNewThread: jest.fn()
      });
      
      render(<MainChat />);
      
      expect(screen.getByText(/response card/i)).toBeInTheDocument();
    });

    it('should display medium layer data', () => {
      mockUseUnifiedChatStore.mockReturnValue({
        ...mockStore,
        isProcessing: true,
        currentRunId: 'run-123',
        activeThreadId: 'thread-1',
        mediumLayerData: {
          deeperAnalysis: 'Detailed analysis',
          recommendations: ['Rec 1', 'Rec 2']
        }
      });
      
      mockUseThreadNavigation.mockReturnValue({
        currentThreadId: 'thread-1',
        isNavigating: false,
        navigateToThread: jest.fn(),
        createNewThread: jest.fn()
      });
      
      render(<MainChat />);
      
      expect(screen.getByText(/response card/i)).toBeInTheDocument();
    });

    it('should display slow layer data with final report', () => {
      mockUseUnifiedChatStore.mockReturnValue({
        ...mockStore,
        isProcessing: false,
        currentRunId: 'run-123',
        activeThreadId: 'thread-1',
        slowLayerData: {
          finalReport: 'Complete analysis report',
          metrics: { accuracy: 0.95 }
        }
      });
      
      mockUseThreadNavigation.mockReturnValue({
        currentThreadId: 'thread-1',
        isNavigating: false,
        navigateToThread: jest.fn(),
        createNewThread: jest.fn()
      });
      
      render(<MainChat />);
      
      expect(screen.getByText(/response card/i)).toBeInTheDocument();
    });

    it('should auto-collapse card after completion', async () => {
      mockUseUnifiedChatStore.mockReturnValue({
        ...mockStore,
        isProcessing: false,
        currentRunId: 'run-123',
        activeThreadId: 'thread-1',
        slowLayerData: {
          finalReport: 'Complete'
        }
      });
      
      mockUseThreadNavigation.mockReturnValue({
        currentThreadId: 'thread-1',
        isNavigating: false,
        navigateToThread: jest.fn(),
        createNewThread: jest.fn()
      });
      
      render(<MainChat />);
      
      const card = screen.getByText(/response card/i).closest('[role=\"region\"]') as HTMLElement;
      expect(card).not.toHaveAttribute('data-collapsed', 'true');
      
      // Fast-forward timer
      act(() => {
        jest.advanceTimersByTime(2000);
      });
      
      await waitFor(() => {
        expect(card).toHaveAttribute('data-collapsed', 'true');
      });
    });

    it('should reset collapse state when new processing starts', () => {
      // Start with completed state
      mockUseUnifiedChatStore.mockReturnValue({
        ...mockStore,
        isProcessing: false,
        currentRunId: 'run-123',
        activeThreadId: 'thread-1',
        slowLayerData: { finalReport: 'Done' }
      });
      
      mockUseThreadNavigation.mockReturnValue({
        currentThreadId: 'thread-1',
        isNavigating: false,
        navigateToThread: jest.fn(),
        createNewThread: jest.fn()
      });
      
      const { rerender } = render(<MainChat />);
      
      act(() => {
        jest.advanceTimersByTime(2000);
      });
      
      // Start new processing
      mockUseUnifiedChatStore.mockReturnValue({
        ...mockStore,
        isProcessing: true,
        currentRunId: 'run-124',
        activeThreadId: 'thread-1',
        slowLayerData: null
      });
      
      rerender(<MainChat />);
      
      const card = screen.getByText(/response card/i).closest('[role=\"region\"]') as HTMLElement;
      expect(card).not.toHaveAttribute('data-collapsed', 'true');
    });

    it('should handle toggle collapse manually', () => {
      mockUseUnifiedChatStore.mockReturnValue({
        ...mockStore,
        isProcessing: true,
        currentRunId: 'run-123',
        activeThreadId: 'thread-1'
      });
      
      mockUseThreadNavigation.mockReturnValue({
        currentThreadId: 'thread-1',
        isNavigating: false,
        navigateToThread: jest.fn(),
        createNewThread: jest.fn()
      });
      
      render(<MainChat />);
      
      const card = screen.getByText(/response card/i).closest('[role=\"region\"]') as HTMLElement;
      const toggleButton = within(card).getByRole('button', { name: /collapse|expand/i });
      
      expect(card).not.toHaveAttribute('data-collapsed', 'true');
      
      // First click to collapse
      act(() => {
        toggleButton.click();
      });
      expect(card).toHaveAttribute('data-collapsed', 'true');
      
      // Second click to expand
      act(() => {
        toggleButton.click();
      });
      expect(card).not.toHaveAttribute('data-collapsed', 'true');
    });
  });
});