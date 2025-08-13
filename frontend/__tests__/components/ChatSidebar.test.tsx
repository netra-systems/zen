import React from 'react';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChatSidebar } from '@/components/chat/ChatSidebar';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useAuthStore } from '@/store/authStore';
import * as ThreadServiceModule from '@/services/threadService';

import { TestProviders } from '../test-utils/providers';

// Mock dependencies
jest.mock('@/store/unified-chat');
jest.mock('@/store/authStore');
jest.mock('@/services/threadService');
jest.mock('@/components/ui/button', () => ({
  Button: ({ children, onClick, variant, size, disabled }: any) => (
    <button onClick={onClick} data-variant={variant} data-size={size} disabled={disabled}>
      {children}
    </button>
  )
}));
jest.mock('@/components/ui/input', () => ({
  Input: ({ value, onChange, placeholder, ...props }: any) => (
    <input
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      {...props}
    />
  )
}));
// Dialog component removed - not used in ChatSidebar

describe('ChatSidebar Component', () => {
  const mockChatStore = {
    isProcessing: false,
    activeThreadId: 'thread-123',
    setActiveThread: jest.fn(),
    clearMessages: jest.fn(),
    resetLayers: jest.fn()
  };

  const mockAuthStore = {
    isDeveloperOrHigher: jest.fn(() => false)
  };

  const mockThreadService = {
    listThreads: jest.fn().mockResolvedValue([]),
    createThread: jest.fn().mockResolvedValue({ id: 'new-thread', created_at: Date.now(), updated_at: Date.now() }),
    getThread: jest.fn(),
    deleteThread: jest.fn(),
    updateThread: jest.fn()
  };

  beforeEach(() => {
    // Mock fetch for config
    global.fetch = jest.fn().mockResolvedValue({
      json: jest.fn().mockResolvedValue({
        ws_url: 'ws://localhost:8000/ws'
      })
    });

    jest.clearAllMocks();
    (useUnifiedChatStore as jest.Mock).mockReturnValue(mockChatStore);
    (useAuthStore as jest.Mock).mockReturnValue(mockAuthStore);
    // Mock ThreadService
    (ThreadServiceModule.ThreadService as any) = mockThreadService;
  });

  const renderWithProvider = (component: React.ReactElement) => {
    return render(
      <TestProviders>
        {component}
      </TestProviders>
    );
  };

  describe('Thread List Display', () => {
    it('should render thread list when threads are available', () => {
      const threadsData = [
        {
          id: 'thread-1',
          title: 'AI Optimization Discussion',
          lastMessage: 'How can I optimize my model?',
          lastActivity: new Date().toISOString(),
          messageCount: 15,
          isActive: false
        },
        {
          id: 'thread-2', 
          title: 'Performance Analysis',
          lastMessage: 'The results show 20% improvement',
          lastActivity: new Date(Date.now() - 3600000).toISOString(), // 1 hour ago
          messageCount: 8,
          isActive: true
        }
      ];
      
      const threadsStore = {
        ...mockChatStore,
        threads: threadsData,
        currentThreadId: 'thread-2'
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(threadsStore);
      
      renderWithProvider(<ChatSidebar />);
      
      expect(screen.getByTestId('thread-list')).toBeInTheDocument();
      expect(screen.getByText('AI Optimization Discussion')).toBeInTheDocument();
      expect(screen.getByText('Performance Analysis')).toBeInTheDocument();
      
      // Active thread should be highlighted
      const activeThread = screen.getByTestId('thread-item-thread-2');
      expect(activeThread).toHaveClass('bg-primary/10', 'border-primary');
    });

    it('should display thread metadata correctly', () => {
      const threadWithMetadata = {
        id: 'thread-1',
        title: 'Test Thread',
        lastMessage: 'Last message content',
        lastActivity: new Date(Date.now() - 1800000).toISOString(), // 30 min ago
        messageCount: 25,
        participants: ['user1', 'assistant'],
        tags: ['optimization', 'performance']
      };
      
      const threadsStore = {
        ...mockChatStore,
        threads: [threadWithMetadata]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(threadsStore);
      
      renderWithProvider(<ChatSidebar />);
      
      const threadItem = screen.getByTestId('thread-item-thread-1');
      
      expect(within(threadItem).getByText('Test Thread')).toBeInTheDocument();
      expect(within(threadItem).getByText('Last message content')).toBeInTheDocument();
      expect(within(threadItem).getByText('25 messages')).toBeInTheDocument();
      expect(within(threadItem).getByText('30m ago')).toBeInTheDocument();
      
      // Tags should be visible
      expect(within(threadItem).getByText('optimization')).toBeInTheDocument();
      expect(within(threadItem).getByText('performance')).toBeInTheDocument();
    });

    it('should show empty state when no threads exist', () => {
      renderWithProvider(<ChatSidebar />);
      
      expect(screen.getByTestId('empty-threads')).toBeInTheDocument();
      expect(screen.getByText(/no conversations yet/i)).toBeInTheDocument();
      expect(screen.getByTestId('create-first-thread-btn')).toBeInTheDocument();
    });

    it('should display loading state while fetching threads', () => {
      const loadingStore = {
        ...mockChatStore,
        isLoadingThreads: true
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(loadingStore);
      
      renderWithProvider(<ChatSidebar />);
      
      expect(screen.getByTestId('threads-loading')).toBeInTheDocument();
      expect(screen.getByText(/loading conversations/i)).toBeInTheDocument();
    });

    it('should show error state when thread loading fails', () => {
      const errorStore = {
        ...mockChatStore,
        threadsError: 'Failed to load threads: Network error'
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(errorStore);
      
      renderWithProvider(<ChatSidebar />);
      
      expect(screen.getByTestId('threads-error')).toBeInTheDocument();
      expect(screen.getByText(/failed to load threads/i)).toBeInTheDocument();
      expect(screen.getByTestId('retry-threads-btn')).toBeInTheDocument();
    });

    it('should group threads by date', () => {
      const groupedThreads = [
        {
          id: 'thread-today',
          title: 'Today Thread',
          lastActivity: new Date().toISOString()
        },
        {
          id: 'thread-yesterday',
          title: 'Yesterday Thread', 
          lastActivity: new Date(Date.now() - 86400000).toISOString() // 24 hours ago
        },
        {
          id: 'thread-last-week',
          title: 'Last Week Thread',
          lastActivity: new Date(Date.now() - 604800000).toISOString() // 7 days ago
        }
      ];
      
      const threadsStore = {
        ...mockChatStore,
        threads: groupedThreads
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(threadsStore);
      
      renderWithProvider(<ChatSidebar />);
      
      expect(screen.getByTestId('date-group-today')).toBeInTheDocument();
      expect(screen.getByTestId('date-group-yesterday')).toBeInTheDocument();
      expect(screen.getByTestId('date-group-older')).toBeInTheDocument();
      
      expect(screen.getByText('Today')).toBeInTheDocument();
      expect(screen.getByText('Yesterday')).toBeInTheDocument();
      expect(screen.getByText('Older')).toBeInTheDocument();
    });

    it('should sort threads by last activity', () => {
      const unsortedThreads = [
        {
          id: 'thread-old',
          title: 'Old Thread',
          lastActivity: new Date(Date.now() - 7200000).toISOString() // 2 hours ago
        },
        {
          id: 'thread-recent',
          title: 'Recent Thread',
          lastActivity: new Date().toISOString() // Now
        },
        {
          id: 'thread-medium',
          title: 'Medium Thread',
          lastActivity: new Date(Date.now() - 3600000).toISOString() // 1 hour ago
        }
      ];
      
      const threadsStore = {
        ...mockChatStore,
        threads: unsortedThreads
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(threadsStore);
      
      renderWithProvider(<ChatSidebar />);
      
      const threadItems = screen.getAllByTestId(/^thread-item-/);
      
      // Should be sorted by most recent first
      expect(within(threadItems[0]).getByText('Recent Thread')).toBeInTheDocument();
      expect(within(threadItems[1]).getByText('Medium Thread')).toBeInTheDocument();
      expect(within(threadItems[2]).getByText('Old Thread')).toBeInTheDocument();
    });

    it('should truncate long thread titles and messages', () => {
      const longContentThread = {
        id: 'thread-1',
        title: 'This is an extremely long thread title that should be truncated when displayed in the sidebar',
        lastMessage: 'This is a very long last message that contains a lot of text and should be truncated to prevent the sidebar from becoming too wide or cluttered with excessive content'
      };
      
      const threadsStore = {
        ...mockChatStore,
        threads: [longContentThread]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(threadsStore);
      
      renderWithProvider(<ChatSidebar />);
      
      const threadItem = screen.getByTestId('thread-item-thread-1');
      const titleElement = within(threadItem).getByTestId('thread-title');
      const messageElement = within(threadItem).getByTestId('thread-last-message');
      
      // Should have truncation styles
      expect(titleElement).toHaveClass('truncate');
      expect(messageElement).toHaveClass('line-clamp-2');
    });

    it('should show thread status indicators', () => {
      const statusThreads = [
        {
          id: 'thread-1',
          title: 'Active Thread',
          status: 'active',
          hasUnreadMessages: true,
          isProcessing: false
        },
        {
          id: 'thread-2',
          title: 'Processing Thread',
          status: 'processing', 
          hasUnreadMessages: false,
          isProcessing: true
        },
        {
          id: 'thread-3',
          title: 'Archived Thread',
          status: 'archived',
          hasUnreadMessages: false,
          isProcessing: false
        }
      ];
      
      const threadsStore = {
        ...mockChatStore,
        threads: statusThreads
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(threadsStore);
      
      renderWithProvider(<ChatSidebar />);
      
      // Unread indicator
      expect(screen.getByTestId('unread-indicator-thread-1')).toBeInTheDocument();
      
      // Processing indicator
      expect(screen.getByTestId('processing-indicator-thread-2')).toBeInTheDocument();
      
      // Archived indicator
      expect(screen.getByTestId('archived-indicator-thread-3')).toBeInTheDocument();
    });
  });

  describe('Thread Navigation and Switching', () => {
    it('should switch to selected thread', async () => {
      const threadsData = [
        { id: 'thread-1', title: 'Thread 1' },
        { id: 'thread-2', title: 'Thread 2' }
      ];
      
      const threadsStore = {
        ...mockChatStore,
        threads: threadsData,
        currentThreadId: 'thread-1'
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(threadsStore);
      
      renderWithProvider(<ChatSidebar />);
      
      const thread2 = screen.getByTestId('thread-item-thread-2');
      await userEvent.click(thread2);
      
      expect(mockChatStore.setCurrentThread).toHaveBeenCalledWith('thread-2');
      expect(mockThreadsHook.switchThread).toHaveBeenCalledWith('thread-2');
    });

    it('should highlight active thread correctly', () => {
      const threadsData = [
        { id: 'thread-1', title: 'Thread 1' },
        { id: 'thread-2', title: 'Thread 2' },
        { id: 'thread-3', title: 'Thread 3' }
      ];
      
      const threadsStore = {
        ...mockChatStore,
        threads: threadsData,
        currentThreadId: 'thread-2'
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(threadsStore);
      
      renderWithProvider(<ChatSidebar />);
      
      const activeThread = screen.getByTestId('thread-item-thread-2');
      const inactiveThread1 = screen.getByTestId('thread-item-thread-1');
      const inactiveThread3 = screen.getByTestId('thread-item-thread-3');
      
      expect(activeThread).toHaveClass('bg-primary/10');
      expect(inactiveThread1).not.toHaveClass('bg-primary/10');
      expect(inactiveThread3).not.toHaveClass('bg-primary/10');
    });

    it('should support keyboard navigation', async () => {
      const threadsData = [
        { id: 'thread-1', title: 'Thread 1' },
        { id: 'thread-2', title: 'Thread 2' },
        { id: 'thread-3', title: 'Thread 3' }
      ];
      
      const threadsStore = {
        ...mockChatStore,
        threads: threadsData,
        currentThreadId: 'thread-1'
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(threadsStore);
      
      renderWithProvider(<ChatSidebar />);
      
      const thread1 = screen.getByTestId('thread-item-thread-1');
      thread1.focus();
      
      // Navigate down
      await userEvent.keyboard('[ArrowDown]');
      expect(screen.getByTestId('thread-item-thread-2')).toHaveFocus();
      
      // Navigate down again
      await userEvent.keyboard('[ArrowDown]');
      expect(screen.getByTestId('thread-item-thread-3')).toHaveFocus();
      
      // Navigate back up
      await userEvent.keyboard('[ArrowUp]');
      expect(screen.getByTestId('thread-item-thread-2')).toHaveFocus();
      
      // Select with Enter
      await userEvent.keyboard('[Enter]');
      expect(mockChatStore.setCurrentThread).toHaveBeenCalledWith('thread-2');
    });

    it('should show thread preview on hover', async () => {
      const threadWithPreview = {
        id: 'thread-1',
        title: 'Thread with Preview',
        lastMessage: 'Preview message',
        messageCount: 10,
        participants: ['user', 'assistant'],
        createdAt: new Date().toISOString()
      };
      
      const threadsStore = {
        ...mockChatStore,
        threads: [threadWithPreview]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(threadsStore);
      
      renderWithProvider(<ChatSidebar />);
      
      const threadItem = screen.getByTestId('thread-item-thread-1');
      await userEvent.hover(threadItem);
      
      await waitFor(() => {
        expect(screen.getByTestId('thread-preview-tooltip')).toBeInTheDocument();
        expect(screen.getByText('10 messages')).toBeInTheDocument();
        expect(screen.getByText('2 participants')).toBeInTheDocument();
      });
    });

    it('should handle rapid thread switching', async () => {
      const threadsData = [
        { id: 'thread-1', title: 'Thread 1' },
        { id: 'thread-2', title: 'Thread 2' },
        { id: 'thread-3', title: 'Thread 3' }
      ];
      
      const threadsStore = {
        ...mockChatStore,
        threads: threadsData
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(threadsStore);
      
      renderWithProvider(<ChatSidebar />);
      
      // Rapidly click different threads
      await userEvent.click(screen.getByTestId('thread-item-thread-1'));
      await userEvent.click(screen.getByTestId('thread-item-thread-2'));
      await userEvent.click(screen.getByTestId('thread-item-thread-3'));
      
      // Should handle all switches
      expect(mockChatStore.setCurrentThread).toHaveBeenCalledTimes(3);
      expect(mockChatStore.setCurrentThread).toHaveBeenLastCalledWith('thread-3');
    });

    it('should persist navigation state across page reloads', () => {
      // Mock localStorage
      const mockStorage = {
        getItem: jest.fn().mockReturnValue('thread-2'),
        setItem: jest.fn()
      };
      Object.defineProperty(window, 'localStorage', { value: mockStorage });
      
      const threadsData = [
        { id: 'thread-1', title: 'Thread 1' },
        { id: 'thread-2', title: 'Thread 2' }
      ];
      
      const threadsStore = {
        ...mockChatStore,
        threads: threadsData,
        currentThreadId: null // Initially null
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(threadsStore);
      
      renderWithProvider(<ChatSidebar />);
      
      // Should restore from localStorage
      expect(mockStorage.getItem).toHaveBeenCalledWith('currentThreadId');
    });
  });

  describe('Thread Management Operations', () => {
    it('should create new thread', async () => {
      renderWithProvider(<ChatSidebar />);
      
      const newThreadBtn = screen.getByTestId('new-thread-btn');
      await userEvent.click(newThreadBtn);
      
      expect(mockChatStore.createNewThread).toHaveBeenCalled();
      expect(mockThreadsHook.createThread).toHaveBeenCalled();
    });

    it('should show thread creation dialog', async () => {
      renderWithProvider(<ChatSidebar />);
      
      const newThreadBtn = screen.getByTestId('new-thread-btn');
      await userEvent.click(newThreadBtn);
      
      expect(screen.getByTestId('dialog')).toBeInTheDocument();
      expect(screen.getByTestId('dialog-title')).toHaveTextContent(/new conversation/i);
      
      const titleInput = screen.getByTestId('thread-title-input');
      const createBtn = screen.getByTestId('create-thread-btn');
      
      await userEvent.type(titleInput, 'New Thread Title');
      await userEvent.click(createBtn);
      
      expect(mockThreadsHook.createThread).toHaveBeenCalledWith({
        title: 'New Thread Title'
      });
    });

    it('should rename existing thread', async () => {
      const renamableThread = {
        id: 'thread-1',
        title: 'Old Title',
        canEdit: true
      };
      
      const threadsStore = {
        ...mockChatStore,
        threads: [renamableThread]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(threadsStore);
      
      renderWithProvider(<ChatSidebar />);
      
      const threadItem = screen.getByTestId('thread-item-thread-1');
      
      // Right-click to open context menu
      await userEvent.pointer([{ target: threadItem, keys: '[MouseRight]' }]);
      
      const renameOption = screen.getByTestId('rename-thread-option');
      await userEvent.click(renameOption);
      
      expect(screen.getByTestId('rename-dialog')).toBeInTheDocument();
      
      const renameInput = screen.getByTestId('rename-input');
      expect(renameInput).toHaveValue('Old Title');
      
      await userEvent.clear(renameInput);
      await userEvent.type(renameInput, 'New Title');
      
      const saveBtn = screen.getByTestId('save-rename-btn');
      await userEvent.click(saveBtn);
      
      expect(mockChatStore.updateThread).toHaveBeenCalledWith('thread-1', {
        title: 'New Title'
      });
    });

    it('should delete thread with confirmation', async () => {
      const deletableThread = {
        id: 'thread-1',
        title: 'Deletable Thread',
        canDelete: true
      };
      
      const threadsStore = {
        ...mockChatStore,
        threads: [deletableThread]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(threadsStore);
      
      renderWithProvider(<ChatSidebar />);
      
      const threadItem = screen.getByTestId('thread-item-thread-1');
      
      // Right-click for context menu
      await userEvent.pointer([{ target: threadItem, keys: '[MouseRight]' }]);
      
      const deleteOption = screen.getByTestId('delete-thread-option');
      await userEvent.click(deleteOption);
      
      // Should show confirmation dialog
      expect(screen.getByTestId('delete-confirmation')).toBeInTheDocument();
      expect(screen.getByText(/delete conversation/i)).toBeInTheDocument();
      expect(screen.getByText(/this action cannot be undone/i)).toBeInTheDocument();
      
      const confirmBtn = screen.getByTestId('confirm-delete-btn');
      await userEvent.click(confirmBtn);
      
      expect(mockChatStore.deleteThread).toHaveBeenCalledWith('thread-1');
      expect(mockThreadsHook.deleteThread).toHaveBeenCalledWith('thread-1');
    });

    it('should archive and unarchive threads', async () => {
      const archivableThread = {
        id: 'thread-1',
        title: 'Archivable Thread',
        isArchived: false,
        canArchive: true
      };
      
      const threadsStore = {
        ...mockChatStore,
        threads: [archivableThread]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(threadsStore);
      
      renderWithProvider(<ChatSidebar />);
      
      const threadItem = screen.getByTestId('thread-item-thread-1');
      await userEvent.pointer([{ target: threadItem, keys: '[MouseRight]' }]);
      
      const archiveOption = screen.getByTestId('archive-thread-option');
      await userEvent.click(archiveOption);
      
      expect(mockChatStore.updateThread).toHaveBeenCalledWith('thread-1', {
        isArchived: true
      });
    });

    it('should handle bulk thread operations', async () => {
      const bulkThreads = [
        { id: 'thread-1', title: 'Thread 1', canDelete: true },
        { id: 'thread-2', title: 'Thread 2', canDelete: true },
        { id: 'thread-3', title: 'Thread 3', canDelete: true }
      ];
      
      const threadsStore = {
        ...mockChatStore,
        threads: bulkThreads,
        deleteThreads: jest.fn()
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(threadsStore);
      
      renderWithProvider(<ChatSidebar />);
      
      // Enter selection mode
      const selectionModeBtn = screen.getByTestId('selection-mode-btn');
      await userEvent.click(selectionModeBtn);
      
      // Select multiple threads
      const thread1 = screen.getByTestId('thread-checkbox-thread-1');
      const thread2 = screen.getByTestId('thread-checkbox-thread-2');
      
      await userEvent.click(thread1);
      await userEvent.click(thread2);
      
      // Bulk delete
      const bulkDeleteBtn = screen.getByTestId('bulk-delete-btn');
      await userEvent.click(bulkDeleteBtn);
      
      const confirmBtn = screen.getByTestId('confirm-bulk-delete');
      await userEvent.click(confirmBtn);
      
      expect(threadsStore.deleteThreads).toHaveBeenCalledWith(['thread-1', 'thread-2']);
    });

    it('should export thread data', async () => {
      const exportableThread = {
        id: 'thread-1',
        title: 'Exportable Thread',
        canExport: true
      };
      
      const threadsStore = {
        ...mockChatStore,
        threads: [exportableThread],
        exportThread: jest.fn()
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(threadsStore);
      
      renderWithProvider(<ChatSidebar />);
      
      const threadItem = screen.getByTestId('thread-item-thread-1');
      await userEvent.pointer([{ target: threadItem, keys: '[MouseRight]' }]);
      
      const exportOption = screen.getByTestId('export-thread-option');
      await userEvent.click(exportOption);
      
      expect(threadsStore.exportThread).toHaveBeenCalledWith('thread-1');
    });
  });

  describe('Thread Search and Filtering', () => {
    it('should provide search functionality', async () => {
      const searchableThreads = [
        { id: 'thread-1', title: 'AI Optimization', lastMessage: 'Model performance' },
        { id: 'thread-2', title: 'Data Analysis', lastMessage: 'Statistical insights' },
        { id: 'thread-3', title: 'Performance Tuning', lastMessage: 'Optimization strategies' }
      ];
      
      const threadsStore = {
        ...mockChatStore,
        threads: searchableThreads
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(threadsStore);
      
      renderWithProvider(<ChatSidebar />);
      
      const searchInput = screen.getByTestId('thread-search-input');
      await userEvent.type(searchInput, 'optimization');
      
      expect(mockChatStore.searchThreads).toHaveBeenCalledWith('optimization');
    });

    it('should filter threads based on search query', () => {
      const searchStore = {
        ...mockChatStore,
        threads: [
          { id: 'thread-1', title: 'AI Optimization', lastMessage: 'Model performance' }
        ],
        searchQuery: 'optimization',
        filteredThreads: [
          { id: 'thread-1', title: 'AI Optimization', lastMessage: 'Model performance' }
        ]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(searchStore);
      
      renderWithProvider(<ChatSidebar />);
      
      expect(screen.getByText('AI Optimization')).toBeInTheDocument();
      expect(screen.getByTestId('search-results-count')).toHaveTextContent('1 result');
    });

    it('should clear search results', async () => {
      const searchStore = {
        ...mockChatStore,
        searchQuery: 'test query',
        filteredThreads: [],
        clearSearch: jest.fn()
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(searchStore);
      
      renderWithProvider(<ChatSidebar />);
      
      const clearButton = screen.getByTestId('clear-search-btn');
      await userEvent.click(clearButton);
      
      expect(searchStore.clearSearch).toHaveBeenCalled();
    });

    it('should filter by thread status', async () => {
      const statusThreads = [
        { id: 'thread-1', title: 'Active Thread', status: 'active' },
        { id: 'thread-2', title: 'Archived Thread', status: 'archived' },
        { id: 'thread-3', title: 'Draft Thread', status: 'draft' }
      ];
      
      const threadsStore = {
        ...mockChatStore,
        threads: statusThreads
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(threadsStore);
      
      renderWithProvider(<ChatSidebar />);
      
      const statusFilter = screen.getByTestId('status-filter');
      await userEvent.click(statusFilter);
      
      const archivedOption = screen.getByText('Archived');
      await userEvent.click(archivedOption);
      
      // Should only show archived threads
      expect(screen.getByText('Archived Thread')).toBeInTheDocument();
      expect(screen.queryByText('Active Thread')).not.toBeInTheDocument();
      expect(screen.queryByText('Draft Thread')).not.toBeInTheDocument();
    });

    it('should filter by date range', async () => {
      const datedThreads = [
        {
          id: 'thread-recent',
          title: 'Recent Thread',
          lastActivity: new Date().toISOString()
        },
        {
          id: 'thread-old',
          title: 'Old Thread',
          lastActivity: new Date(Date.now() - 2592000000).toISOString() // 30 days ago
        }
      ];
      
      const threadsStore = {
        ...mockChatStore,
        threads: datedThreads
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(threadsStore);
      
      renderWithProvider(<ChatSidebar />);
      
      const dateFilter = screen.getByTestId('date-filter');
      await userEvent.click(dateFilter);
      
      const lastWeekOption = screen.getByText('Last week');
      await userEvent.click(lastWeekOption);
      
      // Should only show recent thread
      expect(screen.getByText('Recent Thread')).toBeInTheDocument();
      expect(screen.queryByText('Old Thread')).not.toBeInTheDocument();
    });

    it('should support advanced search with filters', async () => {
      renderWithProvider(<ChatSidebar />);
      
      const advancedSearchBtn = screen.getByTestId('advanced-search-btn');
      await userEvent.click(advancedSearchBtn);
      
      expect(screen.getByTestId('advanced-search-dialog')).toBeInTheDocument();
      
      const titleFilter = screen.getByTestId('search-title-input');
      const messageFilter = screen.getByTestId('search-message-input');
      const participantFilter = screen.getByTestId('search-participant-input');
      
      await userEvent.type(titleFilter, 'optimization');
      await userEvent.type(messageFilter, 'performance');
      await userEvent.type(participantFilter, 'assistant');
      
      const searchBtn = screen.getByTestId('advanced-search-submit');
      await userEvent.click(searchBtn);
      
      expect(mockChatStore.searchThreads).toHaveBeenCalledWith({
        title: 'optimization',
        message: 'performance',
        participant: 'assistant'
      });
    });

    it('should show search suggestions', async () => {
      const suggestionsStore = {
        ...mockChatStore,
        searchSuggestions: [
          'AI optimization',
          'Performance tuning',
          'Model training'
        ]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(suggestionsStore);
      
      renderWithProvider(<ChatSidebar />);
      
      const searchInput = screen.getByTestId('thread-search-input');
      await userEvent.click(searchInput);
      
      expect(screen.getByTestId('search-suggestions')).toBeInTheDocument();
      expect(screen.getByText('AI optimization')).toBeInTheDocument();
      expect(screen.getByText('Performance tuning')).toBeInTheDocument();
      expect(screen.getByText('Model training')).toBeInTheDocument();
    });
  });

  describe('Error Handling and Recovery', () => {
    it('should handle thread switching failures', async () => {
      const threadsData = [
        { id: 'thread-1', title: 'Thread 1' },
        { id: 'thread-2', title: 'Thread 2' }
      ];
      
      const threadsStore = {
        ...mockChatStore,
        threads: threadsData
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(threadsStore);
      mockChatStore.setCurrentThread.mockRejectedValueOnce(new Error('Switch failed'));
      
      renderWithProvider(<ChatSidebar />);
      
      const thread2 = screen.getByTestId('thread-item-thread-2');
      await userEvent.click(thread2);
      
      await waitFor(() => {
        expect(screen.getByTestId('switch-error-toast')).toBeInTheDocument();
        expect(screen.getByText(/failed to switch thread/i)).toBeInTheDocument();
      });
    });

    it('should retry failed operations', async () => {
      const errorStore = {
        ...mockChatStore,
        threadsError: 'Failed to load threads'
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(errorStore);
      
      renderWithProvider(<ChatSidebar />);
      
      const retryBtn = screen.getByTestId('retry-threads-btn');
      await userEvent.click(retryBtn);
      
      expect(mockChatStore.loadThreads).toHaveBeenCalled();
    });

    it('should handle network disconnection gracefully', () => {
      const offlineStore = {
        ...mockChatStore,
        isOffline: true,
        threads: [
          { id: 'cached-1', title: 'Cached Thread', cached: true }
        ]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(offlineStore);
      
      renderWithProvider(<ChatSidebar />);
      
      expect(screen.getByTestId('offline-indicator')).toBeInTheDocument();
      expect(screen.getByText(/offline mode/i)).toBeInTheDocument();
      
      // Should show cached threads
      expect(screen.getByText('Cached Thread')).toBeInTheDocument();
      expect(screen.getByTestId('cached-indicator')).toBeInTheDocument();
    });

    it('should handle partial load failures', () => {
      const partialErrorStore = {
        ...mockChatStore,
        threads: [
          { id: 'thread-1', title: 'Loaded Thread' }
        ],
        partialLoadError: 'Some threads could not be loaded'
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(partialErrorStore);
      
      renderWithProvider(<ChatSidebar />);
      
      expect(screen.getByText('Loaded Thread')).toBeInTheDocument();
      expect(screen.getByTestId('partial-error-warning')).toBeInTheDocument();
      expect(screen.getByText(/some threads could not be loaded/i)).toBeInTheDocument();
    });
  });

  describe('Performance and Optimization', () => {
    it('should virtualize large thread lists', () => {
      const manyThreads = Array.from({ length: 1000 }, (_, i) => ({
        id: `thread-${i}`,
        title: `Thread ${i}`,
        lastActivity: new Date(Date.now() - i * 1000).toISOString()
      }));
      
      const largeThreadsStore = {
        ...mockChatStore,
        threads: manyThreads
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(largeThreadsStore);
      
      renderWithProvider(<ChatSidebar />);
      
      expect(screen.getByTestId('virtualized-thread-list')).toBeInTheDocument();
      
      // Should not render all 1000 threads in DOM
      const renderedThreads = screen.getAllByTestId(/^thread-item-/);
      expect(renderedThreads.length).toBeLessThan(100);
    });

    it('should debounce search input', async () => {
      jest.useFakeTimers();
      
      renderWithProvider(<ChatSidebar />);
      
      const searchInput = screen.getByTestId('thread-search-input');
      
      await userEvent.type(searchInput, 'search query');
      
      // Should not search immediately
      expect(mockChatStore.searchThreads).not.toHaveBeenCalled();
      
      // Fast-forward debounce delay
      jest.advanceTimersByTime(300);
      
      await waitFor(() => {
        expect(mockChatStore.searchThreads).toHaveBeenCalledWith('search query');
      });
      
      jest.useRealTimers();
    });

    it('should cleanup listeners on unmount', () => {
      const { unmount } = renderWithProvider(<ChatSidebar />);
      
      const removeEventListenerSpy = jest.spyOn(document, 'removeEventListener');
      
      unmount();
      
      expect(removeEventListenerSpy).toHaveBeenCalled();
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels and roles', () => {
      const threadsData = [
        { id: 'thread-1', title: 'Test Thread' }
      ];
      
      const threadsStore = {
        ...mockChatStore,
        threads: threadsData,
        currentThreadId: 'thread-1'
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(threadsStore);
      
      renderWithProvider(<ChatSidebar />);
      
      const sidebar = screen.getByRole('navigation', { name: /thread navigation/i });
      expect(sidebar).toBeInTheDocument();
      
      const threadList = screen.getByRole('list', { name: /conversation list/i });
      expect(threadList).toBeInTheDocument();
      
      const activeThread = screen.getByRole('listitem', { name: /test thread.*active/i });
      expect(activeThread).toHaveAttribute('aria-current', 'page');
    });

    it('should support screen reader announcements', async () => {
      const { rerender } = renderWithProvider(<ChatSidebar />);
      
      const statusRegion = screen.getByRole('status');
      expect(statusRegion).toBeInTheDocument();
      
      // Simulate thread switch
      const updatedStore = {
        ...mockChatStore,
        currentThreadId: 'thread-2',
        threads: [
          { id: 'thread-1', title: 'Thread 1' },
          { id: 'thread-2', title: 'Thread 2' }
        ]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(updatedStore);
      rerender(
        <WebSocketProvider>
          <ChatSidebar />
        </WebSocketProvider>
      );
      
      await waitFor(() => {
        expect(statusRegion).toHaveTextContent(/switched to thread 2/i);
      });
    });

    it('should support high contrast mode', () => {
      // Mock high contrast media query
      const matchMediaSpy = jest.spyOn(window, 'matchMedia').mockReturnValue({
        matches: true,
        addEventListener: jest.fn(),
        removeEventListener: jest.fn()
      } as any);
      
      const threadsStore = {
        ...mockChatStore,
        threads: [{ id: 'thread-1', title: 'Test Thread' }],
        currentThreadId: 'thread-1'
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(threadsStore);
      
      renderWithProvider(<ChatSidebar />);
      
      const activeThread = screen.getByTestId('thread-item-thread-1');
      expect(activeThread).toHaveClass('high-contrast-active');
      
      matchMediaSpy.mockRestore();
    });

    it('should provide keyboard shortcuts info', async () => {
      renderWithProvider(<ChatSidebar />);
      
      // Open keyboard shortcuts help
      await userEvent.keyboard('[?]');
      
      expect(screen.getByTestId('keyboard-shortcuts-dialog')).toBeInTheDocument();
      expect(screen.getByText(/keyboard shortcuts/i)).toBeInTheDocument();
      expect(screen.getByText('Ctrl+N: New thread')).toBeInTheDocument();
      expect(screen.getByText('Ctrl+F: Search threads')).toBeInTheDocument();
    });
  });
});