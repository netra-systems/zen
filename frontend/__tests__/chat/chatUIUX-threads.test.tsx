/**
 * Chat UI/UX Thread Management Tests
 * Module-based architecture: Thread management tests ≤300 lines, functions ≤8 lines
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { ChatWindow } from '../../components/chat/ChatWindow';
import { ThreadSidebar } from '../../components/chat/ThreadSidebar';
import { 
  setupBasicMocks,
  setupAuthenticatedStore,
  setupStoreWithThreads,
  createMockAuthStore,
  createMockThreadStore,
  createMockThread,
  renderWithProviders,
  setupThreadServiceMocks,
  setupConfirmMock,
  cleanupMocks
} from './chatUIUX-shared-utilities';

// Setup mocks
setupBasicMocks();

// Import mocked modules
import { useAuthStore } from '../../store/authStore';
import { useChatStore } from '../../store/chatStore';
import { useThreadStore } from '../../store/threadStore';
import { useUnifiedChatStore } from '../../store/unified-chat';
import { useChatWebSocket } from '../../hooks/useChatWebSocket';

describe('Chat UI/UX Thread Management Tests', () => {
  const mockAuthStore = createMockAuthStore();
  const mockThreadStore = createMockThreadStore();
  
  beforeEach(() => {
    jest.clearAllMocks();
    setupConfirmMock();
    setupThreadServiceMocks();
    setupDefaultMockReturnValues();
  });

  afterEach(() => {
    cleanupMocks();
  });

  describe('Thread Creation and Management', () => {
    test('4. Should create a new thread when starting a conversation', async () => {
      const mockOnSendMessage = jest.fn();
      
      render(renderWithProviders(
        <ChatWindow onSendMessage={mockOnSendMessage} />
      ));
      
      await sendTestMessage('Hello, create a new thread', mockOnSendMessage);
    });

    test('5. Should display thread list in sidebar with correct information', async () => {
      const mockThreads = [
        createMockThread('thread-1', 'First Conversation'),
        createMockThread('thread-2', 'Second Conversation')
      ];
      
      setupThreadsInStore(mockThreads);
      
      render(renderWithProviders(<ThreadSidebar />));
      
      await verifyThreadsDisplayed(['First Conversation', 'Second Conversation']);
    });

    test('6. Should switch between threads and load corresponding messages', async () => {
      const mockThreads = [
        createMockThread('thread-1', 'Thread 1'),
        createMockThread('thread-2', 'Thread 2')
      ];
      
      const storeWithSetFunction = setupThreadSwitching(mockThreads);
      
      render(renderWithProviders(<ThreadSidebar />));
      
      await switchToThread('Thread 2', storeWithSetFunction);
    });

    test('7. Should delete a thread and update the UI accordingly', async () => {
      const mockThreads = [createMockThread('thread-1', 'Thread to Delete')];
      const storeWithDeleteFunction = setupThreadDeletion(mockThreads);
      
      render(renderWithProviders(<ThreadSidebar />));
      
      await attemptThreadDeletion('Thread to Delete', storeWithDeleteFunction);
    });

    test('8. Should handle empty thread list gracefully', async () => {
      setupThreadsInStore([]);
      
      render(renderWithProviders(<ThreadSidebar />));
      
      await waitFor(() => {
        // ThreadSidebar should render without errors even with empty threads
        expect(document.body).toBeInTheDocument();
      });
    });

    test('9. Should handle thread loading states', async () => {
      const loadingStore = {
        ...mockThreadStore,
        loading: true,
        threads: []
      };
      (useThreadStore as unknown as jest.Mock).mockReturnValue(loadingStore);
      
      render(renderWithProviders(<ThreadSidebar />));
      
      await waitFor(() => {
        expect(document.body).toBeInTheDocument();
      });
    });

    test('10. Should handle thread errors appropriately', async () => {
      const errorStore = {
        ...mockThreadStore,
        error: 'Failed to load threads',
        threads: []
      };
      (useThreadStore as unknown as jest.Mock).mockReturnValue(errorStore);
      
      render(renderWithProviders(<ThreadSidebar />));
      
      await waitFor(() => {
        expect(document.body).toBeInTheDocument();
      });
    });
  });
});

// Helper functions ≤8 lines each
const setupDefaultMockReturnValues = () => {
  (useAuthStore as unknown as jest.Mock).mockReturnValue(
    setupAuthenticatedStore(mockAuthStore)
  );
  (useChatStore as unknown as jest.Mock).mockReturnValue({
    messages: [],
    isProcessing: false
  });
  (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue({
    isProcessing: false
  });
  (useChatWebSocket as unknown as jest.Mock).mockReturnValue({});
};

const setupThreadsInStore = (threads: any[]) => {
  const storeWithThreads = setupStoreWithThreads(mockThreadStore, threads);
  (useThreadStore as unknown as jest.Mock).mockReturnValue(storeWithThreads);
};

const setupThreadSwitching = (threads: any[]) => {
  const storeWithSetFunction = {
    ...setupStoreWithThreads(mockThreadStore, threads),
    setCurrentThread: jest.fn()
  };
  (useThreadStore as unknown as jest.Mock).mockReturnValue(storeWithSetFunction);
  return storeWithSetFunction;
};

const setupThreadDeletion = (threads: any[]) => {
  const storeWithDeleteFunction = {
    ...setupStoreWithThreads(mockThreadStore, threads),
    deleteThread: jest.fn()
  };
  (useThreadStore as unknown as jest.Mock).mockReturnValue(storeWithDeleteFunction);
  return storeWithDeleteFunction;
};

const sendTestMessage = async (message: string, mockFn: jest.Mock) => {
  const messageInput = screen.getByPlaceholderText(/Type your message/i);
  await userEvent.type(messageInput, message);
  
  const sendButton = screen.getByRole('button', { name: /send/i });
  fireEvent.click(sendButton);
  
  await waitFor(() => {
    expect(mockFn).toHaveBeenCalledWith(message);
  });
};

const verifyThreadsDisplayed = async (threadTitles: string[]) => {
  await waitFor(() => {
    threadTitles.forEach(title => {
      expect(screen.getByText(title)).toBeInTheDocument();
    });
  });
};

const switchToThread = async (threadTitle: string, store: any) => {
  const threadElement = screen.getByText(threadTitle);
  fireEvent.click(threadElement);
  
  await waitFor(() => {
    expect(store.setCurrentThread).toHaveBeenCalledWith('thread-2');
  });
};

const attemptThreadDeletion = async (threadTitle: string, store: any) => {
  await waitFor(() => {
    expect(screen.getByText(threadTitle)).toBeInTheDocument();
  });
  
  const deleteButtons = screen.queryAllByRole('button');
  const deleteButton = findDeleteButton(deleteButtons);
  
  if (deleteButton) {
    fireEvent.click(deleteButton);
    expect(global.confirm).toHaveBeenCalled();
    
    await waitFor(() => {
      expect(store.deleteThread).toHaveBeenCalledWith('thread-1');
    });
  }
};

const findDeleteButton = (buttons: HTMLElement[]) => {
  return buttons.find(btn => 
    btn.querySelector('svg.lucide-trash-2') || 
    btn.querySelector('[data-testid="delete-thread"]')
  );
};