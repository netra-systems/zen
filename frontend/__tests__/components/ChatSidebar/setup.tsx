/**
 * ChatSidebar Test Setup and Utilities
 * Shared setup, mocks, and utilities for ChatSidebar component tests
 */

import React from 'react';
import { render } from '@testing-library/react';
import '@testing-library/jest-dom';

import { useUnifiedChatStore } from '@/store/unified-chat';
import { useAuthStore } from '@/store/authStore';
import { useAuthState } from '@/hooks/useAuthState';
import { useWebSocket } from '@/hooks/useWebSocket';
import * as ChatSidebarHooksModule from '@/components/chat/ChatSidebarHooks';
import * as ThreadServiceModule from '@/services/threadService';
import { TestProviders } from '../../test-utils/providers';

// Mock dependencies - Single declarations only
jest.mock('@/store/unified-chat');
jest.mock('@/store/authStore');
jest.mock('@/hooks/useAuthState');

// Mock AuthGate with proper authentication logic - CRITICAL
jest.mock('@/components/auth/AuthGate', () => ({
  AuthGate: ({ 
    children, 
    fallback, 
    showLoginPrompt = true, 
    requireTier, 
    customMessage 
  }: { 
    children: React.ReactNode; 
    fallback?: React.ReactNode; 
    showLoginPrompt?: boolean; 
    requireTier?: 'Early' | 'Mid' | 'Enterprise';
    customMessage?: string;
  }) => {
    // Use the mocked useAuthState hook to get authentication status
    const { useAuthState } = require('@/hooks/useAuthState');
    const { isAuthenticated, isLoading, userTier } = useAuthState();
    
    console.log('AuthGate mock called', { 
      isAuthenticated, 
      isLoading, 
      userTier, 
      requireTier, 
      hasFallback: !!fallback 
    });

    // Show loading state during auth check
    if (isLoading) {
      return <div data-testid="auth-loading">Verifying access...</div>;
    }

    // Show fallback for unauthenticated users
    if (!isAuthenticated) {
      if (fallback) return <div data-testid="auth-fallback">{fallback}</div>;
      if (!showLoginPrompt) return null;
      return <div data-testid="login-prompt">Login Required</div>;
    }

    // Check tier requirements
    if (requireTier) {
      const tierLevels = { Free: 0, Early: 1, Mid: 2, Enterprise: 3 };
      const current = tierLevels[userTier as keyof typeof tierLevels] || 0;
      const required = tierLevels[requireTier as keyof typeof tierLevels] || 0;
      
      if (current < required) {
        return (
          <div data-testid="tier-upgrade">
            Upgrade to {requireTier} required (current: {userTier})
          </div>
        );
      }
    }

    // Render authenticated content
    return <div data-testid="mocked-authgate">{children}</div>;
  }
}));

// Mock WebSocket hook
jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: jest.fn(() => ({
    sendMessage: jest.fn(),
    isConnected: true,
    connectionStatus: 'connected'
  }))
}));

// Mock ChatSidebar hooks with debugging - CRITICAL: Use exact same path as component import
jest.mock('@/components/chat/ChatSidebarHooks', () => {
  console.log('📦 ChatSidebarHooks module mock created');
  return {
    useChatSidebarState: jest.fn(() => {
      console.log('🔥 HOOK CALLED: useChatSidebarState (DEFAULT)');
      return {
        searchQuery: '',
        setSearchQuery: jest.fn(),
        isCreatingThread: false,
        setIsCreatingThread: jest.fn(),
        showAllThreads: false,
        setShowAllThreads: jest.fn(),
        filterType: 'all' as const,
        setFilterType: jest.fn(),
        currentPage: 1,
        setCurrentPage: jest.fn()
      };
    }),
    useThreadLoader: jest.fn(() => {
      console.log('🔥 HOOK CALLED: useThreadLoader (DEFAULT)');
      return {
        threads: [], // CRITICAL: Always return array, never undefined/null
        isLoadingThreads: false,  // Fixed: Default to false for tests
        loadError: null,
        loadThreads: jest.fn()
      };
    }),
    useThreadFiltering: jest.fn((threads, searchQuery, threadsPerPage, currentPage) => {
      console.log('🔥 HOOK CALLED: useThreadFiltering (DEFAULT)', { 
        threadsType: typeof threads, 
        isArray: Array.isArray(threads), 
        threadsLength: threads?.length 
      });
      // CRITICAL: Ensure threads is always an array to prevent filter errors
      const safeThreads = Array.isArray(threads) ? threads : [];
      return {
        sortedThreads: safeThreads,
        paginatedThreads: safeThreads,
        totalPages: Math.max(1, Math.ceil(safeThreads.length / (threadsPerPage || 50)))
      };
    })
  };
});

// Mock ThreadService
jest.mock('@/services/threadService', () => ({
  ThreadService: {
    listThreads: jest.fn().mockResolvedValue([]),
    createThread: jest.fn().mockResolvedValue({ 
      id: 'new-thread', 
      created_at: Math.floor(Date.now() / 1000), 
      updated_at: Math.floor(Date.now() / 1000),
      message_count: 0
    }),
    getThread: jest.fn(),
    deleteThread: jest.fn(),
    updateThread: jest.fn(),
    getThreadMessages: jest.fn().mockResolvedValue({ messages: [], thread_id: 'test', total: 0, limit: 50, offset: 0 })
  }
}));

// Mock UI components
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

export const mockChatStore = {
  isProcessing: false,
  activeThreadId: 'thread-123',
  setActiveThread: jest.fn(),
  clearMessages: jest.fn(),
  resetLayers: jest.fn(),
  threads: [] as any[],
  currentThreadId: null as string | null,
};

export const mockAuthStore = {
  isDeveloperOrHigher: jest.fn(() => false),
  isAuthenticated: true,
  user: {
    id: 'test-user-1',
    email: 'test@example.com',
    role: 'user'
  },
  hasPermission: jest.fn(() => true),
  isAdminOrHigher: jest.fn(() => false)
};

export const mockAuthState = {
  isAuthenticated: true,
  isLoading: false,
  user: {
    id: 'test-user-1',
    email: 'test@example.com',
    role: 'user'
  },
  userTier: 'Early' as const,
  error: null,
  refreshAuth: jest.fn(),
  logout: jest.fn(),
  clearError: jest.fn(),
  hasPermission: jest.fn(() => true),
  isAdminOrHigher: jest.fn(() => false),
  isDeveloperOrHigher: jest.fn(() => false)
};

export const mockWebSocket = {
  sendMessage: jest.fn(),
  isConnected: true,
  connectionStatus: 'connected'
};

export const mockChatSidebarHooks = {
  useChatSidebarState: jest.fn(() => ({
    searchQuery: '',
    setSearchQuery: jest.fn(),
    isCreatingThread: false,
    setIsCreatingThread: jest.fn(),
    showAllThreads: false,
    setShowAllThreads: jest.fn(),
    filterType: 'all' as const,
    setFilterType: jest.fn(),
    currentPage: 1,
    setCurrentPage: jest.fn()
  })),
  useThreadLoader: jest.fn(() => ({
    threads: [], // CRITICAL: Always return array
    isLoadingThreads: false,
    loadError: null,
    loadThreads: jest.fn()
  })),
  useThreadFiltering: jest.fn((threads, searchQuery, threadsPerPage, currentPage) => {
    // CRITICAL: Ensure threads is always an array to prevent filter errors
    const safeThreads = Array.isArray(threads) ? threads : [];
    return {
      sortedThreads: safeThreads,
      paginatedThreads: safeThreads,
      totalPages: Math.max(1, Math.ceil(safeThreads.length / (threadsPerPage || 50)))
    };
  })
};

export const mockThreadService = {
  listThreads: jest.fn().mockResolvedValue([]),
  createThread: jest.fn().mockResolvedValue({ 
    id: 'new-thread', 
    created_at: Date.now(), 
    updated_at: Date.now() 
  }),
  getThread: jest.fn(),
  deleteThread: jest.fn(),
  updateThread: jest.fn()
};

// Sample thread data matching Thread interface from threadService
export const sampleThreads = [
  {
    id: 'thread-1',
    title: 'AI Optimization Discussion',
    created_at: Math.floor(Date.now() / 1000),
    updated_at: Math.floor(Date.now() / 1000),
    message_count: 15,
    metadata: {
      title: 'AI Optimization Discussion',
      last_message: 'How can I optimize my model?',
      lastActivity: new Date().toISOString(),
      messageCount: 15,
      tags: ['optimization', 'ai']
    }
  },
  {
    id: 'thread-2', 
    title: 'Performance Analysis',
    created_at: Math.floor((Date.now() - 3600000) / 1000), // 1 hour ago
    updated_at: Math.floor((Date.now() - 3600000) / 1000),
    message_count: 8,
    metadata: {
      title: 'Performance Analysis',
      last_message: 'The results show 20% improvement',
      lastActivity: new Date(Date.now() - 3600000).toISOString(),
      messageCount: 8,
      tags: ['performance']
    }
  },
  {
    id: 'thread-3',
    title: 'Data Processing Pipeline',
    created_at: Math.floor((Date.now() - 7200000) / 1000), // 2 hours ago
    updated_at: Math.floor((Date.now() - 7200000) / 1000),
    message_count: 32,
    metadata: {
      title: 'Data Processing Pipeline',
      last_message: 'Pipeline completed successfully',
      lastActivity: new Date(Date.now() - 7200000).toISOString(),
      messageCount: 32,
      tags: ['data', 'pipeline']
    }
  }
];

export class ChatSidebarTestSetup {
  beforeEach() {
    // Mock fetch for config
    global.fetch = jest.fn().mockResolvedValue({
      json: jest.fn().mockResolvedValue({
        ws_url: 'ws://localhost:8000/ws'
      })
    });

    // CRITICAL: Clear mocks FIRST, then configure them
    // This ensures our configurations aren't cleared
    jest.clearAllMocks();
    
    // Configure authentication FIRST - critical for AuthGate mock
    console.log('🔧 Configuring authentication mocks with:', { 
      isAuthenticated: mockAuthState.isAuthenticated, 
      userTier: mockAuthState.userTier 
    });
    (useAuthState as jest.Mock).mockReturnValue(mockAuthState);
    (useAuthStore as jest.Mock).mockReturnValue(mockAuthStore);
    
    // Configure other store mocks
    (useUnifiedChatStore as jest.Mock).mockReturnValue(mockChatStore);
    
    // CRITICAL: Reset ChatSidebar hooks to default empty state
    // This ensures clean state before each test - use mockReset then mockReturnValue
    (ChatSidebarHooksModule.useChatSidebarState as jest.Mock).mockReset().mockReturnValue({
      searchQuery: '',
      setSearchQuery: jest.fn(),
      isCreatingThread: false,
      setIsCreatingThread: jest.fn(),
      showAllThreads: false,
      setShowAllThreads: jest.fn(),
      filterType: 'all' as const,
      setFilterType: jest.fn(),
      currentPage: 1,
      setCurrentPage: jest.fn()
    });
    
    (ChatSidebarHooksModule.useThreadLoader as jest.Mock).mockReset().mockReturnValue({
      threads: [], // CRITICAL: Always ensure this is an array
      isLoadingThreads: false,
      loadError: null,
      loadThreads: jest.fn()
    });
    
    // CRITICAL: Mock useThreadFiltering with parameter validation
    (ChatSidebarHooksModule.useThreadFiltering as jest.Mock).mockReset().mockImplementation(
      (threads, searchQuery, threadsPerPage, currentPage) => {
        console.log('🔥 HOOK RESET: useThreadFiltering', { 
          threadsType: typeof threads, 
          isArray: Array.isArray(threads), 
          threadsLength: threads?.length 
        });
        // Ensure threads is always an array to prevent filter errors
        const safeThreads = Array.isArray(threads) ? threads : [];
        return {
          sortedThreads: safeThreads,
          paginatedThreads: safeThreads,
          totalPages: Math.max(1, Math.ceil(safeThreads.length / (threadsPerPage || 50)))
        };
      }
    );
    
    // Configure ThreadService mock methods
    Object.assign(ThreadServiceModule.ThreadService, mockThreadService);
  }

  afterEach() {
    jest.restoreAllMocks();
  }

  // Configure store with custom data
  configureStore(overrides: Partial<typeof mockChatStore>) {
    const storeConfig = { ...mockChatStore, ...overrides };
    (useUnifiedChatStore as jest.Mock).mockReturnValue(storeConfig);
    return storeConfig;
  }

  // Configure hooks with custom threads  
  configureChatSidebarHooks(overrides: any = {}) {
    // Use provided threads or fallback to sampleThreads
    const threadsToUse = overrides.threads || sampleThreads;
    
    console.log('🔧 configureChatSidebarHooks called with:', {
      threadsProvided: !!overrides.threads,
      threadsCount: threadsToUse.length,
      threadIds: threadsToUse.map((t: any) => t.id)
    });
    
    // Configure useChatSidebarState mock
    const sidebarStateConfig = {
      searchQuery: overrides.sidebarState?.searchQuery || '',
      setSearchQuery: jest.fn(),
      isCreatingThread: overrides.sidebarState?.isCreatingThread || false,
      setIsCreatingThread: jest.fn(),
      showAllThreads: overrides.sidebarState?.showAllThreads || false,
      setShowAllThreads: jest.fn(),
      filterType: (overrides.sidebarState?.filterType || 'all') as const,
      setFilterType: jest.fn(),
      currentPage: overrides.sidebarState?.currentPage || 1,
      setCurrentPage: jest.fn()
    };
    
    // Configure useThreadLoader mock - CRITICAL: ensure isLoadingThreads is false
    const threadLoaderConfig = {
      threads: Array.isArray(threadsToUse) ? threadsToUse : [], // CRITICAL: Ensure always array
      isLoadingThreads: false,  // CRITICAL: Always false for tests
      loadError: null,
      loadThreads: jest.fn(),
      ...overrides.threadLoader
    };
    
    // Configure useThreadFiltering mock
    const safeThreadsForFiltering = Array.isArray(threadsToUse) ? threadsToUse : [];
    const threadFilteringConfig = {
      sortedThreads: safeThreadsForFiltering,
      paginatedThreads: safeThreadsForFiltering,
      totalPages: Math.ceil(safeThreadsForFiltering.length / 50),
      ...overrides.threadFiltering
    };
    
    console.log('🎯 Mock configurations:', {
      threadLoaderConfig,
      threadFilteringConfig
    });
    
    // CRITICAL: Use mockImplementation with debugging instead of mockReturnValue
    // This allows us to see when hooks are actually called
    (ChatSidebarHooksModule.useChatSidebarState as jest.Mock).mockImplementation(() => {
      console.log('🔥 HOOK CALLED: useChatSidebarState (CONFIGURED)', sidebarStateConfig);
      return sidebarStateConfig;
    });
    
    (ChatSidebarHooksModule.useThreadLoader as jest.Mock).mockImplementation((...args: any[]) => {
      console.log('🔥 HOOK CALLED: useThreadLoader (CONFIGURED)', { args, returning: threadLoaderConfig });
      return threadLoaderConfig;
    });
    
    (ChatSidebarHooksModule.useThreadFiltering as jest.Mock).mockImplementation((threads, searchQuery, threadsPerPage, currentPage) => {
      console.log('🔥 HOOK CALLED: useThreadFiltering (CONFIGURED)', { 
        threadsType: typeof threads, 
        isArray: Array.isArray(threads), 
        threadsLength: threads?.length,
        returning: threadFilteringConfig 
      });
      // CRITICAL: Validate threads parameter and provide safe fallback
      if (!Array.isArray(threads)) {
        console.warn('⚠️ useThreadFiltering received non-array threads:', threads);
        const safeConfig = {
          sortedThreads: [],
          paginatedThreads: [],
          totalPages: 1
        };
        return safeConfig;
      }
      return threadFilteringConfig;
    });
    
    console.log('🎯 Applied mock configurations using mockImplementation with debugging');
    
    return {
      sidebarState: sidebarStateConfig,
      threadLoader: threadLoaderConfig,
      threadFiltering: threadFilteringConfig
    };
  }

  // Configure auth store
  configureAuth(overrides: Partial<typeof mockAuthStore>) {
    const authConfig = { ...mockAuthStore, ...overrides };
    (useAuthStore as jest.Mock).mockReturnValue(authConfig);
    return authConfig;
  }

  // Configure auth state
  configureAuthState(overrides: Partial<typeof mockAuthState>) {
    const authStateConfig = { ...mockAuthState, ...overrides };
    console.log('🔧 configureAuthState called with overrides:', overrides);
    console.log('🎯 Final authStateConfig:', authStateConfig);
    (useAuthState as jest.Mock).mockReturnValue(authStateConfig);
    return authStateConfig;
  }

  // Configure thread service responses
  configureThreadService(overrides: any) {
    const { ThreadService } = require('@/services/threadService');
    Object.assign(ThreadService, overrides);
    return ThreadService;
  }

  // Helper to create test threads
  createThread(overrides: Partial<typeof sampleThreads[0]> = {}) {
    return {
      id: `thread-${Math.random().toString(36).substr(2, 9)}`,
      title: 'Test Thread',
      lastMessage: 'Test message',
      lastActivity: new Date().toISOString(),
      messageCount: 1,
      isActive: false,
      participants: ['user1', 'assistant'],
      tags: ['test'],
      ...overrides
    };
  }

  // Mock loading state
  mockLoadingState() {
    this.configureStore({ 
      isProcessing: true,
      threads: []
    });
  }

  // Mock error state
  mockErrorState(error: string = 'Test error') {
    this.configureStore({ 
      error: error,
      threads: []
    });
  }
}

export const createTestSetup = () => new ChatSidebarTestSetup();

// Render helper with providers
export const renderWithProvider = (component: React.ReactElement) => {
  return render(
    <TestProviders>
      {component}
    </TestProviders>
  );
};

// Test utilities
export const findThreadElement = (container: HTMLElement, threadId: string) => {
  return container.querySelector(`[data-testid="thread-item-${threadId}"]`);
};

export const findThreadByTitle = (container: HTMLElement, title: string) => {
  return Array.from(container.querySelectorAll('[data-testid*="thread-item"]')).find(
    el => el.textContent?.includes(title)
  ) as HTMLElement;
};

// Mock user interactions
export const mockUserInteraction = {
  clickThread: (element: HTMLElement) => {
    element.click();
  },
  
  hoverThread: (element: HTMLElement) => {
    element.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
  },
  
  contextMenu: (element: HTMLElement) => {
    element.dispatchEvent(new MouseEvent('contextmenu', { bubbles: true }));
  }
};

// Time formatting utility
export const formatRelativeTime = (date: string | Date) => {
  const now = new Date();
  const target = new Date(date);
  const diffInMs = now.getTime() - target.getTime();
  const diffInMinutes = Math.floor(diffInMs / (1000 * 60));
  const diffInHours = Math.floor(diffInMs / (1000 * 60 * 60));
  const diffInDays = Math.floor(diffInMs / (1000 * 60 * 60 * 24));

  if (diffInMinutes < 60) {
    return `${diffInMinutes}m ago`;
  } else if (diffInHours < 24) {
    return `${diffInHours}h ago`;
  } else {
    return `${diffInDays}d ago`;
  }
};

// Export mocks for use in tests
export { useUnifiedChatStore, useAuthStore, useAuthState, useWebSocket, ChatSidebarHooksModule, ThreadServiceModule };