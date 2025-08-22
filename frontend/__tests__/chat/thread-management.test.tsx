/**
 * Thread Management Tests
 * ======================
 * Modular UI tests for thread lifecycle operations
 * Tests 4-7 (Thread Management) from original chatUIUXCore.test.tsx
 * Focused on thread creation, selection, and deletion workflows
 */

import React from 'react';
import { render } from '@testing-library/react';
import '@testing-library/jest-dom';

// Import shared utilities and test components
import {
  setupDefaultMocks,
  cleanupMocks,
  createThreadStoreMock,
  createTestThread,
  screen,
  fireEvent,
  waitFor,
  expectElementByText,
  expectElementByTestId,
  expectElementByRole,
  findElementByText,
  findElementByTestId,
  findElementByRole,
  waitForElementByText,
  waitForElementByRole
} from './ui-test-utilities';

// Mock stores before importing components
jest.mock('../../store/authStore', () => ({
  useAuthStore: jest.fn(() => ({
    user: { id: 'test-user', email: 'test@example.com', name: 'Test User' },
    token: 'test-token',
    isAuthenticated: true,
    setUser: jest.fn(),
    setToken: jest.fn(),
    logout: jest.fn(),
    checkAuth: jest.fn()
  }))
}));

jest.mock('../../store/chatStore', () => ({
  useChatStore: jest.fn(() => ({
    messages: [],
    addMessage: jest.fn(),
    clearMessages: jest.fn(),
    sendMessage: jest.fn(),
    sendMessageOptimistic: jest.fn(),
    updateMessage: jest.fn(),
    deleteMessage: jest.fn(),
    setMessages: jest.fn(),
    isLoading: false,
    setLoading: jest.fn()
  }))
}));

jest.mock('../../store/threadStore', () => ({
  useThreadStore: jest.fn(() => createThreadStoreMock())
}));

jest.mock('../../hooks/useWebSocket', () => ({
  useWebSocket: jest.fn(() => ({
    connectionState: 'connected',
    sendMessage: jest.fn(),
    subscribe: jest.fn(),
    unsubscribe: jest.fn(),
    reconnect: jest.fn(),
    disconnect: jest.fn()
  }))
}));

jest.mock('../../hooks/useThreadSwitching', () => ({
  useThreadSwitching: jest.fn(() => ({
    state: { isLoading: false },
    switchToThread: jest.fn()
  }))
}));

jest.mock('../../hooks/useThreadCreation', () => ({
  useThreadCreation: jest.fn(() => ({
    state: { isLoading: false },
    createAndNavigate: jest.fn()
  }))
}));

// Import components after mocks
import { ThreadSidebar } from '../../components/chat/ThreadSidebar';
import { useThreadStore } from '../../store/threadStore';

describe('Thread Management Tests', () => {
  
  beforeEach(() => {
    setupDefaultMocks();
  });

  afterEach(() => {
    cleanupMocks();
  });

  // ============================================
  // Thread Display Tests
  // ============================================
  describe('Thread Display', () => {
    
    test('4. Should display list of threads', () => {
      const mockThreads = [
        createTestThread({ 
          id: '1', 
          title: 'Thread 1', 
          created_at: '2025-01-01', 
          message_count: 5 
        }),
        createTestThread({ 
          id: '2', 
          title: 'Thread 2', 
          created_at: '2025-01-02', 
          message_count: 10 
        })
      ];
      
      const mockThreadStore = createThreadStoreMock({
        threads: mockThreads,
        currentThreadId: '1',
        setCurrentThreadId: jest.fn()
      });
      
      jest.mocked(useThreadStore).mockReturnValueOnce(mockThreadStore);
      render(<ThreadSidebar />);
      
      expectElementByText('Thread 1');
      expectElementByText('Thread 2');
    });
  });

  // ============================================
  // Thread Selection Tests
  // ============================================
  describe('Thread Selection', () => {
    
    test('5. Should handle thread selection', async () => {
      const mockSetCurrentThread = jest.fn();
      const mockThreads = [
        createTestThread({ id: '1', title: 'Thread 1' }),
        createTestThread({ id: '2', title: 'Thread 2' })
      ];
      
      const mockThreadStore = createThreadStoreMock({
        threads: mockThreads,
        currentThreadId: '1',
        setCurrentThread: mockSetCurrentThread
      });
      
      jest.mocked(useThreadStore).mockReturnValueOnce(mockThreadStore);
      render(<ThreadSidebar />);
      
      const thread2 = findElementByText('Thread 2');
      fireEvent.click(thread2);
      expect(mockSetCurrentThread).toHaveBeenCalled();
    });
  });

  // ============================================
  // Thread Creation Tests
  // ============================================
  describe('Thread Creation', () => {
    
    test('6. Should create new thread', async () => {
      const mockCreateAndNavigate = jest.fn();
      const mockThreadStore = createThreadStoreMock({
        threads: []
      });
      
      // Import the hooks to get access to their mocks
      const { useThreadCreation } = await import('../../hooks/useThreadCreation');
      jest.mocked(useThreadCreation).mockReturnValueOnce({
        state: { isLoading: false },
        createAndNavigate: mockCreateAndNavigate
      });
      
      jest.mocked(useThreadStore).mockReturnValueOnce(mockThreadStore);
      render(<ThreadSidebar />);
      
      const newThreadButton = findElementByRole('button', { name: /new conversation/i });
      fireEvent.click(newThreadButton);
      expect(mockCreateAndNavigate).toHaveBeenCalled();
    });
  });

  // ============================================
  // Thread Deletion Tests
  // ============================================
  describe('Thread Deletion', () => {
    
    test('7. Should delete thread with confirmation', async () => {
      const mockDeleteThread = jest.fn();
      const mockThreads = [
        createTestThread({ id: '1', title: 'Thread to Delete' })
      ];
      
      const mockThreadStore = createThreadStoreMock({
        threads: mockThreads,
        deleteThread: mockDeleteThread
      });
      
      jest.mocked(useThreadStore).mockReturnValueOnce(mockThreadStore);
      render(<ThreadSidebar />);
      
      const deleteButton = expectElementByTestId('delete-thread-1');
      fireEvent.click(deleteButton);
      
      // Confirm deletion
      const confirmButton = await waitForElementByRole('button', { name: /confirm/i });
      fireEvent.click(confirmButton);
      expect(mockDeleteThread).toHaveBeenCalledWith('1');
    });
  });

  // ============================================
  // Thread Lifecycle Integration Tests
  // ============================================
  describe('Thread Lifecycle Integration', () => {
    
    test('Should handle empty thread list', () => {
      const mockThreadStore = createThreadStoreMock({
        threads: [],
        currentThreadId: null
      });
      
      jest.mocked(useThreadStore).mockReturnValueOnce(mockThreadStore);
      render(<ThreadSidebar />);
      
      expectElementByText(/No threads available/i);
    });

    test('Should handle thread loading state', () => {
      const mockThreadStore = createThreadStoreMock({
        threads: [],
        isLoading: true
      });
      
      jest.mocked(useThreadStore).mockReturnValueOnce(mockThreadStore);
      render(<ThreadSidebar />);
      
      expectElementByTestId('thread-loading');
    });

    test('Should highlight current thread', () => {
      const mockThreads = [
        createTestThread({ id: '1', title: 'Thread 1' }),
        createTestThread({ id: '2', title: 'Thread 2' })
      ];
      
      const mockThreadStore = createThreadStoreMock({
        threads: mockThreads,
        currentThreadId: '2'
      });
      
      jest.mocked(useThreadStore).mockReturnValueOnce(mockThreadStore);
      render(<ThreadSidebar />);
      
      const currentThread = expectElementByTestId('thread-2');
      expect(currentThread).toHaveClass('current');
    });

    test('Should handle thread update operations', async () => {
      const mockUpdateThread = jest.fn();
      const mockThreads = [
        createTestThread({ id: '1', title: 'Original Title' })
      ];
      
      const mockThreadStore = createThreadStoreMock({
        threads: mockThreads,
        updateThread: mockUpdateThread
      });
      
      jest.mocked(useThreadStore).mockReturnValueOnce(mockThreadStore);
      render(<ThreadSidebar />);
      
      const editButton = expectElementByTestId('edit-thread-1');
      fireEvent.click(editButton);
      
      const titleInput = expectElementByTestId('thread-title-input');
      fireEvent.change(titleInput, { target: { value: 'Updated Title' } });
      
      const saveButton = expectElementByRole('button', { name: /save/i });
      fireEvent.click(saveButton);
      
      expect(mockUpdateThread).toHaveBeenCalledWith('1', 
        expect.objectContaining({ title: 'Updated Title' })
      );
    });
  });
});