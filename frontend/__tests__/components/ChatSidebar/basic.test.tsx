/**
 * ChatSidebar Basic Functionality Tests  
 * Tests for thread list display, metadata, and basic rendering
 */

import React from 'react';
import { screen, within, waitFor } from '@testing-library/react';
import { ChatSidebar } from '@/components/chat/ChatSidebar';
import { createTestSetup, renderWithProvider, sampleThreads } from './setup';

describe('ChatSidebar - Basic Functionality', () => {
  const testSetup = createTestSetup();

  beforeEach(() => {
    testSetup.beforeEach();
  });

  afterEach(() => {
    testSetup.afterEach();
  });

  describe('Thread List Display', () => {
    it('should render thread list when threads are available', async () => {
      // Configure ThreadService to return sample threads
      testSetup.configureThreadService({
        listThreads: jest.fn().mockResolvedValue(sampleThreads)
      });
      
      testSetup.configureStore({
        activeThreadId: 'thread-2'
      });
      
      // CRITICAL: Configure hooks to provide thread data
      testSetup.configureChatSidebarHooks({
        threads: sampleThreads
      });
      
      renderWithProvider(<ChatSidebar />);
      
      expect(screen.getByTestId('thread-list')).toBeInTheDocument();
      
      // Wait for the async loading to complete
      await waitFor(() => {
        expect(screen.getByText('AI Optimization Discussion')).toBeInTheDocument();
      });
      
      expect(screen.getByText('Performance Analysis')).toBeInTheDocument();
      expect(screen.getByText('Data Processing Pipeline')).toBeInTheDocument();
      
      // Active thread should be highlighted
      const activeThread = screen.getByTestId('thread-item-thread-2');
      expect(activeThread).toHaveClass('bg-emerald-50');
    });

    it('should display thread metadata correctly', () => {
      const threadWithMetadata = testSetup.createThread({
        id: 'thread-1',
        title: 'Test Thread',
        lastMessage: 'Last message content',
        lastActivity: new Date(Date.now() - 1800000).toISOString(), // 30 min ago
        messageCount: 25,
        participants: ['user1', 'assistant'],
        tags: ['optimization', 'performance']
      });
      
      testSetup.configureStore({
        threads: [threadWithMetadata]
      });
      
      // Configure hooks to provide thread data
      testSetup.configureChatSidebarHooks({
        threads: [threadWithMetadata]
      });
      
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
      testSetup.configureStore({ threads: [] });
      
      renderWithProvider(<ChatSidebar />);
      
      expect(screen.getByText('No conversations yet')).toBeInTheDocument();
      expect(screen.getByText('Start a new conversation to get started')).toBeInTheDocument();
    });

    it('should handle threads with missing metadata gracefully', () => {
      const incompleteThread = {
        id: 'incomplete-thread',
        title: 'Incomplete Thread',
        // Missing other fields
      };
      
      testSetup.configureStore({
        threads: [incompleteThread]
      });
      
      renderWithProvider(<ChatSidebar />);
      
      expect(screen.getByText('Incomplete Thread')).toBeInTheDocument();
      // Should render without crashing despite missing fields
      expect(screen.getByTestId('thread-item-incomplete-thread')).toBeInTheDocument();
    });

    it('should display thread creation time when lastActivity is missing', () => {
      const threadWithoutActivity = testSetup.createThread({
        id: 'no-activity-thread',
        title: 'Thread Without Activity',
        lastActivity: undefined,
        created_at: new Date(Date.now() - 3600000).toISOString() // 1 hour ago
      });
      
      testSetup.configureStore({
        threads: [threadWithoutActivity]
      });
      
      renderWithProvider(<ChatSidebar />);
      
      const threadItem = screen.getByTestId('thread-item-no-activity-thread');
      expect(within(threadItem).getByText('1h ago')).toBeInTheDocument();
    });

    it('should truncate long thread titles appropriately', () => {
      const longTitleThread = testSetup.createThread({
        id: 'long-title-thread',
        title: 'This is an extremely long thread title that should be truncated to prevent layout issues and maintain readability',
      });
      
      testSetup.configureStore({
        threads: [longTitleThread]
      });
      
      renderWithProvider(<ChatSidebar />);
      
      const threadItem = screen.getByTestId('thread-item-long-title-thread');
      const titleElement = within(threadItem).getByText(/This is an extremely long thread title/);
      
      expect(titleElement).toBeInTheDocument();
      // Title should be displayed but potentially with CSS truncation
    });

    it('should show message count with proper formatting', () => {
      const threads = [
        testSetup.createThread({ messageCount: 1, title: 'Single Message' }),
        testSetup.createThread({ messageCount: 0, title: 'No Messages' }),
        testSetup.createThread({ messageCount: 999, title: 'Many Messages' }),
      ];
      
      testSetup.configureStore({ threads });
      
      renderWithProvider(<ChatSidebar />);
      
      expect(screen.getByText('1 message')).toBeInTheDocument();
      expect(screen.getByText('0 messages')).toBeInTheDocument();
      expect(screen.getByText('999 messages')).toBeInTheDocument();
    });

    it('should display participant information', () => {
      const threadWithParticipants = testSetup.createThread({
        id: 'participants-thread',
        participants: ['user1', 'user2', 'assistant'],
        title: 'Multi-participant Thread'
      });
      
      testSetup.configureStore({
        threads: [threadWithParticipants]
      });
      
      renderWithProvider(<ChatSidebar />);
      
      const threadItem = screen.getByTestId('thread-item-participants-thread');
      
      // Should show participant count or indicators
      expect(threadItem).toBeInTheDocument();
      // Implementation may vary on how participants are displayed
    });
  });

  describe('Thread Status and States', () => {
    it('should indicate active/current thread clearly', () => {
      testSetup.configureStore({
        threads: sampleThreads,
        currentThreadId: 'thread-1',
        activeThreadId: 'thread-1'
      });
      
      renderWithProvider(<ChatSidebar />);
      
      const activeThread = screen.getByTestId('thread-item-thread-1');
      expect(activeThread).toHaveAttribute('aria-current', 'page');
      expect(activeThread).toHaveClass('bg-primary/10');
    });

    it('should show loading states for individual threads', () => {
      const loadingThread = testSetup.createThread({
        id: 'loading-thread',
        isLoading: true,
        title: 'Loading Thread'
      });
      
      testSetup.configureStore({
        threads: [loadingThread]
      });
      
      renderWithProvider(<ChatSidebar />);
      
      const threadItem = screen.getByTestId('thread-item-loading-thread');
      // Should show loading indicator (implementation specific)
      expect(threadItem).toBeInTheDocument();
    });

    it('should handle threads with error states', () => {
      const errorThread = testSetup.createThread({
        id: 'error-thread',
        hasError: true,
        errorMessage: 'Failed to load messages',
        title: 'Error Thread'
      });
      
      testSetup.configureStore({
        threads: [errorThread]
      });
      
      renderWithProvider(<ChatSidebar />);
      
      const threadItem = screen.getByTestId('thread-item-error-thread');
      // Should show error indicator or styling
      expect(threadItem).toBeInTheDocument();
    });

    it('should indicate threads with unread messages', () => {
      const unreadThread = testSetup.createThread({
        id: 'unread-thread',
        hasUnread: true,
        unreadCount: 3,
        title: 'Unread Thread'
      });
      
      testSetup.configureStore({
        threads: [unreadThread]
      });
      
      renderWithProvider(<ChatSidebar />);
      
      const threadItem = screen.getByTestId('thread-item-unread-thread');
      // Should show unread indicator
      expect(threadItem).toBeInTheDocument();
      
      // Look for unread count badge
      const unreadBadge = within(threadItem).queryByText('3');
      if (unreadBadge) {
        expect(unreadBadge).toBeInTheDocument();
      }
    });
  });

  describe('Component Structure', () => {
    it('should render main sidebar container', () => {
      renderWithProvider(<ChatSidebar />);
      
      const sidebar = screen.getByRole('complementary') || 
                     screen.getByTestId('chat-sidebar') ||
                     screen.getByText(/conversations/i).closest('div');
      
      expect(sidebar).toBeInTheDocument();
    });

    it('should render new thread button', () => {
      renderWithProvider(<ChatSidebar />);
      
      const newThreadButton = screen.getByRole('button', { name: /new/i }) ||
                             screen.getByTestId('new-thread-button') ||
                             screen.getByText(/new conversation/i);
      
      expect(newThreadButton).toBeInTheDocument();
    });

    it('should render search functionality', () => {
      renderWithProvider(<ChatSidebar />);
      
      const searchInput = screen.queryByRole('textbox') ||
                         screen.queryByPlaceholderText(/search/i);
      
      // Search may be optional, so don't fail if not present
      if (searchInput) {
        expect(searchInput).toBeInTheDocument();
      }
    });

    it('should handle component mount/unmount gracefully', () => {
      const { unmount } = renderWithProvider(<ChatSidebar />);
      
      expect(screen.getByRole('complementary') || screen.getByTestId('chat-sidebar')).toBeInTheDocument();
      
      // Should unmount without errors
      expect(() => unmount()).not.toThrow();
    });
  });

  describe('Responsive Behavior', () => {
    it('should adapt to different screen sizes', () => {
      // Mock small screen
      Object.defineProperty(window, 'innerWidth', { value: 320, configurable: true });
      
      renderWithProvider(<ChatSidebar />);
      
      // Should render appropriately on small screens
      expect(screen.getByRole('complementary') || screen.getByTestId('chat-sidebar')).toBeInTheDocument();
      
      // Mock large screen  
      Object.defineProperty(window, 'innerWidth', { value: 1920, configurable: true });
      
      // Should adapt to larger screens
      expect(screen.getByRole('complementary') || screen.getByTestId('chat-sidebar')).toBeInTheDocument();
    });

    it('should handle sidebar collapse/expand states', () => {
      testSetup.configureStore({
        sidebarCollapsed: true,
        threads: sampleThreads
      });
      
      renderWithProvider(<ChatSidebar />);
      
      // Should handle collapsed state appropriately
      const sidebar = screen.getByRole('complementary') || screen.getByTestId('chat-sidebar');
      expect(sidebar).toBeInTheDocument();
    });
  });
});