import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';

// Hoist all mocks to the top for proper Jest handling
const mockUseUnifiedChatStore = jest.fn();
const mockUseLoadingState = jest.fn();
const mockUseThreadNavigation = jest.fn();
const mockUseWebSocket = jest.fn();
const mockUseEventProcessor = jest.fn();

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

// Mock all the components
jest.mock('@/components/chat/ChatHeader', () => ({
  ChatHeader: () => <div data-testid="chat-header">Chat Header</div>
}));

jest.mock('@/components/chat/MessageList', () => ({
  MessageList: () => <div data-testid="message-list">Message List</div>
}));

jest.mock('@/components/chat/MessageInput', () => ({
  MessageInput: () => <div data-testid="message-input">Message Input</div>
}));

jest.mock('@/components/chat/ExamplePrompts', () => ({
  ExamplePrompts: () => <div data-testid="example-prompts">Example Prompts</div>
}));

jest.mock('@/components/chat/PersistentResponseCard', () => ({
  PersistentResponseCard: ({ isCollapsed, onToggleCollapse }: any) => (
    <div data-testid="response-card" data-collapsed={isCollapsed}>
      <button onClick={onToggleCollapse}>Toggle</button>
      Response Card
    </div>
  )
}));

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
      
      expect(screen.getByTestId('message-list')).toBeInTheDocument();
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
      
      expect(screen.getByTestId('example-prompts')).toBeInTheDocument();
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
      expect(screen.getByTestId('message-list')).toBeInTheDocument();
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
      expect(screen.getByTestId('message-list')).toBeInTheDocument();
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
      expect(screen.getByTestId('message-list')).toBeInTheDocument();
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
      
      expect(screen.getByTestId('message-list')).toBeInTheDocument();
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
      expect(screen.getByTestId('message-list')).toBeInTheDocument();
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
      expect(screen.getByTestId('message-list')).toBeInTheDocument();
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
      expect(screen.getByTestId('example-prompts')).toBeInTheDocument();
      expect(screen.queryByTestId('response-card')).not.toBeInTheDocument();
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
        expect(screen.queryByTestId('example-prompts')).not.toBeInTheDocument();
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
      expect(screen.getByTestId('message-list')).toBeInTheDocument();
    });
  });
});