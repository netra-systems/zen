import React from 'react';
import { render, screen } from '@testing-library/react';
import { ChatHistorySection } from '@/components/ChatHistorySection';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
ender, screen } from '@testing-library/react';
import { ChatHistorySection } from '@/components/ChatHistorySection';

// Direct module mocking with explicit return values
jest.mock('@/store/authStore', () => ({
  useAuthStore: jest.fn(() => ({
    isAuthenticated: true,
    user: { id: 'user-1', email: 'test@example.com' },
    token: 'mock-token'
  }))
}));

jest.mock('@/store/threadStore', () => ({
  useThreadStore: jest.fn(() => ({
    threads: [
      {
        id: 'thread-1',
        title: 'First Conversation',
        created_at: Math.floor(Date.now() / 1000),
        updated_at: Math.floor(Date.now() / 1000),
        user_id: 'user-1',
        message_count: 5,
        status: 'active',
      }
    ],
    currentThread: null,
    currentThreadId: null,
    loading: false,
    error: null,
    setThreads: jest.fn(),
    setCurrentThread: jest.fn(),
    addThread: jest.fn(),
    updateThread: jest.fn(),
    deleteThread: jest.fn(),
    setLoading: jest.fn(),
    setError: jest.fn(),
  }))
}));

jest.mock('@/store/chat', () => ({
  useChatStore: jest.fn(() => ({
    messages: [],
    clearMessages: jest.fn(),
    loadMessages: jest.fn(),
  }))
}));

jest.mock('@/services/threadService', () => ({
  ThreadService: {
    listThreads: jest.fn().mockResolvedValue([]),
    getThreadMessages: jest.fn().mockResolvedValue({ messages: [] }),
    createThread: jest.fn().mockResolvedValue({ id: 'new-thread', title: 'New' }),
    updateThread: jest.fn().mockResolvedValue({ id: 'updated', title: 'Updated' }),
    deleteThread: jest.fn().mockResolvedValue({ success: true }),
  }
}));

jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
  }),
  usePathname: () => '/chat',
}));

jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => React.createElement('div', props, children),
  },
  AnimatePresence: ({ children }: any) => children,
}));

describe('ChatHistorySection - Authentication', () => {
    jest.setTimeout(10000);
  it('should render authenticated content when user is authenticated', () => {
    render(<ChatHistorySection />);
    
    // Should show the authenticated UI, not the sign-in message
    expect(screen.getByText('Chat History')).toBeInTheDocument();
    expect(screen.queryByText('Sign in to view chats')).not.toBeInTheDocument();
  });

  it('should show New Chat button when authenticated', () => {
    render(<ChatHistorySection />);
    
    expect(screen.getByText('New Chat')).toBeInTheDocument();
  });
});