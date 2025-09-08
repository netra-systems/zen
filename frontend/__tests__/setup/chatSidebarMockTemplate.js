// Comprehensive ChatSidebar Mock Template
// Use this template to fix "Element type is invalid" errors when testing components that use ChatSidebar

// Mock all ChatSidebar dependencies to prevent "Element type is invalid" errors
const chatSidebarMocks = `
jest.mock('@/store/authStore', () => ({
  useAuthStore: () => ({
    isDeveloperOrHigher: () => false
  })
}));

jest.mock('@/hooks/useAuthState', () => ({
  useAuthState: () => ({
    isAuthenticated: true,
    userTier: 'Free',
    user: { id: 'test-user', email: 'test@test.com' }
  })
}));

jest.mock('@/components/auth/AuthGate', () => ({
  AuthGate: ({ children }) => children
}));

jest.mock('@/hooks/useThreadSwitching', () => ({
  useThreadSwitching: () => ({
    switchToThread: jest.fn(),
    state: { isLoading: false, error: null }
  })
}));

jest.mock('@/lib/thread-operation-manager', () => ({
  ThreadOperationManager: {
    executeWithRetry: jest.fn().mockResolvedValue({ success: true }),
    switchToThread: jest.fn().mockResolvedValue(true),
    startOperation: jest.fn().mockImplementation(async (operation, threadId, callback) => {
      const result = await callback();
      return result;
    }),
    isOperationInProgress: jest.fn().mockReturnValue(false)
  }
}));

jest.mock('@/lib/thread-state-machine', () => ({
  threadStateMachineManager: {
    transition: jest.fn(),
    getState: jest.fn().mockReturnValue('IDLE'),
    getStateMachine: jest.fn().mockReturnValue({
      canTransition: jest.fn().mockReturnValue(true),
      transition: jest.fn()
    })
  }
}));

jest.mock('@/lib/logger', () => ({
  logger: {
    info: jest.fn(),
    error: jest.fn(),
    debug: jest.fn(),
    warn: jest.fn()
  }
}));

jest.mock('@/components/chat/ChatSidebarUIComponents', () => ({
  NewChatButton: ({ onNewChat }) => React.createElement('button', { onClick: onNewChat, 'data-testid': 'new-chat-button' }, 'New Chat'),
  AdminControls: () => React.createElement('div', { 'data-testid': 'admin-controls' }, 'Admin Controls'),
  SearchBar: ({ onSearchChange }) => React.createElement('input', { onChange: (e) => onSearchChange(e.target.value), 'data-testid': 'search-bar' })
}));

jest.mock('@/components/chat/ChatSidebarThreadList', () => ({
  ThreadList: ({ threads, onThreadClick }) => React.createElement('div', { 'data-testid': 'thread-list' },
    threads && threads.map((thread) => React.createElement('button', {
      key: thread.id,
      onClick: () => onThreadClick && onThreadClick(thread.id),
      'data-testid': \`thread-item-\${thread.id}\`
    }, thread.title))
  ),
  ThreadItem: ({ thread, onClick }) => React.createElement('button', {
    onClick: () => onClick && onClick(),
    'data-testid': \`thread-item-\${thread.id}\`
  }, thread.title)
}));

jest.mock('@/components/chat/ChatSidebarFooter', () => ({
  PaginationControls: () => React.createElement('div', { 'data-testid': 'pagination' }, 'Pagination'),
  Footer: () => React.createElement('div', { 'data-testid': 'footer' }, 'Footer')
}));

jest.mock('@/components/chat/ChatSidebarHooks', () => ({
  useChatSidebarState: () => ({
    searchQuery: '',
    setSearchQuery: jest.fn(),
    isCreatingThread: false,
    setIsCreatingThread: jest.fn(),
    showAllThreads: false,
    setShowAllThreads: jest.fn(),
    filterType: 'all',
    setFilterType: jest.fn(),
    currentPage: 1,
    setCurrentPage: jest.fn(),
    threadsPerPage: 20,
    isAdmin: false
  }),
  useThreadLoader: () => ({
    threads: [],
    isLoadingThreads: false,
    loadError: null,
    loadThreads: jest.fn()
  }),
  useThreadFiltering: (threads) => ({
    sortedThreads: threads || [],
    paginatedThreads: threads || [],
    totalPages: 1
  })
}));

jest.mock('@/services/threadLoadingService', () => ({
  threadLoadingService: {
    loadThread: jest.fn().mockResolvedValue({
      success: true,
      messages: [],
      threadId: 'test-thread'
    })
  }
}));

jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: () => ({
    sendMessage: jest.fn(),
    isConnected: true
  })
}));
`;

module.exports = { chatSidebarMocks };