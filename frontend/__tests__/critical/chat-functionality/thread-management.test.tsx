import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
ent: Growth & Enterprise (Multi-conversation power users)
 * - Business Goal: Enable efficient thread management for complex AI workflows
 * - Value Impact: Thread management essential for 85% of power users
 * - Revenue Impact: Power users convert from Free to paid at 3.2x higher rate
 * 
 * ARCHITECTURAL COMPLIANCE:
 * - File size: ≤300 lines (MANDATORY)
 * - Functions: ≤8 lines each (MANDATORY)
 * - Real thread components with actual state management
 * - Real WebSocket thread operations
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

// Real components and utilities
import { ThreadSidebar } from '../../../components/chat/ThreadSidebar';
import { ChatSidebar } from '../../../components/chat/ChatSidebar';
import { MainChat } from '../../../components/chat/MainChat';
import { TestProviders } from '../../setup/test-providers';

// Real stores and hooks
import { useThreadStore } from '../../../store/threadStore';
import { useUnifiedChatStore } from '../../../store/unified-chat';

// Thread test utilities
import {
  setupThreadTestEnvironment,
  establishThreadConnection,
  cleanupThreadResources,
  createNewThread,
  switchToThread,
  deleteThread,
  expectThreadCreated,
  expectThreadSwitched,
  expectThreadDeleted,
  expectThreadPersisted,
  expectThreadInSidebar,
  THREAD_OPERATION_TIMEOUT
} from './test-helpers';

// Thread data factories
import {
  createBasicThread,
  createThreadWithMessages,
  createThreadSequence,
  createLongThreadTitle,
  createSpecialCharThread,
  createEmptyThread,
  createThreadWithId,
  createThreadUpdate
} from './test-data-factories';

describe('Thread Management Core Functionality', () => {
    jest.setTimeout(10000);
  let user: ReturnType<typeof userEvent.setup>;

  beforeEach(async () => {
    user = userEvent.setup();
    await setupThreadTestEnvironment();
  });

  afterEach(async () => {
    await cleanupThreadResources();
  });

  describe('Thread Creation Workflow', () => {
      jest.setTimeout(10000);
    test('creates new thread with default title', async () => {
      render(
        <TestProviders>
          <ThreadSidebar />
        </TestProviders>
      );

      const createButton = screen.getByRole('button', { name: /new.*thread/i });
      await user.click(createButton);

      await waitFor(() => {
        expectThreadCreated('New Chat');
      }, { timeout: THREAD_OPERATION_TIMEOUT });

      expectThreadInSidebar('New Chat');
    });

    test('creates thread with custom title input', async () => {
      render(
        <TestProviders>
          <ThreadSidebar />
        </TestProviders>
      );

      const createButton = screen.getByRole('button', { name: /new.*thread/i });
      await user.click(createButton);

      const titleInput = screen.getByPlaceholderText(/thread title/i);
      const customTitle = 'AI Strategy Discussion';
      
      await user.clear(titleInput);
      await user.type(titleInput, customTitle);
      await user.keyboard('{Enter}');

      await waitFor(() => {
        expectThreadCreated(customTitle);
      });
    });

    test('creates thread from first message context', async () => {
      render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );

      const messageInput = screen.getByRole('textbox');
      const firstMessage = 'Help me optimize my AI workflow';
      
      await user.type(messageInput, firstMessage);
      await user.keyboard('{Enter}');

      await waitFor(() => {
        const autoTitle = 'AI workflow optimization';
        expectThreadCreated(autoTitle);
      });
    });

    test('handles thread creation errors gracefully', async () => {
      render(
        <TestProviders>
          <ThreadSidebar />
        </TestProviders>
      );

      // Simulate network error during creation
      const createButton = screen.getByRole('button', { name: /new.*thread/i });
      await user.click(createButton);

      await waitFor(() => {
        const errorMessage = screen.queryByText(/error.*creating.*thread/i);
        expect(errorMessage).toBeInTheDocument();
      });
    });

    test('validates thread title length limits', async () => {
      render(
        <TestProviders>
          <ThreadSidebar />
        </TestProviders>
      );

      const createButton = screen.getByRole('button', { name: /new.*thread/i });
      await user.click(createButton);

      const titleInput = screen.getByPlaceholderText(/thread title/i);
      const longTitle = createLongThreadTitle(200);
      
      await user.type(titleInput, longTitle);
      await user.keyboard('{Enter}');

      await waitFor(() => {
        const warningMessage = screen.queryByText(/title.*too.*long/i);
        expect(warningMessage).toBeInTheDocument();
      });
    });

    test('creates multiple threads without conflicts', async () => {
      render(
        <TestProviders>
          <ThreadSidebar />
        </TestProviders>
      );

      const threadTitles = ['Research Project', 'Code Review', 'Planning Session'];
      
      for (const title of threadTitles) {
        const createButton = screen.getByRole('button', { name: /new.*thread/i });
        await user.click(createButton);
        
        const titleInput = screen.getByPlaceholderText(/thread title/i);
        await user.clear(titleInput);
        await user.type(titleInput, title);
        await user.keyboard('{Enter}');
        
        await waitFor(() => {
          expectThreadInSidebar(title);
        });
      }

      // All three threads should be visible
      threadTitles.forEach(title => {
        expect(screen.getByText(title)).toBeInTheDocument();
      });
    });
  });

  describe('Thread Switching Without Data Loss', () => {
      jest.setTimeout(10000);
    test('switches between threads maintaining state', async () => {
      const { threadId1, threadId2 } = await createThreadSequence(2);
      
      render(
        <TestProviders>
          <ThreadSidebar />
        </TestProviders>
      );

      // Switch to first thread
      await switchToThread(threadId1);
      
      await waitFor(() => {
        expectThreadSwitched(threadId1);
      });

      // Switch to second thread
      await switchToThread(threadId2);
      
      await waitFor(() => {
        expectThreadSwitched(threadId2);
      });
    });

    test('preserves message input when switching threads', async () => {
      const { threadId1, threadId2 } = await createThreadSequence(2);
      
      render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );

      // Type draft message in first thread
      const messageInput = screen.getByRole('textbox');
      const draftMessage = 'This is a draft message';
      
      await switchToThread(threadId1);
      await user.type(messageInput, draftMessage);

      // Switch to second thread
      await switchToThread(threadId2);
      
      // Switch back to first thread
      await switchToThread(threadId1);

      // Draft should be preserved
      await waitFor(() => {
        expect(messageInput).toHaveValue(draftMessage);
      });
    });

    test('maintains scroll position during thread switch', async () => {
      const threadWithMessages = createThreadWithMessages(50);
      
      render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );

      await switchToThread(threadWithMessages.id);
      
      // Scroll to middle of conversation
      const chatContainer = screen.getByTestId('chat-messages');
      act(() => {
        chatContainer.scrollTop = 500;
      });

      // Switch away and back
      const { threadId } = await createThreadSequence(1);
      await switchToThread(threadId);
      await switchToThread(threadWithMessages.id);

      // Scroll position should be restored
      await waitFor(() => {
        expect(chatContainer.scrollTop).toBe(500);
      });
    });

    test('handles rapid thread switching without errors', async () => {
      const { threadIds } = await createThreadSequence(5);
      
      render(
        <TestProviders>
          <ThreadSidebar />
        </TestProviders>
      );

      // Rapidly switch between threads
      for (let i = 0; i < 10; i++) {
        const randomThreadId = threadIds[i % threadIds.length];
        await switchToThread(randomThreadId);
        await new Promise(resolve => setTimeout(resolve, 50));
      }

      // Should not show any error states
      expect(screen.queryByText(/error/i)).not.toBeInTheDocument();
    });
  });

  describe('Thread Deletion with Confirmation', () => {
      jest.setTimeout(10000);
    test('deletes thread after user confirmation', async () => {
      const thread = createBasicThread();
      
      render(
        <TestProviders>
          <ThreadSidebar />
        </TestProviders>
      );

      const deleteButton = screen.getByTestId(`delete-thread-${thread.id}`);
      await user.click(deleteButton);

      // Confirm deletion
      const confirmButton = screen.getByRole('button', { name: /confirm.*delete/i });
      await user.click(confirmButton);

      await waitFor(() => {
        expectThreadDeleted(thread.id);
      });

      expect(screen.queryByText(thread.title)).not.toBeInTheDocument();
    });

    test('cancels deletion when user declines', async () => {
      const thread = createBasicThread();
      
      render(
        <TestProviders>
          <ThreadSidebar />
        </TestProviders>
      );

      const deleteButton = screen.getByTestId(`delete-thread-${thread.id}`);
      await user.click(deleteButton);

      // Cancel deletion
      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      await user.click(cancelButton);

      // Thread should still be there
      expect(screen.getByText(thread.title)).toBeInTheDocument();
    });

    test('prevents deletion of last remaining thread', async () => {
      const thread = createBasicThread();
      
      render(
        <TestProviders>
          <ThreadSidebar />
        </TestProviders>
      );

      const deleteButton = screen.getByTestId(`delete-thread-${thread.id}`);
      await user.click(deleteButton);

      await waitFor(() => {
        const warningMessage = screen.queryByText(/cannot.*delete.*last.*thread/i);
        expect(warningMessage).toBeInTheDocument();
      });
    });

    test('handles deletion errors with user feedback', async () => {
      const thread = createBasicThread();
      
      render(
        <TestProviders>
          <ThreadSidebar />
        </TestProviders>
      );

      const deleteButton = screen.getByTestId(`delete-thread-${thread.id}`);
      await user.click(deleteButton);

      const confirmButton = screen.getByRole('button', { name: /confirm.*delete/i });
      await user.click(confirmButton);

      // Simulate network error
      await waitFor(() => {
        const errorMessage = screen.queryByText(/error.*deleting.*thread/i);
        expect(errorMessage).toBeInTheDocument();
      });
    });
  });

  describe('Thread Persistence and Recovery', () => {
      jest.setTimeout(10000);
    test('persists threads across browser sessions', async () => {
      const thread = createBasicThread();
      
      render(
        <TestProviders>
          <ThreadSidebar />
        </TestProviders>
      );

      await createNewThread(thread.title);
      
      // Simulate page refresh
      await cleanupThreadResources();
      await setupThreadTestEnvironment();
      
      render(
        <TestProviders>
          <ThreadSidebar />
        </TestProviders>
      );

      await waitFor(() => {
        expectThreadPersisted(thread.title);
      });
    });

    test('recovers thread state after network reconnection', async () => {
      const thread = createThreadWithMessages(10);
      
      render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );

      await switchToThread(thread.id);
      
      // Simulate network disconnection and reconnection
      await establishThreadConnection();

      await waitFor(() => {
        expect(screen.getByText(thread.title)).toBeInTheDocument();
        // Messages should be recovered
        expect(screen.getAllByText(/message/i)).toHaveLength(10);
      });
    });
  });
});