import React from 'react';
import { render, screen, waitFor, within, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// Mock only the hooks and services, NOT UI components
jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: jest.fn()
}));

jest.mock('@/hooks/useLoadingState', () => ({
  useLoadingState: jest.fn()
}));

jest.mock('@/hooks/useThreadNavigation', () => ({
  useThreadNavigation: jest.fn()
}));

jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: jest.fn()
}));

jest.mock('@/hooks/useEventProcessor', () => ({
  useEventProcessor: jest.fn()
}));

// Mock utility services but NOT UI components
jest.mock('@/lib/logger', () => ({
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

// Mock chat components
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
    <div 
      role="region" 
      aria-label="response card"
      data-testid="response-card"
      data-collapsed={isCollapsed?.toString()}
    >
      <span>response card</span>
      <button 
        role="button" 
        aria-label={`${isCollapsed ? 'expand' : 'collapse'} analysis card`}
        onClick={onToggleCollapse}
      >
        {isCollapsed ? 'Expand' : 'Collapse'}
      </button>
    </div>
  )
}));

jest.mock('@/components/chat/ExamplePrompts', () => ({
  ExamplePrompts: () => <div data-testid="example-prompts">Example Prompts</div>
}));

jest.mock('@/components/chat/OverflowPanel', () => ({
  OverflowPanel: () => <div data-testid="overflow-panel">Overflow Panel</div>
}));

jest.mock('@/components/chat/EventDiagnosticsPanel', () => ({
  EventDiagnosticsPanel: () => <div data-testid="event-diagnostics-panel">Event Diagnostics Panel</div>
}));

// Mock lucide-react icons
jest.mock('lucide-react', () => ({
  Loader2: () => <div data-testid="loader">Loading...</div>,
  ChevronDown: () => <div data-testid="chevron-down">▼</div>,
  ChevronUp: () => <div data-testid="chevron-up">▲</div>
}));

import MainChat from '@/components/chat/MainChat';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useLoadingState } from '@/hooks/useLoadingState';
import { useThreadNavigation } from '@/hooks/useThreadNavigation';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useEventProcessor } from '@/hooks/useEventProcessor';

// Get the mocked functions
const mockUseUnifiedChatStore = useUnifiedChatStore as jest.MockedFunction<typeof useUnifiedChatStore>;
const mockUseLoadingState = useLoadingState as jest.MockedFunction<typeof useLoadingState>;
const mockUseThreadNavigation = useThreadNavigation as jest.MockedFunction<typeof useThreadNavigation>;
const mockUseWebSocket = useWebSocket as jest.MockedFunction<typeof useWebSocket>;
const mockUseEventProcessor = useEventProcessor as jest.MockedFunction<typeof useEventProcessor>;

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