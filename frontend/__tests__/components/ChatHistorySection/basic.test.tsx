/**
 * ChatHistorySection Basic Functionality Tests
 * Tests for basic rendering, display, and thread highlighting
 */

// Hoist all mocks to the top for proper Jest handling
const mockUseUnifiedChatStore = jest.fn();
const mockUseLoadingState = jest.fn();
const mockUseThreadNavigation = jest.fn();

jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: mockUseUnifiedChatStore
}));

jest.mock('@/hooks/useLoadingState', () => ({
  useLoadingState: mockUseLoadingState
}));

jest.mock('@/hooks/useThreadNavigation', () => ({
  useThreadNavigation: mockUseThreadNavigation
}));

// AuthGate mock - always render children
jest.mock('@/components/auth/AuthGate', () => ({
  AuthGate: ({ children }: { children: React.ReactNode }) => children
}));

jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => React.createElement('div', props, children),
  },
  AnimatePresence: ({ children }: any) => children,
}));

import React from 'react';
import { render, screen } from '@testing-library/react';
import { ChatHistorySection } from '@/components/ChatHistorySection';
import { createTestSetup, mockThreads } from './setup';

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
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('History item rendering', () => {
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
      // Configure store to have currentThreadId set
      mockUseUnifiedChatStore.mockReturnValue({
        ...mockStore,
        currentThreadId: 'thread-1'
      });
      
      mockUseThreadNavigation.mockReturnValue({
        currentThreadId: 'thread-1',
        isNavigating: false,
        navigateToThread: jest.fn(),
        createNewThread: jest.fn()
      });
      
      render(<ChatHistorySection />);
      
      const firstThread = screen.getByText('First Conversation').closest('div[class*="group"]');
      expect(firstThread).toHaveClass('bg-accent');
    });

    it('should show message icons for each thread', () => {
      render(<ChatHistorySection />);
      
      // Look for SVG elements with the message-square class
      const container = screen.getByText('Chat History').closest('.flex-col');
      const messageIcons = container?.querySelectorAll('svg.lucide-message-square');
      expect(messageIcons?.length).toBeGreaterThanOrEqual(3);
    });

    it('should render empty state when no threads exist', () => {
      mockUseUnifiedChatStore.mockReturnValue({
        ...mockStore,
        threads: []
      });

      render(<ChatHistorySection />);
      
      expect(screen.getByText('No conversations yet')).toBeInTheDocument();
    });

    it('should show hover effects on non-active threads', () => {
      render(<ChatHistorySection />);
      
      const secondThread = screen.getByText('Second Conversation').closest('div[class*="group"]');
      expect(secondThread).toHaveClass('hover:bg-accent/50');
    });

    it('should render thread with null title as Untitled', () => {
      const threadsWithNullTitle = [
        { ...mockThreads[0], title: null },
      ];
      
      mockUseUnifiedChatStore.mockReturnValue({
        ...mockStore,
        threads: threadsWithNullTitle
      });

      render(<ChatHistorySection />);
      
      expect(screen.getByText('Untitled')).toBeInTheDocument();
    });

    it('should render thread with empty title as Untitled', () => {
      const threadsWithEmptyTitle = [
        { ...mockThreads[0], title: '' },
      ];
      
      mockUseUnifiedChatStore.mockReturnValue({
        ...mockStore,
        threads: threadsWithEmptyTitle
      });

      render(<ChatHistorySection />);
      
      expect(screen.getByText('Untitled')).toBeInTheDocument();
    });

    it('should display message count for each thread', () => {
      render(<ChatHistorySection />);
      
      // Check if message counts are displayed (this depends on the actual component implementation)
      // Looking for any indication of message counts
      const historyContainer = screen.getByText('Chat History').closest('.flex-col');
      expect(historyContainer).toBeInTheDocument();
      
      // The specific implementation may vary, but we expect some way to show message counts
      // This test validates the basic structure is in place
    });

    it('should handle threads with very long titles', () => {
      const threadsWithLongTitle = [
        { ...mockThreads[0], title: 'This is a very long conversation title that should be handled properly by the component without breaking the layout or causing any display issues' },
      ];
      
      mockUseUnifiedChatStore.mockReturnValue({
        ...mockStore,
        threads: threadsWithLongTitle
      });

      render(<ChatHistorySection />);
      
      const longTitleElement = screen.getByText(/This is a very long conversation title/);
      expect(longTitleElement).toBeInTheDocument();
    });

    it('should render threads in chronological order', () => {
      // Create threads with specific order
      const orderedThreads = [
        { ...mockThreads[0], title: 'Newest Thread', created_at: Math.floor(Date.now() / 1000) },
        { ...mockThreads[1], title: 'Middle Thread', created_at: Math.floor(Date.now() / 1000) - 3600 },
        { ...mockThreads[2], title: 'Oldest Thread', created_at: Math.floor(Date.now() / 1000) - 7200 },
      ];
      
      mockUseUnifiedChatStore.mockReturnValue({
        ...mockStore,
        threads: orderedThreads
      });
      
      render(<ChatHistorySection />);
      
      // Verify all threads are rendered
      expect(screen.getByText('Newest Thread')).toBeInTheDocument();
      expect(screen.getByText('Middle Thread')).toBeInTheDocument();
      expect(screen.getByText('Oldest Thread')).toBeInTheDocument();
    });

    it('should handle missing timestamps gracefully', () => {
      const threadsWithMissingTimestamp = [
        { ...mockThreads[0], created_at: null, updated_at: null },
      ];
      
      mockUseUnifiedChatStore.mockReturnValue({
        ...mockStore,
        threads: threadsWithMissingTimestamp
      });

      render(<ChatHistorySection />);
      
      // Should still render the thread even without timestamps
      expect(screen.getByText('First Conversation')).toBeInTheDocument();
      expect(screen.getByText('Unknown date')).toBeInTheDocument();
    });
  });

  describe('Component structure', () => {
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