import React from 'react';
import { render, screen } from '@testing-library/react';
import { ChatHistorySection } from '@/components/ChatHistorySection';
import { useThreadStore } from '@/store/threadStore';
import { useChatStore } from '@/store/chat';
import { useAuthStore } from '@/store/authStore';
import { ThreadService } from '@/services/threadService';

// Mock dependencies
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(() => ({ push: jest.fn() })),
  usePathname: jest.fn(() => '/chat'),
}));

jest.mock('@/store/threadStore');
jest.mock('@/store/chat');
jest.mock('@/store/authStore');
jest.mock('@/services/threadService');
jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    button: ({ children, ...props }: any) => <button {...props}>{children}</button>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

describe('ChatHistorySection - Timestamp Handling', () => {
      setupAntiHang();
    jest.setTimeout(10000);
  const mockThreads = [
    {
      id: 'thread-1',
      title: 'Test Thread 1',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
    {
      id: 'thread-2', 
      title: 'Test Thread 2',
      created_at: '2024-01-15T10:30:00.000Z',
      updated_at: '2024-01-15T10:30:00.000Z',
    },
  ];

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Setup default mocks
    (useAuthStore as jest.Mock).mockReturnValue({
      isAuthenticated: true,
    });
    
    (useThreadStore as jest.Mock).mockReturnValue({
      threads: mockThreads,
      currentThreadId: null,
      setThreads: jest.fn(),
      setCurrentThread: jest.fn(),
      addThread: jest.fn(),
      updateThread: jest.fn(),
      deleteThread: jest.fn(),
      setLoading: jest.fn(),
      setError: jest.fn(),
    });
    
    (useChatStore as jest.Mock).mockReturnValue({
      clearMessages: jest.fn(),
      loadMessages: jest.fn(),
    });
    
    (ThreadService.listThreads as jest.Mock).mockResolvedValue(mockThreads);
  });

  describe('formatDate function behavior', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should correctly display ISO string timestamps', () => {
      const today = new Date();
      const todayThread = {
        ...mockThreads[0],
        created_at: today.toISOString(),
      };
      
      (useThreadStore as jest.Mock).mockReturnValue({
        threads: [todayThread],
        currentThreadId: null,
        setThreads: jest.fn(),
        setCurrentThread: jest.fn(),
        addThread: jest.fn(),
        updateThread: jest.fn(),
        deleteThread: jest.fn(),
        setLoading: jest.fn(),
        setError: jest.fn(),
      });
      
      render(<ChatHistorySection />);
      
      // Should show "Today" for thread created today
      expect(screen.getByText('Today')).toBeInTheDocument();
    });

    it('should correctly display yesterday timestamp', () => {
      const yesterday = new Date();
      yesterday.setDate(yesterday.getDate() - 1);
      
      const yesterdayThread = {
        ...mockThreads[0],
        created_at: yesterday.toISOString(),
      };
      
      (useThreadStore as jest.Mock).mockReturnValue({
        threads: [yesterdayThread],
        currentThreadId: null,
        setThreads: jest.fn(),
        setCurrentThread: jest.fn(),
        addThread: jest.fn(),
        updateThread: jest.fn(),
        deleteThread: jest.fn(),
        setLoading: jest.fn(),
        setError: jest.fn(),
      });
      
      render(<ChatHistorySection />);
      
      expect(screen.getByText('Yesterday')).toBeInTheDocument();
    });

    it('should correctly display days ago for recent dates', () => {
      const threeDaysAgo = new Date();
      threeDaysAgo.setDate(threeDaysAgo.getDate() - 3);
      
      const recentThread = {
        ...mockThreads[0],
        created_at: threeDaysAgo.toISOString(),
      };
      
      (useThreadStore as jest.Mock).mockReturnValue({
        threads: [recentThread],
        currentThreadId: null,
        setThreads: jest.fn(),
        setCurrentThread: jest.fn(),
        addThread: jest.fn(),
        updateThread: jest.fn(),
        deleteThread: jest.fn(),
        setLoading: jest.fn(),
        setError: jest.fn(),
      });
      
      render(<ChatHistorySection />);
      
      expect(screen.getByText('3 days ago')).toBeInTheDocument();
    });

    it('should correctly display full date for older dates', () => {
      const oldDate = new Date('2024-01-15T10:30:00.000Z');
      
      const oldThread = {
        ...mockThreads[0],
        created_at: oldDate.toISOString(),
      };
      
      (useThreadStore as jest.Mock).mockReturnValue({
        threads: [oldThread],
        currentThreadId: null,
        setThreads: jest.fn(),
        setCurrentThread: jest.fn(),
        addThread: jest.fn(),
        updateThread: jest.fn(),
        deleteThread: jest.fn(),
        setLoading: jest.fn(),
        setError: jest.fn(),
      });
      
      render(<ChatHistorySection />);
      
      // Should display as localized date string
      const dateElement = screen.getByText((content, element) => {
        return content.includes('/202') || content.includes('202');
      });
      expect(dateElement).toBeInTheDocument();
    });
  });

  describe('Regression prevention tests', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should NOT multiply ISO string timestamps by 1000', () => {
      // This test ensures ISO strings are not treated as Unix timestamps
      const isoString = '2024-01-15T10:30:00.000Z';
      
      const threadWithIsoString = {
        ...mockThreads[0],
        created_at: isoString,
      };
      
      (useThreadStore as jest.Mock).mockReturnValue({
        threads: [threadWithIsoString],
        currentThreadId: null,
        setThreads: jest.fn(),
        setCurrentThread: jest.fn(),
        addThread: jest.fn(),
        updateThread: jest.fn(),
        deleteThread: jest.fn(),
        setLoading: jest.fn(),
        setError: jest.fn(),
      });
      
      render(<ChatHistorySection />);
      
      // Should not show "Invalid date" or "Unknown date"
      expect(screen.queryByText('Invalid date')).not.toBeInTheDocument();
      expect(screen.queryByText('Unknown date')).not.toBeInTheDocument();
      
      // Should show a valid date representation
      const dateElement = screen.getByText((content, element) => {
        return content.includes('ago') || content.includes('/') || content.includes('202');
      });
      expect(dateElement).toBeInTheDocument();
    });

    it('should handle Unix timestamps in seconds correctly', () => {
      // Unix timestamp for a recent date (in seconds)
      const unixSeconds = Math.floor(Date.now() / 1000);
      
      const threadWithUnixTimestamp = {
        ...mockThreads[0],
        created_at: unixSeconds,
      };
      
      (useThreadStore as jest.Mock).mockReturnValue({
        threads: [threadWithUnixTimestamp],
        currentThreadId: null,
        setThreads: jest.fn(),
        setCurrentThread: jest.fn(),
        addThread: jest.fn(),
        updateThread: jest.fn(),
        deleteThread: jest.fn(),
        setLoading: jest.fn(),
        setError: jest.fn(),
      });
      
      render(<ChatHistorySection />);
      
      // Should show "Today" for current Unix timestamp
      expect(screen.getByText('Today')).toBeInTheDocument();
    });

    it('should handle null timestamps gracefully', () => {
      const threadWithNullTimestamp = {
        ...mockThreads[0],
        created_at: null,
      };
      
      (useThreadStore as jest.Mock).mockReturnValue({
        threads: [threadWithNullTimestamp],
        currentThreadId: null,
        setThreads: jest.fn(),
        setCurrentThread: jest.fn(),
        addThread: jest.fn(),
        updateThread: jest.fn(),
        deleteThread: jest.fn(),
        setLoading: jest.fn(),
        setError: jest.fn(),
      });
      
      render(<ChatHistorySection />);
      
      // Should show "Unknown date" for null timestamps
      expect(screen.getByText('Unknown date')).toBeInTheDocument();
    });

    it('should handle undefined timestamps gracefully', () => {
      const threadWithUndefinedTimestamp = {
        ...mockThreads[0],
        created_at: undefined,
      };
      
      (useThreadStore as jest.Mock).mockReturnValue({
        threads: [threadWithUndefinedTimestamp],
        currentThreadId: null,
        setThreads: jest.fn(),
        setCurrentThread: jest.fn(),
        addThread: jest.fn(),
        updateThread: jest.fn(),
        deleteThread: jest.fn(),
        setLoading: jest.fn(),
        setError: jest.fn(),
      });
      
      render(<ChatHistorySection />);
      
      // Should show "Unknown date" for undefined timestamps
      expect(screen.getByText('Unknown date')).toBeInTheDocument();
    });

    it('should handle invalid date strings gracefully', () => {
      const threadWithInvalidDate = {
        ...mockThreads[0],
        created_at: 'not-a-valid-date',
      };
      
      (useThreadStore as jest.Mock).mockReturnValue({
        threads: [threadWithInvalidDate],
        currentThreadId: null,
        setThreads: jest.fn(),
        setCurrentThread: jest.fn(),
        addThread: jest.fn(),
        updateThread: jest.fn(),
        deleteThread: jest.fn(),
        setLoading: jest.fn(),
        setError: jest.fn(),
      });
      
      render(<ChatHistorySection />);
      
      // Should show "Unknown date" for invalid date strings
      expect(screen.getByText('Unknown date')).toBeInTheDocument();
    });

    it('should handle mixed timestamp formats in the same list', () => {
      const mixedThreads = [
        {
          id: 'thread-1',
          title: 'ISO String Thread',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
        {
          id: 'thread-2',
          title: 'Unix Timestamp Thread',
          created_at: Math.floor(Date.now() / 1000),
          updated_at: Math.floor(Date.now() / 1000),
        },
        {
          id: 'thread-3',
          title: 'Null Timestamp Thread',
          created_at: null,
          updated_at: null,
        },
      ];
      
      (useThreadStore as jest.Mock).mockReturnValue({
        threads: mixedThreads,
        currentThreadId: null,
        setThreads: jest.fn(),
        setCurrentThread: jest.fn(),
        addThread: jest.fn(),
        updateThread: jest.fn(),
        deleteThread: jest.fn(),
        setLoading: jest.fn(),
        setError: jest.fn(),
      });
      
      render(<ChatHistorySection />);
      
      // Should handle all formats correctly
      expect(screen.getAllByText('Today')).toHaveLength(2); // ISO and Unix
      expect(screen.getByText('Unknown date')).toBeInTheDocument(); // Null
    });
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});