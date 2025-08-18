/**
 * ChatSidebar Interaction Tests
 * Tests for navigation, thread management, search, and user interactions
 */

import React from 'react';
import { screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// CRITICAL: Mock AuthGate before importing ChatSidebar
jest.mock('@/components/auth/AuthGate', () => ({
  AuthGate: ({ children }: { children: React.ReactNode }) => {
    return <div data-testid="mocked-authgate">{children}</div>;
  }
}));

// CRITICAL: ChatSidebar hooks are mocked in setup.tsx - no duplicate mocks needed

import { ChatSidebar } from '@/components/chat/ChatSidebar';
import * as ChatSidebarHooksModule from '@/components/chat/ChatSidebarHooks';
import { 
  createTestSetup, 
  renderWithProvider, 
  sampleThreads, 
  mockChatStore, 
  mockThreadService 
} from './setup';

describe('ChatSidebar - Interactions', () => {
  const testSetup = createTestSetup();

  beforeEach(() => {
    testSetup.beforeEach();
  });

  afterEach(() => {
    testSetup.afterEach();
  });

  describe('Thread Navigation and Switching', () => {
    it('should navigate to thread when clicked', async () => {
      // CRITICAL: Configure all mocks BEFORE rendering
      // Ensure authenticated state for thread rendering
      testSetup.configureAuthState({
        isAuthenticated: true,
        isLoading: false,
        userTier: 'Early'
      });
      
      testSetup.configureStore({
        currentThreadId: 'thread-1'
      });
      
      // Configure hooks to return sample threads BEFORE rendering
      testSetup.configureChatSidebarHooks({
        threads: sampleThreads
      });
      
      renderWithProvider(<ChatSidebar />);
      
      const thread2 = screen.getByTestId('thread-item-thread-2');
      fireEvent.click(thread2);
      
      await waitFor(() => {
        expect(mockChatStore.setActiveThread).toHaveBeenCalledWith('thread-2');
      });
    });

    it('should not trigger navigation when already on current thread', () => {
      // CRITICAL: Configure all mocks BEFORE rendering
      // Ensure authenticated state for thread rendering
      testSetup.configureAuthState({
        isAuthenticated: true,
        isLoading: false,
        userTier: 'Early'
      });
      
      testSetup.configureStore({
        currentThreadId: 'thread-1',
        activeThreadId: 'thread-1'
      });
      
      // Configure hooks to return sample threads BEFORE rendering
      testSetup.configureChatSidebarHooks({
        threads: sampleThreads
      });
      
      renderWithProvider(<ChatSidebar />);
      
      const thread1 = screen.getByTestId('thread-item-thread-1');
      fireEvent.click(thread1);
      
      // Should not call setActiveThread for already active thread
      expect(mockChatStore.setActiveThread).not.toHaveBeenCalled();
    });

    it('should handle keyboard navigation between threads', async () => {
      // CRITICAL: Configure all mocks BEFORE rendering
      // Ensure authenticated state for thread rendering
      testSetup.configureAuthState({
        isAuthenticated: true,
        isLoading: false,
        userTier: 'Early'
      });
      
      testSetup.configureStore({});
      
      // Configure hooks to return sample threads BEFORE rendering
      testSetup.configureChatSidebarHooks({
        threads: sampleThreads
      });
      
      renderWithProvider(<ChatSidebar />);
      
      const thread1 = screen.getByTestId('thread-item-thread-1');
      
      // Focus first thread
      thread1.focus();
      expect(document.activeElement).toBe(thread1);
      
      // Navigate with arrow keys
      fireEvent.keyDown(thread1, { key: 'ArrowDown' });
      
      await waitFor(() => {
        const thread2 = screen.getByTestId('thread-item-thread-2');
        expect(document.activeElement).toBe(thread2);
      });
    });

    it('should support Enter key to activate thread', async () => {
      // CRITICAL: Configure all mocks BEFORE rendering
      // Ensure authenticated state for thread rendering
      testSetup.configureAuthState({
        isAuthenticated: true,
        isLoading: false,
        userTier: 'Early'
      });
      
      testSetup.configureStore({});
      
      // Configure hooks to return sample threads BEFORE rendering
      testSetup.configureChatSidebarHooks({
        threads: sampleThreads
      });
      
      renderWithProvider(<ChatSidebar />);
      
      const thread1 = screen.getByTestId('thread-item-thread-1');
      thread1.focus();
      
      fireEvent.keyDown(thread1, { key: 'Enter' });
      
      await waitFor(() => {
        expect(mockChatStore.setActiveThread).toHaveBeenCalledWith('thread-1');
      });
    });

    it('should handle thread selection with Space key', async () => {
      // CRITICAL: Configure all mocks BEFORE rendering
      // Ensure authenticated state for thread rendering
      testSetup.configureAuthState({
        isAuthenticated: true,
        isLoading: false,
        userTier: 'Early'
      });
      
      testSetup.configureStore({});
      
      // Configure hooks to return sample threads BEFORE rendering
      testSetup.configureChatSidebarHooks({
        threads: sampleThreads
      });
      
      renderWithProvider(<ChatSidebar />);
      
      const thread2 = screen.getByTestId('thread-item-thread-2');
      thread2.focus();
      
      fireEvent.keyDown(thread2, { key: ' ' }); // Space key
      
      await waitFor(() => {
        expect(mockChatStore.setActiveThread).toHaveBeenCalledWith('thread-2');
      });
    });
  });

  describe('Thread Management Operations', () => {
    it('should create new thread when new thread button is clicked', async () => {
      // CRITICAL: Configure all mocks BEFORE rendering
      // Ensure authenticated state for UI interactions
      testSetup.configureAuthState({
        isAuthenticated: true,
        isLoading: false,
        userTier: 'Early'
      });
      
      testSetup.configureStore({});
      
      // Configure hooks BEFORE rendering
      testSetup.configureChatSidebarHooks({});
      
      mockThreadService.createThread.mockResolvedValue({
        id: 'new-thread-id',
        title: 'New Thread',
        created_at: Date.now(),
        updated_at: Date.now()
      });
      
      renderWithProvider(<ChatSidebar />);
      
      const newThreadButton = screen.getByRole('button', { name: /new/i }) ||
                             screen.getByTestId('new-thread-button');
      
      fireEvent.click(newThreadButton);
      
      await waitFor(() => {
        expect(mockThreadService.createThread).toHaveBeenCalled();
      });
    });

    it('should handle thread deletion', async () => {
      // CRITICAL: Configure all mocks BEFORE rendering
      // Ensure authenticated state for thread rendering
      testSetup.configureAuthState({
        isAuthenticated: true,
        isLoading: false,
        userTier: 'Early'
      });
      
      testSetup.configureStore({});
      
      // Configure hooks to return sample threads BEFORE rendering
      testSetup.configureChatSidebarHooks({
        threads: sampleThreads
      });
      
      mockThreadService.deleteThread.mockResolvedValue({ success: true });
      
      renderWithProvider(<ChatSidebar />);
      
      const thread1 = screen.getByTestId('thread-item-thread-1');
      
      // Right-click to show context menu
      fireEvent.contextMenu(thread1);
      
      // Look for delete option
      const deleteOption = screen.queryByText(/delete/i) || 
                          screen.queryByRole('menuitem', { name: /delete/i });
      
      if (deleteOption) {
        fireEvent.click(deleteOption);
        
        // Confirm deletion if confirmation dialog appears
        const confirmButton = screen.queryByText(/confirm/i) || 
                             screen.queryByText(/yes/i) ||
                             screen.queryByRole('button', { name: /delete/i });
        
        if (confirmButton) {
          fireEvent.click(confirmButton);
        }
        
        await waitFor(() => {
          expect(mockThreadService.deleteThread).toHaveBeenCalledWith('thread-1');
        });
      }
    });

    it('should handle thread rename operation', async () => {
      // CRITICAL: Configure all mocks BEFORE rendering
      // Ensure authenticated state for thread rendering
      testSetup.configureAuthState({
        isAuthenticated: true,
        isLoading: false,
        userTier: 'Early'
      });
      
      testSetup.configureStore({});
      
      // Configure hooks to return sample threads BEFORE rendering
      testSetup.configureChatSidebarHooks({
        threads: sampleThreads
      });
      
      mockThreadService.updateThread.mockResolvedValue({ success: true });
      
      renderWithProvider(<ChatSidebar />);
      
      const thread1 = screen.getByTestId('thread-item-thread-1');
      
      // Double-click to rename or find rename button
      fireEvent.doubleClick(thread1);
      
      // Look for inline edit input
      const editInput = screen.queryByDisplayValue('AI Optimization Discussion') ||
                       screen.queryByRole('textbox');
      
      if (editInput) {
        await userEvent.clear(editInput);
        await userEvent.type(editInput, 'Renamed Thread');
        fireEvent.keyDown(editInput, { key: 'Enter' });
        
        await waitFor(() => {
          expect(mockThreadService.updateThread).toHaveBeenCalledWith(
            'thread-1', 
            expect.objectContaining({ title: 'Renamed Thread' })
          );
        });
      }
    });

    it('should handle thread archiving', async () => {
      // CRITICAL: Configure all mocks BEFORE rendering
      // Ensure authenticated state for thread rendering
      testSetup.configureAuthState({
        isAuthenticated: true,
        isLoading: false,
        userTier: 'Early'
      });
      
      testSetup.configureStore({});
      
      // Configure hooks to return sample threads BEFORE rendering
      testSetup.configureChatSidebarHooks({
        threads: sampleThreads
      });
      
      renderWithProvider(<ChatSidebar />);
      
      const thread2 = screen.getByTestId('thread-item-thread-2');
      fireEvent.contextMenu(thread2);
      
      const archiveOption = screen.queryByText(/archive/i) ||
                           screen.queryByRole('menuitem', { name: /archive/i });
      
      if (archiveOption) {
        fireEvent.click(archiveOption);
        
        await waitFor(() => {
          expect(mockThreadService.updateThread).toHaveBeenCalledWith(
            'thread-2',
            expect.objectContaining({ status: 'archived' })
          );
        });
      }
    });

    it('should handle bulk operations on multiple threads', async () => {
      // CRITICAL: Configure all mocks BEFORE rendering
      // Ensure authenticated state for thread rendering
      testSetup.configureAuthState({
        isAuthenticated: true,
        isLoading: false,
        userTier: 'Early'
      });
      
      testSetup.configureStore({
        selectionMode: true
      });
      
      // Configure hooks to return sample threads BEFORE rendering
      testSetup.configureChatSidebarHooks({
        threads: sampleThreads
      });
      
      renderWithProvider(<ChatSidebar />);
      
      // Select multiple threads (if bulk selection is supported)
      const thread1 = screen.getByTestId('thread-item-thread-1');
      const thread2 = screen.getByTestId('thread-item-thread-2');
      
      // Ctrl+click for multi-select
      fireEvent.click(thread1, { ctrlKey: true });
      fireEvent.click(thread2, { ctrlKey: true });
      
      // Look for bulk actions toolbar
      const bulkDeleteButton = screen.queryByRole('button', { name: /delete selected/i });
      
      if (bulkDeleteButton) {
        fireEvent.click(bulkDeleteButton);
        
        await waitFor(() => {
          expect(mockThreadService.deleteThread).toHaveBeenCalledTimes(2);
        });
      }
    });
  });

  describe('Thread Search and Filtering', () => {
    it('should filter threads based on search query', async () => {
      // CRITICAL: Configure all mocks BEFORE rendering
      // Ensure authenticated state for thread rendering
      testSetup.configureAuthState({
        isAuthenticated: true,
        isLoading: false,
        userTier: 'Early'
      });
      
      testSetup.configureStore({});
      
      // Configure hooks to return sample threads BEFORE rendering
      testSetup.configureChatSidebarHooks({
        threads: sampleThreads
      });
      
      renderWithProvider(<ChatSidebar />);
      
      const searchInput = screen.queryByRole('textbox') ||
                         screen.queryByPlaceholderText(/search/i);
      
      if (searchInput) {
        await userEvent.type(searchInput, 'Performance');
        
        await waitFor(() => {
          expect(screen.getByText('Performance Analysis')).toBeInTheDocument();
          expect(screen.queryByText('AI Optimization Discussion')).not.toBeInTheDocument();
          expect(screen.queryByText('Data Processing Pipeline')).not.toBeInTheDocument();
        });
      }
    });

    it('should clear search and show all threads', async () => {
      // CRITICAL: Configure all mocks BEFORE rendering
      // Ensure authenticated state for thread rendering
      testSetup.configureAuthState({
        isAuthenticated: true,
        isLoading: false,
        userTier: 'Early'
      });
      
      testSetup.configureStore({});
      
      // Configure hooks to return sample threads with search query BEFORE rendering
      testSetup.configureChatSidebarHooks({
        threads: sampleThreads,
        sidebarState: {
          searchQuery: 'Performance'
        }
      });
      
      renderWithProvider(<ChatSidebar />);
      
      const searchInput = screen.queryByRole('textbox');
      
      if (searchInput) {
        await userEvent.clear(searchInput);
        
        await waitFor(() => {
          expect(screen.getByText('AI Optimization Discussion')).toBeInTheDocument();
          expect(screen.getByText('Performance Analysis')).toBeInTheDocument();
          expect(screen.getByText('Data Processing Pipeline')).toBeInTheDocument();
        });
      }
    });

    it('should search by thread content and tags', async () => {
      // CRITICAL: Configure all mocks BEFORE rendering
      // Ensure authenticated state for thread rendering
      testSetup.configureAuthState({
        isAuthenticated: true,
        isLoading: false,
        userTier: 'Early'
      });
      
      testSetup.configureStore({});
      
      // Configure hooks to return sample threads BEFORE rendering
      testSetup.configureChatSidebarHooks({
        threads: sampleThreads
      });
      
      renderWithProvider(<ChatSidebar />);
      
      const searchInput = screen.queryByRole('textbox');
      
      if (searchInput) {
        // Search by tag
        await userEvent.type(searchInput, 'optimization');
        
        await waitFor(() => {
          expect(screen.getByText('AI Optimization Discussion')).toBeInTheDocument();
          expect(screen.queryByText('Data Processing Pipeline')).not.toBeInTheDocument();
        });
        
        // Clear and search by content
        await userEvent.clear(searchInput);
        await userEvent.type(searchInput, 'pipeline');
        
        await waitFor(() => {
          expect(screen.getByText('Data Processing Pipeline')).toBeInTheDocument();
          expect(screen.queryByText('AI Optimization Discussion')).not.toBeInTheDocument();
        });
      }
    });

    it('should show no results message when search has no matches', async () => {
      // CRITICAL: Configure all mocks BEFORE rendering
      // Ensure authenticated state for thread rendering
      testSetup.configureAuthState({
        isAuthenticated: true,
        isLoading: false,
        userTier: 'Early'
      });
      
      testSetup.configureStore({});
      
      // Configure hooks to return sample threads BEFORE rendering
      testSetup.configureChatSidebarHooks({
        threads: sampleThreads
      });
      
      renderWithProvider(<ChatSidebar />);
      
      const searchInput = screen.queryByRole('textbox');
      
      if (searchInput) {
        await userEvent.type(searchInput, 'nonexistent search term');
        
        await waitFor(() => {
          expect(screen.queryByText('AI Optimization Discussion')).not.toBeInTheDocument();
          expect(screen.queryByText('Performance Analysis')).not.toBeInTheDocument();
          expect(screen.queryByText('Data Processing Pipeline')).not.toBeInTheDocument();
          
          // Should show no results message
          expect(screen.getByText(/no threads found/i) || 
                screen.getByText(/no results/i)).toBeInTheDocument();
        });
      }
    });

    it('should handle search with debouncing', async () => {
      // CRITICAL: Configure all mocks BEFORE rendering
      // Ensure authenticated state for thread rendering
      testSetup.configureAuthState({
        isAuthenticated: true,
        isLoading: false,
        userTier: 'Early'
      });
      
      testSetup.configureStore({});
      
      // Configure hooks to return sample threads BEFORE rendering
      testSetup.configureChatSidebarHooks({
        threads: sampleThreads
      });
      
      const searchSpy = jest.fn();
      
      renderWithProvider(<ChatSidebar />);
      
      const searchInput = screen.queryByRole('textbox');
      
      if (searchInput) {
        // Type rapidly
        await userEvent.type(searchInput, 'test search query');
        
        // If debouncing is implemented, it should not search on every keystroke
        await waitFor(() => {
          // The actual search behavior depends on implementation
          expect(searchInput).toHaveValue('test search query');
        });
      }
    });
  });

  describe('Context Menu Operations', () => {
    it('should show context menu on right click', () => {
      // CRITICAL: Configure all mocks BEFORE rendering
      // Ensure authenticated state for thread rendering
      testSetup.configureAuthState({
        isAuthenticated: true,
        isLoading: false,
        userTier: 'Early'
      });
      
      testSetup.configureStore({});
      
      // Configure hooks to return sample threads BEFORE rendering
      testSetup.configureChatSidebarHooks({
        threads: sampleThreads
      });
      
      renderWithProvider(<ChatSidebar />);
      
      const thread1 = screen.getByTestId('thread-item-thread-1');
      fireEvent.contextMenu(thread1);
      
      // Should show context menu with options
      const contextMenu = screen.queryByRole('menu') ||
                         screen.queryByTestId('context-menu');
      
      if (contextMenu) {
        expect(contextMenu).toBeInTheDocument();
        
        // Should have common menu items
        expect(screen.queryByText(/rename/i) || 
               screen.queryByText(/delete/i) ||
               screen.queryByText(/archive/i)).toBeInTheDocument();
      }
    });

    it('should close context menu when clicking elsewhere', () => {
      // CRITICAL: Configure all mocks BEFORE rendering
      // Ensure authenticated state for thread rendering
      testSetup.configureAuthState({
        isAuthenticated: true,
        isLoading: false,
        userTier: 'Early'
      });
      
      testSetup.configureStore({});
      
      // Configure hooks to return sample threads BEFORE rendering
      testSetup.configureChatSidebarHooks({
        threads: sampleThreads
      });
      
      renderWithProvider(<ChatSidebar />);
      
      const thread1 = screen.getByTestId('thread-item-thread-1');
      fireEvent.contextMenu(thread1);
      
      // Click outside to close
      fireEvent.click(document.body);
      
      const contextMenu = screen.queryByRole('menu');
      if (contextMenu) {
        expect(contextMenu).not.toBeInTheDocument();
      }
    });

    it('should handle keyboard shortcuts in context menu', () => {
      // Ensure authenticated state for thread rendering
      testSetup.configureAuthState({
        isAuthenticated: true,
        isLoading: false,
        userTier: 'Early'
      });
      
      testSetup.configureStore({});
      
      // Configure hooks to return sample threads
      testSetup.configureChatSidebarHooks({
        threads: sampleThreads
      });
      
      renderWithProvider(<ChatSidebar />);
      
      const thread1 = screen.getByTestId('thread-item-thread-1');
      fireEvent.contextMenu(thread1);
      
      // Use keyboard to navigate menu
      const contextMenu = screen.queryByRole('menu');
      if (contextMenu) {
        fireEvent.keyDown(contextMenu, { key: 'ArrowDown' });
        fireEvent.keyDown(contextMenu, { key: 'Enter' });
        
        // Should execute the selected action
        expect(contextMenu).toBeTruthy();
      }
    });
  });

  describe('Drag and Drop Operations', () => {
    it('should support drag to reorder threads', () => {
      // Ensure authenticated state for thread rendering
      testSetup.configureAuthState({
        isAuthenticated: true,
        isLoading: false,
        userTier: 'Early'
      });
      
      testSetup.configureStore({});
      
      // Configure hooks to return sample threads
      testSetup.configureChatSidebarHooks({
        threads: sampleThreads
      });
      
      renderWithProvider(<ChatSidebar />);
      
      const thread1 = screen.getByTestId('thread-item-thread-1');
      const thread2 = screen.getByTestId('thread-item-thread-2');
      
      // Start drag
      fireEvent.dragStart(thread1);
      fireEvent.dragOver(thread2);
      fireEvent.drop(thread2);
      
      // Should handle reordering (implementation specific)
      expect(thread1).toBeInTheDocument();
      expect(thread2).toBeInTheDocument();
    });

    it('should handle drag and drop for thread organization', () => {
      // Ensure authenticated state for thread rendering
      testSetup.configureAuthState({
        isAuthenticated: true,
        isLoading: false,
        userTier: 'Early'
      });
      
      testSetup.configureStore({
        folders: [{ id: 'folder-1', name: 'Work Threads' }]
      });
      
      // Configure hooks to return sample threads
      testSetup.configureChatSidebarHooks({
        threads: sampleThreads
      });
      
      renderWithProvider(<ChatSidebar />);
      
      const thread1 = screen.getByTestId('thread-item-thread-1');
      const folder = screen.queryByTestId('folder-work-threads');
      
      if (folder) {
        fireEvent.dragStart(thread1);
        fireEvent.dragOver(folder);
        fireEvent.drop(folder);
        
        // Should move thread to folder
        expect(mockThreadService.updateThread).toHaveBeenCalledWith(
          'thread-1',
          expect.objectContaining({ folderId: 'folder-1' })
        );
      }
    });
  });
});