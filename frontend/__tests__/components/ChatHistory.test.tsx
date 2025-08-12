import React from 'react';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChatHistory } from '@/components/chat/ChatHistory';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useWebSocket } from '@/hooks/useWebSocket';
import { chatService } from '@/services/chatService';
import { WebSocketProvider } from '@/providers/WebSocketProvider';

// Mock dependencies
jest.mock('@/store/unified-chat');
jest.mock('@/hooks/useWebSocket');
jest.mock('@/services/chatService');
jest.mock('@/components/ui/button', () => ({
  Button: ({ children, onClick, disabled, variant }: any) => (
    <button onClick={onClick} disabled={disabled} data-variant={variant}>
      {children}
    </button>
  )
}));
jest.mock('@/components/ui/scroll-area', () => ({
  ScrollArea: ({ children, className }: any) => (
    <div className={className} data-testid="scroll-area">{children}</div>
  )
}));

// Mock IntersectionObserver
const mockIntersectionObserver = jest.fn();
mockIntersectionObserver.mockReturnValue({
  observe: () => null,
  unobserve: () => null,
  disconnect: () => null,
});
window.IntersectionObserver = mockIntersectionObserver;

describe('ChatHistory Component', () => {
  const mockChatStore = {
    currentThreadId: 'thread-123',
    messages: [],
    historyMessages: [],
    isLoadingHistory: false,
    hasMoreHistory: true,
    historyError: null,
    loadMessageHistory: jest.fn(),
    loadMoreHistory: jest.fn(),
    clearHistory: jest.fn(),
    deleteMessage: jest.fn(),
    retryLoadHistory: jest.fn(),
    searchMessages: jest.fn(),
    searchResults: []
  };

  const mockWebSocket = {
    connected: true,
    error: null,
    sendMessage: jest.fn()
  };

  const mockChatService = {
    getMessageHistory: jest.fn(),
    searchMessages: jest.fn(),
    deleteMessage: jest.fn()
  };

  beforeEach(() => {
    jest.clearAllMocks();
    (useUnifiedChatStore as jest.Mock).mockReturnValue(mockChatStore);
    (useWebSocket as jest.Mock).mockReturnValue(mockWebSocket);
    (chatService as any).mockReturnValue(mockChatService);
  });

  const renderWithProvider = (component: React.ReactElement) => {
    return render(
      <WebSocketProvider>
        {component}
      </WebSocketProvider>
    );
  };

  describe('History Loading and Pagination', () => {
    it('should load initial message history on mount', async () => {
      renderWithProvider(<ChatHistory threadId="thread-123" />);
      
      await waitFor(() => {
        expect(mockChatStore.loadMessageHistory).toHaveBeenCalledWith('thread-123');
      });
    });

    it('should display loading state during initial load', () => {
      const loadingStore = {
        ...mockChatStore,
        isLoadingHistory: true
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(loadingStore);
      
      renderWithProvider(<ChatHistory threadId="thread-123" />);
      
      expect(screen.getByTestId('history-loading')).toBeInTheDocument();
      expect(screen.getByText(/loading message history/i)).toBeInTheDocument();
    });

    it('should display message history once loaded', () => {
      const historyStore = {
        ...mockChatStore,
        historyMessages: [
          {
            id: 'msg-1',
            content: 'Hello, how can I help you?',
            role: 'assistant',
            timestamp: new Date().toISOString(),
            threadId: 'thread-123'
          },
          {
            id: 'msg-2', 
            content: 'I need help with optimization',
            role: 'user',
            timestamp: new Date().toISOString(),
            threadId: 'thread-123'
          }
        ]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(historyStore);
      
      renderWithProvider(<ChatHistory threadId="thread-123" />);
      
      expect(screen.getByTestId('message-history-list')).toBeInTheDocument();
      expect(screen.getByText('Hello, how can I help you?')).toBeInTheDocument();
      expect(screen.getByText('I need help with optimization')).toBeInTheDocument();
    });

    it('should load more history when scrolled to top', async () => {
      const historyStore = {
        ...mockChatStore,
        historyMessages: [
          { id: 'msg-1', content: 'Recent message', role: 'user', timestamp: new Date().toISOString() }
        ],
        hasMoreHistory: true
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(historyStore);
      
      renderWithProvider(<ChatHistory threadId="thread-123" />);
      
      // Mock intersection observer triggering for load more
      const [intersectionCallback] = mockIntersectionObserver.mock.calls[0];
      intersectionCallback([{ isIntersecting: true }]);
      
      await waitFor(() => {
        expect(mockChatStore.loadMoreHistory).toHaveBeenCalled();
      });
    });

    it('should show "Load More" button when more history available', () => {
      const moreHistoryStore = {
        ...mockChatStore,
        historyMessages: [
          { id: 'msg-1', content: 'Message 1', role: 'user' }
        ],
        hasMoreHistory: true
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(moreHistoryStore);
      
      renderWithProvider(<ChatHistory threadId="thread-123" />);
      
      expect(screen.getByTestId('load-more-btn')).toBeInTheDocument();
      expect(screen.getByText(/load more messages/i)).toBeInTheDocument();
    });

    it('should handle "Load More" button click', async () => {
      const moreHistoryStore = {
        ...mockChatStore,
        historyMessages: [
          { id: 'msg-1', content: 'Message 1', role: 'user' }
        ],
        hasMoreHistory: true
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(moreHistoryStore);
      
      renderWithProvider(<ChatHistory threadId="thread-123" />);
      
      const loadMoreBtn = screen.getByTestId('load-more-btn');
      await userEvent.click(loadMoreBtn);
      
      expect(mockChatStore.loadMoreHistory).toHaveBeenCalled();
    });

    it('should hide "Load More" when no more history available', () => {
      const noMoreHistoryStore = {
        ...mockChatStore,
        historyMessages: [
          { id: 'msg-1', content: 'Message 1', role: 'user' }
        ],
        hasMoreHistory: false
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(noMoreHistoryStore);
      
      renderWithProvider(<ChatHistory threadId="thread-123" />);
      
      expect(screen.queryByTestId('load-more-btn')).not.toBeInTheDocument();
      expect(screen.getByText(/no more messages/i)).toBeInTheDocument();
    });

    it('should show loading state for pagination', () => {
      const paginationLoadingStore = {
        ...mockChatStore,
        historyMessages: [
          { id: 'msg-1', content: 'Message 1', role: 'user' }
        ],
        isLoadingHistory: true,
        hasMoreHistory: true
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(paginationLoadingStore);
      
      renderWithProvider(<ChatHistory threadId="thread-123" />);
      
      expect(screen.getByTestId('pagination-loading')).toBeInTheDocument();
      expect(screen.getByText(/loading more messages/i)).toBeInTheDocument();
    });

    it('should preserve scroll position when loading more history', async () => {
      const scrollSpy = jest.fn();
      const mockScrollArea = {
        scrollTop: 100,
        scrollHeight: 500,
        scrollTo: scrollSpy
      };
      
      jest.spyOn(document, 'querySelector').mockReturnValue(mockScrollArea as any);
      
      const historyStore = {
        ...mockChatStore,
        historyMessages: [
          { id: 'msg-1', content: 'Message 1', role: 'user' }
        ],
        hasMoreHistory: true
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(historyStore);
      
      renderWithProvider(<ChatHistory threadId="thread-123" />);
      
      const loadMoreBtn = screen.getByTestId('load-more-btn');
      await userEvent.click(loadMoreBtn);
      
      // Simulate new messages loaded
      const updatedStore = {
        ...historyStore,
        historyMessages: [
          { id: 'msg-0', content: 'Older message', role: 'assistant' },
          { id: 'msg-1', content: 'Message 1', role: 'user' }
        ]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(updatedStore);
      
      // Should maintain relative scroll position
      await waitFor(() => {
        expect(scrollSpy).toHaveBeenCalled();
      });
    });

    it('should handle thread switching', async () => {
      const { rerender } = renderWithProvider(<ChatHistory threadId="thread-123" />);
      
      expect(mockChatStore.loadMessageHistory).toHaveBeenCalledWith('thread-123');
      
      // Switch to different thread
      rerender(
        <WebSocketProvider>
          <ChatHistory threadId="thread-456" />
        </WebSocketProvider>
      );
      
      await waitFor(() => {
        expect(mockChatStore.loadMessageHistory).toHaveBeenCalledWith('thread-456');
      });
    });

    it('should batch load requests to prevent excessive API calls', async () => {
      const historyStore = {
        ...mockChatStore,
        hasMoreHistory: true
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(historyStore);
      
      renderWithProvider(<ChatHistory threadId="thread-123" />);
      
      const loadMoreBtn = screen.getByTestId('load-more-btn');
      
      // Rapidly click load more multiple times
      await userEvent.click(loadMoreBtn);
      await userEvent.click(loadMoreBtn);
      await userEvent.click(loadMoreBtn);
      
      // Should debounce and only make one call
      await waitFor(() => {
        expect(mockChatStore.loadMoreHistory).toHaveBeenCalledTimes(1);
      });
    });
  });

  describe('Message Display and Formatting', () => {
    it('should display messages in chronological order', () => {
      const orderedMessages = [
        {
          id: 'msg-1',
          content: 'First message',
          role: 'user',
          timestamp: '2024-01-01T10:00:00Z'
        },
        {
          id: 'msg-2',
          content: 'Second message', 
          role: 'assistant',
          timestamp: '2024-01-01T10:01:00Z'
        },
        {
          id: 'msg-3',
          content: 'Third message',
          role: 'user',
          timestamp: '2024-01-01T10:02:00Z'
        }
      ];
      
      const historyStore = {
        ...mockChatStore,
        historyMessages: orderedMessages
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(historyStore);
      
      renderWithProvider(<ChatHistory threadId="thread-123" />);
      
      const messageItems = screen.getAllByTestId(/^message-item-/);
      expect(messageItems).toHaveLength(3);
      
      // Should be in chronological order
      expect(within(messageItems[0]).getByText('First message')).toBeInTheDocument();
      expect(within(messageItems[1]).getByText('Second message')).toBeInTheDocument(); 
      expect(within(messageItems[2]).getByText('Third message')).toBeInTheDocument();
    });

    it('should format timestamps correctly', () => {
      const timestampedMessage = {
        id: 'msg-1',
        content: 'Test message',
        role: 'user',
        timestamp: '2024-01-01T15:30:00Z'
      };
      
      const historyStore = {
        ...mockChatStore,
        historyMessages: [timestampedMessage]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(historyStore);
      
      renderWithProvider(<ChatHistory threadId="thread-123" />);
      
      // Should display formatted timestamp
      expect(screen.getByText(/3:30 PM/)).toBeInTheDocument();
      expect(screen.getByText(/Jan 1, 2024/)).toBeInTheDocument();
    });

    it('should group messages by date', () => {
      const messagesFromDifferentDays = [
        {
          id: 'msg-1',
          content: 'Yesterday message',
          role: 'user',
          timestamp: '2024-01-01T10:00:00Z'
        },
        {
          id: 'msg-2',
          content: 'Today message',
          role: 'user', 
          timestamp: '2024-01-02T10:00:00Z'
        }
      ];
      
      const historyStore = {
        ...mockChatStore,
        historyMessages: messagesFromDifferentDays
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(historyStore);
      
      renderWithProvider(<ChatHistory threadId="thread-123" />);
      
      // Should have date separators
      expect(screen.getByTestId('date-separator-2024-01-01')).toBeInTheDocument();
      expect(screen.getByTestId('date-separator-2024-01-02')).toBeInTheDocument();
    });

    it('should highlight search results', () => {
      const searchStore = {
        ...mockChatStore,
        historyMessages: [
          {
            id: 'msg-1',
            content: 'This is a test message with optimization keywords',
            role: 'user',
            timestamp: new Date().toISOString()
          }
        ],
        searchQuery: 'optimization'
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(searchStore);
      
      renderWithProvider(<ChatHistory threadId="thread-123" />);
      
      // Should highlight search term
      const highlightedText = screen.getByTestId('highlighted-text');
      expect(highlightedText).toHaveTextContent('optimization');
      expect(highlightedText).toHaveClass('bg-yellow-200');
    });

    it('should show message metadata on hover', async () => {
      const messageWithMetadata = {
        id: 'msg-1',
        content: 'Test message',
        role: 'user',
        timestamp: new Date().toISOString(),
        metadata: {
          processingTime: 150,
          tokens: 25,
          model: 'gpt-4'
        }
      };
      
      const historyStore = {
        ...mockChatStore,
        historyMessages: [messageWithMetadata]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(historyStore);
      
      renderWithProvider(<ChatHistory threadId="thread-123" />);
      
      const messageItem = screen.getByTestId('message-item-msg-1');
      await userEvent.hover(messageItem);
      
      await waitFor(() => {
        expect(screen.getByTestId('message-metadata')).toBeInTheDocument();
        expect(screen.getByText('Processing: 150ms')).toBeInTheDocument();
        expect(screen.getByText('Tokens: 25')).toBeInTheDocument();
        expect(screen.getByText('Model: gpt-4')).toBeInTheDocument();
      });
    });

    it('should render markdown content correctly', () => {
      const markdownMessage = {
        id: 'msg-1',
        content: '# Heading\n\n**Bold text** and *italic text*\n\n```python\nprint("hello")\n```',
        role: 'assistant',
        timestamp: new Date().toISOString()
      };
      
      const historyStore = {
        ...mockChatStore,
        historyMessages: [markdownMessage]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(historyStore);
      
      renderWithProvider(<ChatHistory threadId="thread-123" />);
      
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Heading');
      expect(screen.getByTestId('code-block')).toHaveTextContent('print("hello")');
    });

    it('should handle empty message content gracefully', () => {
      const emptyMessage = {
        id: 'msg-1',
        content: '',
        role: 'user',
        timestamp: new Date().toISOString()
      };
      
      const historyStore = {
        ...mockChatStore,
        historyMessages: [emptyMessage]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(historyStore);
      
      renderWithProvider(<ChatHistory threadId="thread-123" />);
      
      expect(screen.getByTestId('empty-message-placeholder')).toBeInTheDocument();
      expect(screen.getByText(/message content unavailable/i)).toBeInTheDocument();
    });
  });

  describe('Message Search and Filtering', () => {
    it('should provide search functionality', async () => {
      renderWithProvider(<ChatHistory threadId="thread-123" />);
      
      const searchInput = screen.getByTestId('message-search-input');
      await userEvent.type(searchInput, 'optimization');
      
      expect(mockChatStore.searchMessages).toHaveBeenCalledWith('optimization');
    });

    it('should display search results', () => {
      const searchResultsStore = {
        ...mockChatStore,
        searchResults: [
          {
            id: 'msg-1',
            content: 'This message contains optimization tips',
            role: 'assistant',
            timestamp: new Date().toISOString(),
            relevanceScore: 0.95
          }
        ],
        searchQuery: 'optimization'
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(searchResultsStore);
      
      renderWithProvider(<ChatHistory threadId="thread-123" />);
      
      expect(screen.getByTestId('search-results')).toBeInTheDocument();
      expect(screen.getByText(/1 result found/i)).toBeInTheDocument();
      expect(screen.getByText('This message contains optimization tips')).toBeInTheDocument();
    });

    it('should clear search results', async () => {
      const searchResultsStore = {
        ...mockChatStore,
        searchResults: [
          { id: 'msg-1', content: 'Search result', role: 'user' }
        ],
        searchQuery: 'test',
        clearSearch: jest.fn()
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(searchResultsStore);
      
      renderWithProvider(<ChatHistory threadId="thread-123" />);
      
      const clearButton = screen.getByTestId('clear-search-btn');
      await userEvent.click(clearButton);
      
      expect(searchResultsStore.clearSearch).toHaveBeenCalled();
    });

    it('should filter by message type', async () => {
      const mixedMessages = [
        { id: 'msg-1', content: 'User message', role: 'user' },
        { id: 'msg-2', content: 'Assistant message', role: 'assistant' },
        { id: 'msg-3', content: 'System message', role: 'system' }
      ];
      
      const historyStore = {
        ...mockChatStore,
        historyMessages: mixedMessages
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(historyStore);
      
      renderWithProvider(<ChatHistory threadId="thread-123" />);
      
      const filterSelect = screen.getByTestId('message-type-filter');
      await userEvent.click(filterSelect);
      
      const userOnlyOption = screen.getByText('User messages only');
      await userEvent.click(userOnlyOption);
      
      // Should only show user messages
      expect(screen.getByText('User message')).toBeInTheDocument();
      expect(screen.queryByText('Assistant message')).not.toBeInTheDocument();
      expect(screen.queryByText('System message')).not.toBeInTheDocument();
    });

    it('should filter by date range', async () => {
      const datedMessages = [
        {
          id: 'msg-1',
          content: 'Old message',
          role: 'user',
          timestamp: '2024-01-01T10:00:00Z'
        },
        {
          id: 'msg-2',
          content: 'Recent message',
          role: 'user',
          timestamp: '2024-01-10T10:00:00Z'
        }
      ];
      
      const historyStore = {
        ...mockChatStore,
        historyMessages: datedMessages
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(historyStore);
      
      renderWithProvider(<ChatHistory threadId="thread-123" />);
      
      const dateFilter = screen.getByTestId('date-range-filter');
      await userEvent.click(dateFilter);
      
      const lastWeekOption = screen.getByText('Last week');
      await userEvent.click(lastWeekOption);
      
      // Should only show recent message
      expect(screen.getByText('Recent message')).toBeInTheDocument();
      expect(screen.queryByText('Old message')).not.toBeInTheDocument();
    });

    it('should debounce search input', async () => {
      jest.useFakeTimers();
      
      renderWithProvider(<ChatHistory threadId="thread-123" />);
      
      const searchInput = screen.getByTestId('message-search-input');
      
      // Type rapidly
      await userEvent.type(searchInput, 'optimization');
      
      // Should not search immediately
      expect(mockChatStore.searchMessages).not.toHaveBeenCalled();
      
      // Fast-forward debounce delay
      jest.advanceTimersByTime(500);
      
      await waitFor(() => {
        expect(mockChatStore.searchMessages).toHaveBeenCalledWith('optimization');
      });
      
      jest.useRealTimers();
    });
  });

  describe('Message Management Actions', () => {
    it('should allow deleting messages', async () => {
      const deletableMessage = {
        id: 'msg-1',
        content: 'Deletable message',
        role: 'user',
        timestamp: new Date().toISOString(),
        canDelete: true
      };
      
      const historyStore = {
        ...mockChatStore,
        historyMessages: [deletableMessage]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(historyStore);
      
      renderWithProvider(<ChatHistory threadId="thread-123" />);
      
      const messageItem = screen.getByTestId('message-item-msg-1');
      await userEvent.hover(messageItem);
      
      const deleteBtn = screen.getByTestId('delete-message-btn');
      await userEvent.click(deleteBtn);
      
      // Should show confirmation dialog
      expect(screen.getByTestId('delete-confirmation')).toBeInTheDocument();
      
      const confirmBtn = screen.getByTestId('confirm-delete-btn');
      await userEvent.click(confirmBtn);
      
      expect(mockChatStore.deleteMessage).toHaveBeenCalledWith('msg-1');
    });

    it('should allow copying message content', async () => {
      const copyableMessage = {
        id: 'msg-1',
        content: 'Copyable message content',
        role: 'assistant',
        timestamp: new Date().toISOString()
      };
      
      const historyStore = {
        ...mockChatStore,
        historyMessages: [copyableMessage]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(historyStore);
      
      // Mock clipboard API
      const writeTextSpy = jest.fn();
      Object.assign(navigator, {
        clipboard: { writeText: writeTextSpy }
      });
      
      renderWithProvider(<ChatHistory threadId="thread-123" />);
      
      const messageItem = screen.getByTestId('message-item-msg-1');
      await userEvent.hover(messageItem);
      
      const copyBtn = screen.getByTestId('copy-message-btn');
      await userEvent.click(copyBtn);
      
      expect(writeTextSpy).toHaveBeenCalledWith('Copyable message content');
    });

    it('should allow regenerating assistant messages', async () => {
      const regenerableMessage = {
        id: 'msg-1',
        content: 'Assistant response',
        role: 'assistant',
        timestamp: new Date().toISOString(),
        canRegenerate: true
      };
      
      const historyStore = {
        ...mockChatStore,
        historyMessages: [regenerableMessage],
        regenerateMessage: jest.fn()
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(historyStore);
      
      renderWithProvider(<ChatHistory threadId="thread-123" />);
      
      const messageItem = screen.getByTestId('message-item-msg-1');
      await userEvent.hover(messageItem);
      
      const regenerateBtn = screen.getByTestId('regenerate-message-btn');
      await userEvent.click(regenerateBtn);
      
      expect(historyStore.regenerateMessage).toHaveBeenCalledWith('msg-1');
    });

    it('should show message edit functionality', async () => {
      const editableMessage = {
        id: 'msg-1',
        content: 'Editable user message',
        role: 'user',
        timestamp: new Date().toISOString(),
        canEdit: true
      };
      
      const historyStore = {
        ...mockChatStore,
        historyMessages: [editableMessage],
        editMessage: jest.fn()
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(historyStore);
      
      renderWithProvider(<ChatHistory threadId="thread-123" />);
      
      const messageItem = screen.getByTestId('message-item-msg-1');
      await userEvent.hover(messageItem);
      
      const editBtn = screen.getByTestId('edit-message-btn');
      await userEvent.click(editBtn);
      
      // Should show edit form
      const editForm = screen.getByTestId('edit-message-form');
      expect(editForm).toBeInTheDocument();
      
      const editInput = screen.getByTestId('edit-message-input');
      expect(editInput).toHaveValue('Editable user message');
      
      await userEvent.clear(editInput);
      await userEvent.type(editInput, 'Updated message content');
      
      const saveBtn = screen.getByTestId('save-edit-btn');
      await userEvent.click(saveBtn);
      
      expect(historyStore.editMessage).toHaveBeenCalledWith('msg-1', 'Updated message content');
    });

    it('should handle bulk message operations', async () => {
      const multipleMessages = [
        { id: 'msg-1', content: 'Message 1', role: 'user', canDelete: true },
        { id: 'msg-2', content: 'Message 2', role: 'assistant', canDelete: true },
        { id: 'msg-3', content: 'Message 3', role: 'user', canDelete: true }
      ];
      
      const historyStore = {
        ...mockChatStore,
        historyMessages: multipleMessages,
        deleteMessages: jest.fn()
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(historyStore);
      
      renderWithProvider(<ChatHistory threadId="thread-123" />);
      
      // Select multiple messages
      const selectAll = screen.getByTestId('select-all-messages');
      await userEvent.click(selectAll);
      
      // Should show bulk actions
      expect(screen.getByTestId('bulk-actions')).toBeInTheDocument();
      
      const bulkDeleteBtn = screen.getByTestId('bulk-delete-btn');
      await userEvent.click(bulkDeleteBtn);
      
      const confirmBtn = screen.getByTestId('confirm-bulk-delete');
      await userEvent.click(confirmBtn);
      
      expect(historyStore.deleteMessages).toHaveBeenCalledWith(['msg-1', 'msg-2', 'msg-3']);
    });
  });

  describe('Error Handling and Recovery', () => {
    it('should display error state when history loading fails', () => {
      const errorStore = {
        ...mockChatStore,
        historyError: 'Failed to load message history: Network error'
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(errorStore);
      
      renderWithProvider(<ChatHistory threadId="thread-123" />);
      
      expect(screen.getByTestId('history-error')).toBeInTheDocument();
      expect(screen.getByText(/failed to load message history/i)).toBeInTheDocument();
      expect(screen.getByTestId('retry-history-btn')).toBeInTheDocument();
    });

    it('should allow retrying failed history loads', async () => {
      const errorStore = {
        ...mockChatStore,
        historyError: 'Network error'
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(errorStore);
      
      renderWithProvider(<ChatHistory threadId="thread-123" />);
      
      const retryBtn = screen.getByTestId('retry-history-btn');
      await userEvent.click(retryBtn);
      
      expect(mockChatStore.retryLoadHistory).toHaveBeenCalled();
    });

    it('should handle partial load failures', () => {
      const partialErrorStore = {
        ...mockChatStore,
        historyMessages: [
          { id: 'msg-1', content: 'Loaded message', role: 'user' }
        ],
        partialError: 'Some messages could not be loaded'
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(partialErrorStore);
      
      renderWithProvider(<ChatHistory threadId="thread-123" />);
      
      // Should show both loaded messages and partial error
      expect(screen.getByText('Loaded message')).toBeInTheDocument();
      expect(screen.getByTestId('partial-error-warning')).toBeInTheDocument();
      expect(screen.getByText(/some messages could not be loaded/i)).toBeInTheDocument();
    });

    it('should handle offline state gracefully', () => {
      const offlineStore = {
        ...mockChatStore,
        isOffline: true,
        historyMessages: [] // No cached messages
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(offlineStore);
      
      renderWithProvider(<ChatHistory threadId="thread-123" />);
      
      expect(screen.getByTestId('offline-message')).toBeInTheDocument();
      expect(screen.getByText(/offline mode/i)).toBeInTheDocument();
      expect(screen.getByText(/message history unavailable/i)).toBeInTheDocument();
    });

    it('should show cached messages when offline', () => {
      const cachedOfflineStore = {
        ...mockChatStore,
        isOffline: true,
        historyMessages: [
          { id: 'cached-1', content: 'Cached message', role: 'user', cached: true }
        ]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(cachedOfflineStore);
      
      renderWithProvider(<ChatHistory threadId="thread-123" />);
      
      expect(screen.getByText('Cached message')).toBeInTheDocument();
      expect(screen.getByTestId('cached-message-indicator')).toBeInTheDocument();
      expect(screen.getByText(/cached data/i)).toBeInTheDocument();
    });

    it('should handle malformed message data', () => {
      const malformedStore = {
        ...mockChatStore,
        historyMessages: [
          { id: 'msg-1', content: 'Valid message', role: 'user' },
          { id: 'msg-2', content: null, role: 'assistant' }, // Invalid content
          { id: null, content: 'Invalid ID', role: 'user' }, // Invalid ID
          { content: 'Missing ID and role' } // Missing required fields
        ]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(malformedStore);
      
      renderWithProvider(<ChatHistory threadId="thread-123" />);
      
      // Should only show valid message
      expect(screen.getByText('Valid message')).toBeInTheDocument();
      
      // Should show warning about invalid data
      expect(screen.getByTestId('data-validation-warning')).toBeInTheDocument();
    });
  });

  describe('Performance and Virtualization', () => {
    it('should virtualize long message lists for performance', () => {
      const manyMessages = Array.from({ length: 1000 }, (_, i) => ({
        id: `msg-${i}`,
        content: `Message ${i}`,
        role: i % 2 === 0 ? 'user' : 'assistant',
        timestamp: new Date(Date.now() - i * 1000).toISOString()
      }));
      
      const largeHistoryStore = {
        ...mockChatStore,
        historyMessages: manyMessages
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(largeHistoryStore);
      
      renderWithProvider(<ChatHistory threadId="thread-123" />);
      
      // Should render virtualized list
      expect(screen.getByTestId('virtualized-message-list')).toBeInTheDocument();
      
      // Should not render all 1000 messages in DOM
      const renderedMessages = screen.getAllByTestId(/^message-item-/);
      expect(renderedMessages.length).toBeLessThan(100); // Only visible items
    });

    it('should cleanup observers on unmount', () => {
      const { unmount } = renderWithProvider(<ChatHistory threadId="thread-123" />);
      
      const disconnectSpy = jest.spyOn(mockIntersectionObserver.mock.instances[0], 'disconnect');
      
      unmount();
      
      expect(disconnectSpy).toHaveBeenCalled();
    });

    it('should optimize re-renders with message memoization', () => {
      const { rerender } = renderWithProvider(<ChatHistory threadId="thread-123" />);
      
      const stableMessages = [
        { id: 'msg-1', content: 'Stable message', role: 'user' }
      ];
      
      const stableStore = {
        ...mockChatStore,
        historyMessages: stableMessages
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(stableStore);
      
      rerender(
        <WebSocketProvider>
          <ChatHistory threadId="thread-123" />
        </WebSocketProvider>
      );
      
      // Should not re-render messages unnecessarily
      const messageItems = screen.getAllByTestId(/^message-item-/);
      expect(messageItems).toHaveLength(1);
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels and roles', () => {
      const historyStore = {
        ...mockChatStore,
        historyMessages: [
          { id: 'msg-1', content: 'Test message', role: 'user' }
        ]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(historyStore);
      
      renderWithProvider(<ChatHistory threadId="thread-123" />);
      
      const historyRegion = screen.getByRole('region', { name: /message history/i });
      expect(historyRegion).toBeInTheDocument();
      
      const messageList = screen.getByRole('log', { name: /conversation history/i });
      expect(messageList).toBeInTheDocument();
    });

    it('should support keyboard navigation', async () => {
      const historyStore = {
        ...mockChatStore,
        historyMessages: [
          { id: 'msg-1', content: 'First message', role: 'user' },
          { id: 'msg-2', content: 'Second message', role: 'assistant' }
        ]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(historyStore);
      
      renderWithProvider(<ChatHistory threadId="thread-123" />);
      
      const firstMessage = screen.getByTestId('message-item-msg-1');
      firstMessage.focus();
      
      // Navigate with arrow keys
      await userEvent.keyboard('[ArrowDown]');
      expect(screen.getByTestId('message-item-msg-2')).toHaveFocus();
      
      await userEvent.keyboard('[ArrowUp]');
      expect(screen.getByTestId('message-item-msg-1')).toHaveFocus();
    });

    it('should announce dynamic content changes', async () => {
      const { rerender } = renderWithProvider(<ChatHistory threadId="thread-123" />);
      
      const liveRegion = screen.getByRole('status');
      expect(liveRegion).toBeInTheDocument();
      
      // Add new message to history
      const updatedStore = {
        ...mockChatStore,
        historyMessages: [
          { id: 'msg-1', content: 'New message loaded', role: 'user' }
        ]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(updatedStore);
      
      rerender(
        <WebSocketProvider>
          <ChatHistory threadId="thread-123" />
        </WebSocketProvider>
      );
      
      await waitFor(() => {
        expect(liveRegion).toHaveTextContent(/new messages loaded/i);
      });
    });

    it('should provide meaningful alt text for message actions', () => {
      const historyStore = {
        ...mockChatStore,
        historyMessages: [
          { 
            id: 'msg-1', 
            content: 'Test message', 
            role: 'user',
            canDelete: true,
            canEdit: true
          }
        ]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(historyStore);
      
      renderWithProvider(<ChatHistory threadId="thread-123" />);
      
      const messageItem = screen.getByTestId('message-item-msg-1');
      const deleteBtn = within(messageItem).getByLabelText(/delete this message/i);
      const editBtn = within(messageItem).getByLabelText(/edit this message/i);
      
      expect(deleteBtn).toBeInTheDocument();
      expect(editBtn).toBeInTheDocument();
    });
  });
});