import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ThreadList } from '@/components/ThreadList';
import { useChatStore } from '@/store/chat';

// Mock the chat store
jest.mock('@/store/chat');

// Mock fetch for API calls
global.fetch = jest.fn();

describe('ThreadList', () => {
  const mockThreads = [
    {
      id: 'thread-1',
      created_at: 1234567890,
      metadata_: { user_id: 'user-1' },
      messages: [
        { content: [{ text: { value: 'First thread message' } }] }
      ]
    },
    {
      id: 'thread-2',
      created_at: 1234567891,
      metadata_: { user_id: 'user-1' },
      messages: [
        { content: [{ text: { value: 'Second thread message' } }] }
      ]
    }
  ];

  beforeEach(() => {
    jest.clearAllMocks();
    (fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockThreads,
    });
  });

  it('should render thread list', async () => {
    const mockSetActiveThread = jest.fn();
    const mockLoadThreadMessages = jest.fn();
    
    (useChatStore as jest.Mock).mockReturnValue({
      activeThreadId: null,
      setActiveThread: mockSetActiveThread,
      loadThreadMessages: mockLoadThreadMessages,
    });

    render(<ThreadList />);

    await waitFor(() => {
      expect(screen.getByText('Conversations')).toBeInTheDocument();
    });

    // Check if threads are rendered
    expect(screen.getByText('First thread message')).toBeInTheDocument();
    expect(screen.getByText('Second thread message')).toBeInTheDocument();
  });

  it('should handle thread selection', async () => {
    const mockSetActiveThread = jest.fn();
    const mockLoadThreadMessages = jest.fn();
    
    (useChatStore as jest.Mock).mockReturnValue({
      activeThreadId: null,
      setActiveThread: mockSetActiveThread,
      loadThreadMessages: mockLoadThreadMessages,
    });

    // Mock thread messages API call
    (fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockThreads,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [
          {
            id: 'msg-1',
            role: 'user',
            content: [{ text: { value: 'Test message' } }],
            created_at: 123456,
          }
        ],
      });

    render(<ThreadList />);

    await waitFor(() => {
      expect(screen.getByText('First thread message')).toBeInTheDocument();
    });

    // Click on first thread
    fireEvent.click(screen.getByText('First thread message'));

    await waitFor(() => {
      expect(mockSetActiveThread).toHaveBeenCalledWith('thread-1');
    });

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/threads/thread-1/messages'),
      expect.any(Object)
    );
  });

  it('should highlight active thread', async () => {
    (useChatStore as jest.Mock).mockReturnValue({
      activeThreadId: 'thread-1',
      setActiveThread: jest.fn(),
      loadThreadMessages: jest.fn(),
    });

    render(<ThreadList />);

    await waitFor(() => {
      const activeThread = screen.getByText('First thread message').closest('div');
      expect(activeThread).toHaveClass('bg-blue-50');
    });
  });

  it('should handle new thread creation', async () => {
    const mockClearMessages = jest.fn();
    const mockSetActiveThread = jest.fn();
    
    (useChatStore as jest.Mock).mockReturnValue({
      activeThreadId: 'thread-1',
      setActiveThread: mockSetActiveThread,
      loadThreadMessages: jest.fn(),
      clearMessages: mockClearMessages,
    });

    render(<ThreadList />);

    await waitFor(() => {
      expect(screen.getByText('New Chat')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('New Chat'));

    expect(mockSetActiveThread).toHaveBeenCalledWith(null);
    expect(mockClearMessages).toHaveBeenCalled();
  });

  it('should handle empty thread list', async () => {
    (fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => [],
    });

    (useChatStore as jest.Mock).mockReturnValue({
      activeThreadId: null,
      setActiveThread: jest.fn(),
      loadThreadMessages: jest.fn(),
    });

    render(<ThreadList />);

    await waitFor(() => {
      expect(screen.getByText('No conversations yet')).toBeInTheDocument();
    });
  });

  it('should handle API errors gracefully', async () => {
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
    
    (fetch as jest.Mock).mockRejectedValue(new Error('API Error'));

    (useChatStore as jest.Mock).mockReturnValue({
      activeThreadId: null,
      setActiveThread: jest.fn(),
      loadThreadMessages: jest.fn(),
    });

    render(<ThreadList />);

    await waitFor(() => {
      expect(screen.getByText('Failed to load conversations')).toBeInTheDocument();
    });

    expect(consoleSpy).toHaveBeenCalledWith(
      'Failed to fetch threads:',
      expect.any(Error)
    );

    consoleSpy.mockRestore();
  });

  it('should format thread timestamps correctly', async () => {
    const recentThread = {
      id: 'thread-recent',
      created_at: Math.floor(Date.now() / 1000) - 3600, // 1 hour ago
      metadata_: { user_id: 'user-1' },
      messages: [
        { content: [{ text: { value: 'Recent message' } }] }
      ]
    };

    (fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => [recentThread],
    });

    (useChatStore as jest.Mock).mockReturnValue({
      activeThreadId: null,
      setActiveThread: jest.fn(),
      loadThreadMessages: jest.fn(),
    });

    render(<ThreadList />);

    await waitFor(() => {
      expect(screen.getByText('1 hour ago')).toBeInTheDocument();
    });
  });
});