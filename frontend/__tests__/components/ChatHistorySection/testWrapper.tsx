/**
 * Test wrapper for ChatHistorySection with authenticated context
 * Ensures proper authentication state for testing
 */

import React from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { ChatHistorySection } from '@/components/ChatHistorySection';

// Mock the stores directly in the component's context
const mockAuthenticatedStore = {
  isAuthenticated: true,
  user: { id: 'user-1', email: 'test@example.com' },
  token: 'mock-token'
};

const mockThreadStoreData = {
  threads: [
    {
      id: 'thread-1',
      title: 'First Conversation',
      created_at: Math.floor(Date.now() / 1000),
      updated_at: Math.floor(Date.now() / 1000),
      user_id: 'user-1',
      message_count: 5,
      status: 'active' as const,
    },
    {
      id: 'thread-2',
      title: 'Second Conversation',
      created_at: Math.floor((Date.now() - 86400000) / 1000),
      updated_at: Math.floor((Date.now() - 86400000) / 1000),
      user_id: 'user-1',
      message_count: 3,
      status: 'active' as const,
    },
    {
      id: 'thread-3',
      title: 'Third Conversation',
      created_at: Math.floor((Date.now() - 604800000) / 1000),
      updated_at: Math.floor((Date.now() - 604800000) / 1000),
      user_id: 'user-1',
      message_count: 10,
      status: 'active' as const,
    },
  ],
  currentThread: null,
  currentThreadId: 'thread-1',
  loading: false,
  error: null,
  setThreads: jest.fn(),
  setCurrentThread: jest.fn(),
  addThread: jest.fn(),
  updateThread: jest.fn(),
  deleteThread: jest.fn(),
  setLoading: jest.fn(),
  setError: jest.fn(),
};

const mockChatStoreData = {
  messages: [],
  clearMessages: jest.fn(),
  loadMessages: jest.fn(),
};

// Create authenticated wrapper component
export const AuthenticatedChatHistorySection: React.FC = () => {
  // Force the component to see authenticated state
  React.useEffect(() => {
    // Override the auth store hook to return authenticated state
    const originalUseAuthStore = require('@/store/authStore').useAuthStore;
    jest.mocked(originalUseAuthStore).mockReturnValue(mockAuthenticatedStore);
    
    const originalUseThreadStore = require('@/store/threadStore').useThreadStore;
    jest.mocked(originalUseThreadStore).mockReturnValue(mockThreadStoreData);
    
    const originalUseChatStore = require('@/store/chat').useChatStore;
    jest.mocked(originalUseChatStore).mockReturnValue(mockChatStoreData);
  }, []);

  return <ChatHistorySection />;
};

// Custom render function that ensures authentication
export const renderWithAuth = (
  ui: React.ReactElement = <AuthenticatedChatHistorySection />,
  options?: Omit<RenderOptions, 'wrapper'>
) => {
  return render(ui, options);
};

export { mockAuthenticatedStore, mockThreadStoreData, mockChatStoreData };