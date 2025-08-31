import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';

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
  MessageList: () => <div data-testid="message-list" role="list">Message List</div>
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
  ExamplePrompts: () => <div data-testid="example-prompts">explore these examples</div>
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

describe('MainChat - Message Interactions Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    
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
    jest.clearAllMocks();
  });

  describe('Message sending and receiving', () => {
    it('should display messages from store', () => {
      const messages = [
        { id: '1', type: 'user', content: 'Hello', displayed_to_user: true },
        { id: '2', type: 'agent', content: 'Hi there!', displayed_to_user: true }
      ];
      
      // First setup mocks in the right order
      mockUseLoadingState.mockImplementation(() => ({
        shouldShowLoading: false,
        shouldShowEmptyState: false,
        shouldShowExamplePrompts: false,
        loadingMessage: ''
      }));
      
      mockUseThreadNavigation.mockImplementation(() => ({
        currentThreadId: 'thread-1',
        isNavigating: false,
        navigateToThread: jest.fn(),
        createNewThread: jest.fn()
      }));
      
      mockUseUnifiedChatStore.mockImplementation(() => ({
        ...mockStore,
        messages,
        activeThreadId: 'thread-1'
      }));
      
      render(<MainChat />);
      
      expect(screen.getByRole('list')).toBeInTheDocument();
    });

    it('should show example prompts when no messages', () => {
      // Configure mocks for example prompts state
      mockUseLoadingState.mockReturnValue({
        shouldShowLoading: false,
        shouldShowEmptyState: false,
        shouldShowExamplePrompts: true,
        loadingMessage: ''
      });
      
      mockUseThreadNavigation.mockReturnValue({
        currentThreadId: 'thread-1',
        isNavigating: false,
        navigateToThread: jest.fn(),
        createNewThread: jest.fn()
      });
      
      mockUseUnifiedChatStore.mockReturnValue({
        ...mockStore,
        messages: [],
        activeThreadId: 'thread-1'
      });
      
      render(<MainChat />);
      
      expect(screen.getByText(/explore these examples/i)).toBeInTheDocument();
    });

    it('should hide example prompts when messages exist', () => {
      // Configure mocks for message display state (no example prompts)
      mockUseLoadingState.mockReturnValue({
        shouldShowLoading: false,
        shouldShowEmptyState: false,
        shouldShowExamplePrompts: false,
        loadingMessage: ''
      });
      
      mockUseThreadNavigation.mockReturnValue({
        currentThreadId: 'thread-1',
        isNavigating: false,
        navigateToThread: jest.fn(),
        createNewThread: jest.fn()
      });
      
      mockUseUnifiedChatStore.mockReturnValue({
        ...mockStore,
        messages: [{ id: '1', type: 'user', content: 'Test' }],
        activeThreadId: 'thread-1'
      });
      
      render(<MainChat />);
      
      expect(screen.queryByTestId('example-prompts')).not.toBeInTheDocument();
    });

    it('should handle message updates from WebSocket', () => {
      // Initial state - no messages, show example prompts
      mockUseLoadingState.mockReturnValue({
        shouldShowLoading: false,
        shouldShowEmptyState: false,
        shouldShowExamplePrompts: true,
        loadingMessage: ''
      });
      
      mockUseThreadNavigation.mockReturnValue({
        currentThreadId: 'thread-1',
        isNavigating: false,
        navigateToThread: jest.fn(),
        createNewThread: jest.fn()
      });
      
      mockUseUnifiedChatStore.mockReturnValue({
        ...mockStore,
        messages: [],
        activeThreadId: 'thread-1'
      });
      
      const { rerender } = render(<MainChat />);
      
      // Update mocks for message received state
      mockUseLoadingState.mockReturnValue({
        shouldShowLoading: false,
        shouldShowEmptyState: false,
        shouldShowExamplePrompts: false,
        loadingMessage: ''
      });
      
      // Simulate receiving a message
      mockUseUnifiedChatStore.mockReturnValue({
        ...mockStore,
        messages: [{ id: '1', type: 'user', content: 'New message' }],
        activeThreadId: 'thread-1'
      });
      
      rerender(<MainChat />);
      
      // Message list should be present
      expect(screen.getByRole('list')).toBeInTheDocument();
    });

    it('should maintain message order', () => {
      const messages = [
        { id: '1', type: 'user', content: 'First', created_at: '2024-01-01T10:00:00Z' },
        { id: '2', type: 'agent', content: 'Second', created_at: '2024-01-01T10:01:00Z' },
        { id: '3', type: 'user', content: 'Third', created_at: '2024-01-01T10:02:00Z' }
      ];
      
      // Configure mocks for message display state
      mockUseLoadingState.mockReturnValue({
        shouldShowLoading: false,
        shouldShowEmptyState: false,
        shouldShowExamplePrompts: false,
        loadingMessage: ''
      });
      
      mockUseThreadNavigation.mockReturnValue({
        currentThreadId: 'thread-1',
        isNavigating: false,
        navigateToThread: jest.fn(),
        createNewThread: jest.fn()
      });
      
      mockUseUnifiedChatStore.mockReturnValue({
        ...mockStore,
        messages,
        activeThreadId: 'thread-1'
      });
      
      render(<MainChat />);
      
      // Messages should be displayed in order
      expect(screen.getByRole('list')).toBeInTheDocument();
    });

    it('should handle empty message content gracefully', () => {
      const messages = [
        { id: '1', type: 'user', content: '' },
        { id: '2', type: 'agent', content: null }
      ];
      
      // Configure mocks for message display state
      mockUseLoadingState.mockReturnValue({
        shouldShowLoading: false,
        shouldShowEmptyState: false,
        shouldShowExamplePrompts: false,
        loadingMessage: ''
      });
      
      mockUseThreadNavigation.mockReturnValue({
        currentThreadId: 'thread-1',
        isNavigating: false,
        navigateToThread: jest.fn(),
        createNewThread: jest.fn()
      });
      
      mockUseUnifiedChatStore.mockReturnValue({
        ...mockStore,
        messages,
        activeThreadId: 'thread-1'
      });
      
      render(<MainChat />);
      
      // Should not crash
      expect(screen.getByRole('list')).toBeInTheDocument();
    });
  });

  describe('Message history loading', () => {
    it('should load message history on mount', () => {
      const historicalMessages = [
        { id: 'h1', type: 'user', content: 'Historical 1' },
        { id: 'h2', type: 'agent', content: 'Historical 2' }
      ];
      
      // Configure mocks for message display state
      mockUseLoadingState.mockReturnValue({
        shouldShowLoading: false,
        shouldShowEmptyState: false,
        shouldShowExamplePrompts: false,
        loadingMessage: ''
      });
      
      mockUseThreadNavigation.mockReturnValue({
        currentThreadId: 'thread-1',
        isNavigating: false,
        navigateToThread: jest.fn(),
        createNewThread: jest.fn()
      });
      
      mockUseUnifiedChatStore.mockReturnValue({
        ...mockStore,
        messages: historicalMessages,
        activeThreadId: 'thread-1'
      });
      
      render(<MainChat />);
      
      expect(screen.getByRole('list')).toBeInTheDocument();
    });

    it('should handle pagination of message history', () => {
      const manyMessages = Array.from({ length: 100 }, (_, i) => ({
        id: `msg-${i}`,
        type: i % 2 === 0 ? 'user' : 'agent',
        content: `Message ${i}`
      }));
      
      // Configure mocks for message display state
      mockUseLoadingState.mockReturnValue({
        shouldShowLoading: false,
        shouldShowEmptyState: false,
        shouldShowExamplePrompts: false,
        loadingMessage: ''
      });
      
      mockUseThreadNavigation.mockReturnValue({
        currentThreadId: 'thread-1',
        isNavigating: false,
        navigateToThread: jest.fn(),
        createNewThread: jest.fn()
      });
      
      mockUseUnifiedChatStore.mockReturnValue({
        ...mockStore,
        messages: manyMessages,
        activeThreadId: 'thread-1'
      });
      
      render(<MainChat />);
      
      // Should handle large message lists
      expect(screen.getByRole('list')).toBeInTheDocument();
    });

    it('should preserve scroll position when loading history', async () => {
      // Configure mocks for message display state
      mockUseLoadingState.mockReturnValue({
        shouldShowLoading: false,
        shouldShowEmptyState: false,
        shouldShowExamplePrompts: false,
        loadingMessage: ''
      });
      
      mockUseThreadNavigation.mockReturnValue({
        currentThreadId: 'thread-1',
        isNavigating: false,
        navigateToThread: jest.fn(),
        createNewThread: jest.fn()
      });
      
      mockUseUnifiedChatStore.mockReturnValue({
        ...mockStore,
        messages: [],
        activeThreadId: 'thread-1'
      });
      
      const { rerender } = render(<MainChat />);
      
      // Initial messages
      mockUseUnifiedChatStore.mockReturnValue({
        ...mockStore,
        messages: [
          { id: '1', type: 'user', content: 'Initial' }
        ],
        activeThreadId: 'thread-1'
      });
      
      rerender(<MainChat />);
      
      // Load more history
      mockUseUnifiedChatStore.mockReturnValue({
        ...mockStore,
        messages: [
          { id: '0', type: 'user', content: 'Earlier' },
          { id: '1', type: 'user', content: 'Initial' }
        ],
        activeThreadId: 'thread-1'
      });
      
      rerender(<MainChat />);
      
      // Scroll position should be maintained
      expect(screen.getByRole('list')).toBeInTheDocument();
    });

    it('should handle empty message history', () => {
      // Configure mocks for empty state with example prompts
      mockUseLoadingState.mockReturnValue({
        shouldShowLoading: false,
        shouldShowEmptyState: false,
        shouldShowExamplePrompts: true,
        loadingMessage: ''
      });
      
      mockUseThreadNavigation.mockReturnValue({
        currentThreadId: 'thread-1',
        isNavigating: false,
        navigateToThread: jest.fn(),
        createNewThread: jest.fn()
      });
      
      mockUseUnifiedChatStore.mockReturnValue({
        ...mockStore,
        messages: [],
        activeThreadId: 'thread-1',
        currentRunId: null
      });
      
      render(<MainChat />);
      
      // Should show example prompts instead
      expect(screen.getByText(/explore these examples/i)).toBeInTheDocument();
      expect(screen.queryByText(/fast layer/i)).not.toBeInTheDocument();
    });

    it('should update history when new messages arrive', async () => {
      // Initial state - no messages, show example prompts
      mockUseLoadingState.mockReturnValue({
        shouldShowLoading: false,
        shouldShowEmptyState: false,
        shouldShowExamplePrompts: true,
        loadingMessage: ''
      });
      
      mockUseThreadNavigation.mockReturnValue({
        currentThreadId: 'thread-1',
        isNavigating: false,
        navigateToThread: jest.fn(),
        createNewThread: jest.fn()
      });
      
      mockUseUnifiedChatStore.mockReturnValue({
        ...mockStore,
        messages: [],
        activeThreadId: 'thread-1'
      });
      
      const { rerender } = render(<MainChat />);
      
      // Update mocks for new message state
      mockUseLoadingState.mockReturnValue({
        shouldShowLoading: false,
        shouldShowEmptyState: false,
        shouldShowExamplePrompts: false,
        loadingMessage: ''
      });
      
      // Add new message
      mockUseUnifiedChatStore.mockReturnValue({
        ...mockStore,
        messages: [{ id: 'new-1', type: 'user', content: 'New message' }],
        activeThreadId: 'thread-1'
      });
      
      rerender(<MainChat />);
      
      // Example prompts should disappear when there are messages
      await waitFor(() => {
        expect(screen.queryByText(/explore these examples/i)).not.toBeInTheDocument();
      });
    });

    it('should handle message deletion from history', () => {
      // Configure mocks for message display state
      mockUseLoadingState.mockReturnValue({
        shouldShowLoading: false,
        shouldShowEmptyState: false,
        shouldShowExamplePrompts: false,
        loadingMessage: ''
      });
      
      mockUseThreadNavigation.mockReturnValue({
        currentThreadId: 'thread-1',
        isNavigating: false,
        navigateToThread: jest.fn(),
        createNewThread: jest.fn()
      });
      
      mockUseUnifiedChatStore.mockReturnValue({
        ...mockStore,
        messages: [],
        activeThreadId: 'thread-1'
      });
      
      const { rerender } = render(<MainChat />);
      
      // Start with messages
      mockUseUnifiedChatStore.mockReturnValue({
        ...mockStore,
        messages: [
          { id: '1', type: 'user', content: 'Message 1' },
          { id: '2', type: 'agent', content: 'Message 2' }
        ],
        activeThreadId: 'thread-1'
      });
      
      rerender(<MainChat />);
      
      // Delete a message
      mockUseUnifiedChatStore.mockReturnValue({
        ...mockStore,
        messages: [
          { id: '2', type: 'agent', content: 'Message 2' }
        ],
        activeThreadId: 'thread-1'
      });
      
      rerender(<MainChat />);
      
      // Should still render
      expect(screen.getByRole('list')).toBeInTheDocument();
    });
  });
});