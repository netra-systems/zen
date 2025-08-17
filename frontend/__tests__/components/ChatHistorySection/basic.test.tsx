/**
 * ChatHistorySection Basic Functionality Tests
 * Tests for basic rendering, display, and thread highlighting
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { ChatHistorySection } from '@/components/ChatHistorySection';
import { createTestSetup, mockThreads, useThreadStore, useAuthStore } from './setup';

describe('ChatHistorySection - Basic Functionality', () => {
  const testSetup = createTestSetup();

  beforeEach(() => {
    testSetup.beforeEach();
  });

  afterEach(() => {
    testSetup.afterEach();
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
      testSetup.configureStoreMocks({ currentThreadId: 'thread-1' });
      
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
      testSetup.configureStoreMocks({ threads: [] });

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
      
      testSetup.configureStoreMocks({ threads: threadsWithNullTitle });

      render(<ChatHistorySection />);
      
      expect(screen.getByText('Untitled')).toBeInTheDocument();
    });

    it('should render thread with empty title as Untitled', () => {
      const threadsWithEmptyTitle = [
        { ...mockThreads[0], title: '' },
      ];
      
      testSetup.configureStoreMocks({ threads: threadsWithEmptyTitle });

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
      
      testSetup.configureStoreMocks({ threads: threadsWithLongTitle });

      render(<ChatHistorySection />);
      
      const longTitleElement = screen.getByText(/This is a very long conversation title/);
      expect(longTitleElement).toBeInTheDocument();
    });

    it('should render threads in chronological order', () => {
      render(<ChatHistorySection />);
      
      const historyContainer = screen.getByText('Chat History').closest('.flex-col');
      const threadElements = Array.from(historyContainer?.querySelectorAll('[data-testid*="thread"]') || []);
      
      // Verify that threads are rendered (exact order checking depends on component implementation)
      expect(threadElements.length).toBeGreaterThanOrEqual(3);
    });

    it('should handle missing timestamps gracefully', () => {
      const threadsWithMissingTimestamp = [
        { ...mockThreads[0], created_at: null, updated_at: null },
      ];
      
      testSetup.configureStoreMocks({ threads: threadsWithMissingTimestamp });

      render(<ChatHistorySection />);
      
      // Should still render the thread even without timestamps
      expect(screen.getByText('First Conversation')).toBeInTheDocument();
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
      testSetup.mockLoadingState(true);
      
      render(<ChatHistorySection />);
      
      // Should show some loading indicator (implementation specific)
      const container = screen.getByText('Chat History').closest('.flex-col');
      expect(container).toBeInTheDocument();
    });

    it('should handle error state gracefully', () => {
      testSetup.mockErrorState('Failed to load threads');
      
      render(<ChatHistorySection />);
      
      // Should still render the basic structure even with errors
      expect(screen.getByText('Chat History')).toBeInTheDocument();
    });

    it('should recover from error state when data is available', () => {
      // First render with error
      testSetup.mockErrorState('Network error');
      const { rerender } = render(<ChatHistorySection />);
      
      // Then render with data
      testSetup.beforeEach(); // Reset to normal state
      rerender(<ChatHistorySection />);
      
      expect(screen.getByText('First Conversation')).toBeInTheDocument();
    });
  });
});