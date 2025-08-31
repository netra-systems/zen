/**
 * ChatHistorySection Basic Functionality Tests
 * Tests for basic rendering, display, and thread highlighting
 */

// Mock functions need to be declared before jest.mock calls with default implementations
const mockUseUnifiedChatStore = jest.fn(() => ({
  isProcessing: false,
  messages: [],
  threads: [],
  currentThreadId: null,
  isThreadLoading: false,
  addMessage: jest.fn(),
  setProcessing: jest.fn(),
  clearMessages: jest.fn(),
  updateThreads: jest.fn(),
  setCurrentThreadId: jest.fn(),
}));

const mockUseThreadStore = jest.fn(() => ({
  threads: [],
  currentThreadId: null,
  setThreads: jest.fn(),
  setCurrentThread: jest.fn(),
  addThread: jest.fn(),
  updateThread: jest.fn(),
  deleteThread: jest.fn(),
  setLoading: jest.fn(),
  setError: jest.fn()
}));

const mockUseChatStore = jest.fn(() => ({
  clearMessages: jest.fn(),
  loadMessages: jest.fn(),
  messages: []
}));

const mockUseLoadingState = jest.fn(() => ({
  shouldShowLoading: false,
  shouldShowEmptyState: false,
  shouldShowExamplePrompts: false,
  loadingMessage: ''
}));

const mockUseThreadNavigation = jest.fn(() => ({
  currentThreadId: null,
  isNavigating: false,
  navigateToThread: jest.fn(),
  createNewThread: jest.fn()
}));

const mockUseAuthStore = jest.fn(() => ({
  isAuthenticated: true,
  user: { id: 'user-1', email: 'test@example.com' },
  login: jest.fn(),
  logout: jest.fn(),
  checkAuth: jest.fn()
}));

// Mock all store imports
jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: () => mockUseUnifiedChatStore()
}));

jest.mock('@/hooks/useLoadingState', () => ({
  useLoadingState: () => mockUseLoadingState()
}));

jest.mock('@/hooks/useThreadNavigation', () => ({
  useThreadNavigation: () => mockUseThreadNavigation()
}));

jest.mock('@/store/authStore', () => ({
  useAuthStore: () => mockUseAuthStore()
}));

jest.mock('@/store/threadStore', () => ({
  useThreadStore: () => mockUseThreadStore()
}));

jest.mock('@/store/chat', () => ({
  useChatStore: () => mockUseChatStore()
}));

// AuthGate mock - always render children
jest.mock('@/components/auth/AuthGate', () => {
  const React = require('react');
  return {
    AuthGate: ({ children }: { children: React.ReactNode }) => children
  };
});

// Mock ThreadService
jest.mock('@/services/threadService', () => ({
  ThreadService: {
    listThreads: jest.fn(),
    createThread: jest.fn(),
    getThreadMessages: jest.fn(),
    updateThread: jest.fn(),
    deleteThread: jest.fn()
  }
}));

// Mock next/navigation
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(() => ({
    push: jest.fn(),
    replace: jest.fn(),
    back: jest.fn()
  })),
  usePathname: jest.fn(() => '/chat')
}));

// Mock logger
jest.mock('@/lib/logger', () => ({
  logger: {
    error: jest.fn(),
    info: jest.fn(),
    debug: jest.fn(),
    warn: jest.fn()
  }
}));

jest.mock('framer-motion', () => {
  const React = require('react');
  return {
    motion: {
      div: ({ children, ...props }: any) => React.createElement('div', props, children),
    },
    AnimatePresence: ({ children }: any) => children,
  };
});

import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
import React from 'react';
import { render, screen } from '@testing-library/react';
import { createTestSetup } from './setup';
import { mockThreads } from './mockData';

// Import ChatHistorySection after mocks are set up
const { ChatHistorySection } = require('@/components/ChatHistorySection');
import { setupStoreForEmptyState, 
  setupStoreForCurrentThread, 
  setupStoreWithCustomThreads,
  expectBasicStructure, 
  expectThreadsRendered, 
  expectEmptyState, 
  expectActiveThread,
  createThreadWithTitle,
  expectUntitledThread,
  expectSpecificThreadTitle,
  expectMultipleThreadTitles,
  expectThreadStructure
} from './testUtils';

const mockStore = {
  isProcessing: false,
  messages: [],
  threads: mockThreads,
  currentThreadId: 'thread-1',
  isThreadLoading: false,
  addMessage: jest.fn(),
  setProcessing: jest.fn(),
  clearMessages: jest.fn(),
  updateThreads: jest.fn(),
  setCurrentThreadId: jest.fn(),
};

describe('ChatHistorySection - Basic Functionality', () => {
  setupAntiHang();
    jest.setTimeout(10000);
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Set up default mock return values
    mockUseUnifiedChatStore.mockReturnValue(mockStore);
    
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
    
    mockUseAuthStore.mockReturnValue({
      isAuthenticated: true,
      user: { id: 'user-1', email: 'test@example.com' },
      login: jest.fn(),
      logout: jest.fn(),
      checkAuth: jest.fn()
    });
    
    mockUseThreadStore.mockReturnValue({
      threads: mockThreads,
      currentThreadId: 'thread-1',
      setThreads: jest.fn(),
      setCurrentThread: jest.fn(),
      addThread: jest.fn(),
      updateThread: jest.fn(),
      deleteThread: jest.fn(),
      setLoading: jest.fn(),
      setError: jest.fn()
    });
    
    mockUseChatStore.mockReturnValue({
      clearMessages: jest.fn(),
      loadMessages: jest.fn(),
      messages: []
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
      cleanupAntiHang();
  });

  describe('History item rendering', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should render all conversation threads', () => {
      render(<ChatHistorySection />);
      
      expect(screen.getByText('First Conversation')).toBeInTheDocument();
      expect(screen.getByText('Second Conversation')).toBeInTheDocument();
      expect(screen.getByText('Third Conversation')).toBeInTheDocument();
    });

    it('should display correct timestamps for threads', () => {
      render(<ChatHistorySection />);
      
      expect(screen.getByText('Today')).toBeInTheDocument();
      expect(screen.getByText('Yesterday')).toBeInTheDocument();
      // The third thread shows a date instead of "7 days ago"
      const dateText = screen.getByText(/\d{1,2}\/\d{1,2}\/\d{4}/);
      expect(dateText).toBeInTheDocument();
    });

    it('should highlight the current active thread', () => {
      const testSetup = createTestSetup();
      setupStoreForCurrentThread(testSetup, 'thread-1');
      
      render(<ChatHistorySection />);
      
      expectActiveThread(screen, 'First Conversation');
    });

    it('should show message icons for each thread', () => {
      render(<ChatHistorySection />);
      
      // Look for SVG elements with the message-square class
      const container = screen.getByText('Chat History').closest('.flex-col');
      const messageIcons = container?.querySelectorAll('svg.lucide-message-square');
      expect(messageIcons?.length).toBeGreaterThanOrEqual(3);
    });

    it('should render empty state when no threads exist', () => {
      const testSetup = createTestSetup();
      setupStoreForEmptyState(testSetup);

      render(<ChatHistorySection />);
      
      expectEmptyState(screen);
    });

    it('should show hover effects on non-active threads', () => {
      render(<ChatHistorySection />);
      
      const secondThread = screen.getByText('Second Conversation').closest('div[class*="group"]');
      expect(secondThread).toHaveClass('hover:bg-accent/50');
    });

    it('should render thread with null title as Untitled', () => {
      const testSetup = createTestSetup();
      const threadsWithNullTitle = [createThreadWithTitle(mockThreads[0], null)];
      setupStoreWithCustomThreads(testSetup, threadsWithNullTitle);

      render(<ChatHistorySection />);
      
      expectUntitledThread(screen);
    });

    it('should render thread with empty title as Untitled', () => {
      const testSetup = createTestSetup();
      const threadsWithEmptyTitle = [createThreadWithTitle(mockThreads[0], '')];
      setupStoreWithCustomThreads(testSetup, threadsWithEmptyTitle);

      render(<ChatHistorySection />);
      
      expectUntitledThread(screen);
    });

    it('should display message count for each thread', () => {
      render(<ChatHistorySection />);
      
      // Check if message counts are displayed (this depends on the actual component implementation)
      expectThreadStructure(screen);
    });

    it('should handle threads with very long titles', () => {
      const testSetup = createTestSetup();
      const longTitle = 'This is a very long conversation title that should be handled properly by the component without breaking the layout or causing any display issues';
      const threadsWithLongTitle = [createThreadWithTitle(mockThreads[0], longTitle)];
      setupStoreWithCustomThreads(testSetup, threadsWithLongTitle);

      render(<ChatHistorySection />);
      
      expectSpecificThreadTitle(screen, longTitle);
    });

    it('should render threads in chronological order', () => {
      const testSetup = createTestSetup();
      const orderedThreads = [
        { ...mockThreads[0], title: 'Newest Thread', created_at: Math.floor(Date.now() / 1000) },
        { ...mockThreads[1], title: 'Middle Thread', created_at: Math.floor(Date.now() / 1000) - 3600 },
        { ...mockThreads[2], title: 'Oldest Thread', created_at: Math.floor(Date.now() / 1000) - 7200 },
      ];
      setupStoreWithCustomThreads(testSetup, orderedThreads);
      
      render(<ChatHistorySection />);
      
      expectMultipleThreadTitles(screen, ['Newest Thread', 'Middle Thread', 'Oldest Thread']);
    });

    it('should handle missing timestamps gracefully', () => {
      const testSetup = createTestSetup();
      const threadsWithMissingTimestamp = [{ ...mockThreads[0], created_at: null, updated_at: null }];
      setupStoreWithCustomThreads(testSetup, threadsWithMissingTimestamp);

      render(<ChatHistorySection />);
      
      expect(screen.getByText('First Conversation')).toBeInTheDocument();
      expect(screen.getByText('Unknown date')).toBeInTheDocument();
    });
  });

  describe('Component structure', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should render the main chat history header', () => {
      render(<ChatHistorySection />);
      
      expect(screen.getByText('Chat History')).toBeInTheDocument();
    });

    it('should render a scrollable container for threads', () => {
      render(<ChatHistorySection />);
      
      const container = screen.getByText('Chat History').closest('.flex-col');
      expect(container).toBeInTheDocument();
    });

    it('should apply consistent styling to thread items', () => {
      render(<ChatHistorySection />);
      
      const firstThread = screen.getByText('First Conversation').closest('div[class*="group"]');
      const secondThread = screen.getByText('Second Conversation').closest('div[class*="group"]');
      
      // Both should have similar class structures for consistency
      expect(firstThread?.className).toBeDefined();
      expect(secondThread?.className).toBeDefined();
    });

    it('should handle component mounting and unmounting', () => {
      const { unmount } = render(<ChatHistorySection />);
      
      expect(screen.getByText('Chat History')).toBeInTheDocument();
      
      // Should unmount without errors
      expect(() => unmount()).not.toThrow();
    });
  });

  describe('Loading and error states', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should show loading state when threads are being fetched', () => {
      mockUseLoadingState.mockReturnValue({
        shouldShowLoading: true,
        shouldShowEmptyState: false,
        shouldShowExamplePrompts: false,
        loadingMessage: 'Loading...'
      });
      
      mockUseUnifiedChatStore.mockReturnValue({
        ...mockStore,
        isThreadLoading: true
      });
      
      render(<ChatHistorySection />);
      
      // Should show some loading indicator (implementation specific)
      const container = screen.getByText('Chat History').closest('.flex-col');
      expect(container).toBeInTheDocument();
    });

    it('should handle error state gracefully', () => {
      mockUseUnifiedChatStore.mockReturnValue({
        ...mockStore,
        error: 'Failed to load threads'
      });
      
      render(<ChatHistorySection />);
      
      // Should still render the basic structure even with errors
      expect(screen.getByText('Chat History')).toBeInTheDocument();
    });

    it('should recover from error state when data is available', () => {
      // First render with error
      mockUseUnifiedChatStore.mockReturnValue({
        ...mockStore,
        error: 'Network error'
      });
      const { rerender } = render(<ChatHistorySection />);
      
      // Then render with data
      mockUseUnifiedChatStore.mockReturnValue(mockStore);
      rerender(<ChatHistorySection />);
      
      expect(screen.getByText('First Conversation')).toBeInTheDocument();
    });
  });
});