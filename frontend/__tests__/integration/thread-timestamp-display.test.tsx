import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChatHistorySection } from '@/components/ChatHistorySection';
import { ThreadSidebarActions } from '@/components/chat/ThreadSidebarActions';
import { ThreadService } from '@/services/threadService';
import { Thread } from '@/types/thread';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

// Mock all dependencies
jest.mock('next/navigation');
jest.mock('@/store/threadStore');
jest.mock('@/store/chat');
jest.mock('@/store/unified-chat');
jest.mock('@/store/authStore');
jest.mock('@/hooks/useThreadSwitching');
jest.mock('@/hooks/useThreadCreation');
jest.mock('@/hooks/useAuth');
jest.mock('@/services/threadService');

/**
 * Integration tests to prevent timestamp display regression
 * 
 * These tests verify that timestamps are correctly displayed across
 * the entire thread UI, handling both ISO strings and Unix timestamps
 * from the backend correctly.
 */
describe('Thread Timestamp Display - Integration Tests', () => {
  
  setupAntiHang();
  
    jest.setTimeout(10000);
  
  describe('End-to-end timestamp handling', () => {
    
        setupAntiHang();
    
      jest.setTimeout(10000);
    
    it('should correctly display threads with ISO string timestamps from backend', async () => {
      // Mock backend response with ISO string timestamps
      const mockThreadsFromBackend: Thread[] = [
        {
          id: 'thread-1',
          title: 'Recent Thread',
          created_at: new Date().toISOString(), // ISO string format
          updated_at: new Date().toISOString(),
          user_id: 'user-1',
          metadata: {},
        },
        {
          id: 'thread-2',
          title: 'Yesterday Thread',
          created_at: (() => {
            const yesterday = new Date();
            yesterday.setDate(yesterday.getDate() - 1);
            return yesterday.toISOString();
          })(),
          updated_at: (() => {
            const yesterday = new Date();
            yesterday.setDate(yesterday.getDate() - 1);
            return yesterday.toISOString();
          })(),
          user_id: 'user-1',
          metadata: {},
        },
        {
          id: 'thread-3',
          title: 'Old Thread',
          created_at: '2024-01-15T10:30:00.000Z',
          updated_at: '2024-01-15T10:30:00.000Z',
          user_id: 'user-1',
          metadata: {},
        },
      ];
      
      // Setup mock service to return ISO string timestamps
      (ThreadService.listThreads as jest.Mock).mockResolvedValue(mockThreadsFromBackend);
      
      // Mock store states
      const { useThreadStore } = require('@/store/threadStore');
      const { useAuthStore } = require('@/store/authStore');
      const { useChatStore } = require('@/store/chat');
      
      useAuthStore.mockReturnValue({ isAuthenticated: true });
      useThreadStore.mockReturnValue({
        threads: mockThreadsFromBackend,
        currentThreadId: null,
        setThreads: jest.fn(),
        setCurrentThread: jest.fn(),
        addThread: jest.fn(),
        updateThread: jest.fn(),
        deleteThread: jest.fn(),
        setLoading: jest.fn(),
        setError: jest.fn(),
      });
      useChatStore.mockReturnValue({
        clearMessages: jest.fn(),
        loadMessages: jest.fn(),
      });
      
      // Render the component
      const { container } = render(<ChatHistorySection />);
      
      // Wait for threads to load
      await waitFor(() => {
        expect(screen.getByText('Recent Thread')).toBeInTheDocument();
      });
      
      // Verify timestamps are displayed correctly
      expect(screen.getByText('Today')).toBeInTheDocument();
      expect(screen.getByText('Yesterday')).toBeInTheDocument();
      
      // For old thread, should show formatted date
      const dateElements = screen.getAllByText((content, element) => {
        return content.includes('/202') || content.includes('202');
      });
      expect(dateElements.length).toBeGreaterThan(0);
      
      // Ensure no "Invalid Date" or error displays
      expect(screen.queryByText('Invalid date')).not.toBeInTheDocument();
      expect(screen.queryByText('Invalid Date')).not.toBeInTheDocument();
      expect(screen.queryByText('Unknown date')).not.toBeInTheDocument();
    });
    
    it('should correctly display threads with Unix timestamps from backend', async () => {
      // Mock backend response with Unix timestamps (in seconds)
      const now = Date.now();
      const mockThreadsFromBackend: Thread[] = [
        {
          id: 'thread-1',
          title: 'Unix Today',
          created_at: Math.floor(now / 1000) as any, // Unix seconds
          updated_at: Math.floor(now / 1000) as any,
          user_id: 'user-1',
          metadata: {},
        },
        {
          id: 'thread-2',
          title: 'Unix Yesterday',
          created_at: Math.floor((now - 86400000) / 1000) as any, // Yesterday in Unix seconds
          updated_at: Math.floor((now - 86400000) / 1000) as any,
          user_id: 'user-1',
          metadata: {},
        },
        {
          id: 'thread-3',
          title: 'Unix Week Ago',
          created_at: Math.floor((now - 604800000) / 1000) as any, // Week ago in Unix seconds
          updated_at: Math.floor((now - 604800000) / 1000) as any,
          user_id: 'user-1',
          metadata: {},
        },
      ];
      
      // Setup mock service
      (ThreadService.listThreads as jest.Mock).mockResolvedValue(mockThreadsFromBackend);
      
      // Mock store states
      const { useThreadStore } = require('@/store/threadStore');
      const { useAuthStore } = require('@/store/authStore');
      const { useChatStore } = require('@/store/chat');
      
      useAuthStore.mockReturnValue({ isAuthenticated: true });
      useThreadStore.mockReturnValue({
        threads: mockThreadsFromBackend,
        currentThreadId: null,
        setThreads: jest.fn(),
        setCurrentThread: jest.fn(),
        addThread: jest.fn(),
        updateThread: jest.fn(),
        deleteThread: jest.fn(),
        setLoading: jest.fn(),
        setError: jest.fn(),
      });
      useChatStore.mockReturnValue({
        clearMessages: jest.fn(),
        loadMessages: jest.fn(),
      });
      
      // Render the component
      render(<ChatHistorySection />);
      
      // Wait for threads to load
      await waitFor(() => {
        expect(screen.getByText('Unix Today')).toBeInTheDocument();
      });
      
      // Verify timestamps are displayed correctly
      expect(screen.getByText('Today')).toBeInTheDocument();
      expect(screen.getByText('Yesterday')).toBeInTheDocument();
      expect(screen.getByText('7 days ago')).toBeInTheDocument();
      
      // Ensure no "Invalid Date" displays
      expect(screen.queryByText('Invalid date')).not.toBeInTheDocument();
      expect(screen.queryByText('Invalid Date')).not.toBeInTheDocument();
    });
    
    it('should handle mixed timestamp formats from backend gracefully', async () => {
      // Mock backend response with mixed formats
      const mockThreadsFromBackend: Thread[] = [
        {
          id: 'thread-iso',
          title: 'ISO Format Thread',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          user_id: 'user-1',
          metadata: {},
        },
        {
          id: 'thread-unix',
          title: 'Unix Format Thread',
          created_at: Math.floor(Date.now() / 1000) as any,
          updated_at: Math.floor(Date.now() / 1000) as any,
          user_id: 'user-1',
          metadata: {},
        },
        {
          id: 'thread-null',
          title: 'Null Timestamp Thread',
          created_at: null as any,
          updated_at: null as any,
          user_id: 'user-1',
          metadata: {},
        },
        {
          id: 'thread-undefined',
          title: 'Undefined Timestamp Thread',
          created_at: undefined as any,
          updated_at: undefined as any,
          user_id: 'user-1',
          metadata: {},
        },
      ];
      
      // Setup mock service
      (ThreadService.listThreads as jest.Mock).mockResolvedValue(mockThreadsFromBackend);
      
      // Mock store states
      const { useThreadStore } = require('@/store/threadStore');
      const { useAuthStore } = require('@/store/authStore');
      const { useChatStore } = require('@/store/chat');
      
      useAuthStore.mockReturnValue({ isAuthenticated: true });
      useThreadStore.mockReturnValue({
        threads: mockThreadsFromBackend,
        currentThreadId: null,
        setThreads: jest.fn(),
        setCurrentThread: jest.fn(),
        addThread: jest.fn(),
        updateThread: jest.fn(),
        deleteThread: jest.fn(),
        setLoading: jest.fn(),
        setError: jest.fn(),
      });
      useChatStore.mockReturnValue({
        clearMessages: jest.fn(),
        loadMessages: jest.fn(),
      });
      
      // Render the component
      render(<ChatHistorySection />);
      
      // Wait for threads to load
      await waitFor(() => {
        expect(screen.getByText('ISO Format Thread')).toBeInTheDocument();
      });
      
      // Verify all threads are displayed
      expect(screen.getByText('ISO Format Thread')).toBeInTheDocument();
      expect(screen.getByText('Unix Format Thread')).toBeInTheDocument();
      expect(screen.getByText('Null Timestamp Thread')).toBeInTheDocument();
      expect(screen.getByText('Undefined Timestamp Thread')).toBeInTheDocument();
      
      // Verify timestamps handle all formats
      const todayElements = screen.getAllByText('Today');
      expect(todayElements).toHaveLength(2); // ISO and Unix should both show "Today"
      
      const unknownElements = screen.getAllByText('Unknown date');
      expect(unknownElements).toHaveLength(2); // Null and undefined should show "Unknown date"
      
      // No invalid date errors
      expect(screen.queryByText('Invalid date')).not.toBeInTheDocument();
      expect(screen.queryByText('Invalid Date')).not.toBeInTheDocument();
    });
  });
  
  describe('Regression prevention', () => {
    
        setupAntiHang();
    
      jest.setTimeout(10000);
    
    it('should NOT multiply ISO strings by 1000 (prevent timestamp regression)', async () => {
      // This is the critical regression test
      // The bug was: ISO strings were being treated as Unix timestamps and multiplied by 1000
      
      const isoString = '2024-01-15T10:30:00.000Z';
      const mockThread: Thread = {
        id: 'regression-test',
        title: 'Regression Test Thread',
        created_at: isoString,
        updated_at: isoString,
        user_id: 'user-1',
        metadata: {},
      };
      
      // Setup mock service
      (ThreadService.listThreads as jest.Mock).mockResolvedValue([mockThread]);
      
      // Mock store states
      const { useThreadStore } = require('@/store/threadStore');
      const { useAuthStore } = require('@/store/authStore');
      const { useChatStore } = require('@/store/chat');
      
      useAuthStore.mockReturnValue({ isAuthenticated: true });
      useThreadStore.mockReturnValue({
        threads: [mockThread],
        currentThreadId: null,
        setThreads: jest.fn(),
        setCurrentThread: jest.fn(),
        addThread: jest.fn(),
        updateThread: jest.fn(),
        deleteThread: jest.fn(),
        setLoading: jest.fn(),
        setError: jest.fn(),
      });
      useChatStore.mockReturnValue({
        clearMessages: jest.fn(),
        loadMessages: jest.fn(),
      });
      
      // Render the component
      render(<ChatHistorySection />);
      
      // Wait for thread to load
      await waitFor(() => {
        expect(screen.getByText('Regression Test Thread')).toBeInTheDocument();
      });
      
      // The date should be displayed as a valid past date
      // If the bug exists, multiplying by 1000 would create an invalid future date
      
      // Should NOT show "Invalid date"
      expect(screen.queryByText('Invalid date')).not.toBeInTheDocument();
      expect(screen.queryByText('Invalid Date')).not.toBeInTheDocument();
      
      // Should show a reasonable date (either formatted date or "X days ago")
      const dateText = screen.getByText((content, element) => {
        // Check for valid date patterns
        return (
          content.includes('/202') || // Formatted date
          content.includes('202') || // Year in date
          content.includes('days ago') || // Days ago format
          content.includes('months ago') || // Months ago
          content.includes('year') // Years ago
        );
      });
      
      expect(dateText).toBeInTheDocument();
    });
    
    it('should maintain timestamp accuracy when switching between threads', async () => {
      // Test that timestamps remain accurate when navigating between threads
      
      const thread1 = {
        id: 'thread-1',
        title: 'Thread 1',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        user_id: 'user-1',
        metadata: {},
      };
      
      const thread2 = {
        id: 'thread-2',
        title: 'Thread 2',
        created_at: Math.floor(Date.now() / 1000) as any, // Unix timestamp
        updated_at: Math.floor(Date.now() / 1000) as any,
        user_id: 'user-1',
        metadata: {},
      };
      
      // Setup mock service
      (ThreadService.listThreads as jest.Mock).mockResolvedValue([thread1, thread2]);
      
      // Mock store states
      const { useThreadStore } = require('@/store/threadStore');
      const { useAuthStore } = require('@/store/authStore');
      const { useChatStore } = require('@/store/chat');
      
      const mockSetCurrentThread = jest.fn();
      
      useAuthStore.mockReturnValue({ isAuthenticated: true });
      useThreadStore.mockReturnValue({
        threads: [thread1, thread2],
        currentThreadId: null,
        setThreads: jest.fn(),
        setCurrentThread: mockSetCurrentThread,
        addThread: jest.fn(),
        updateThread: jest.fn(),
        deleteThread: jest.fn(),
        setLoading: jest.fn(),
        setError: jest.fn(),
      });
      useChatStore.mockReturnValue({
        clearMessages: jest.fn(),
        loadMessages: jest.fn(),
      });
      
      // Mock ThreadService for messages
      (ThreadService.getThreadMessages as jest.Mock).mockResolvedValue({ messages: [] });
      
      // Render the component
      const { rerender } = render(<ChatHistorySection />);
      
      // Wait for threads to load
      await waitFor(() => {
        expect(screen.getByText('Thread 1')).toBeInTheDocument();
        expect(screen.getByText('Thread 2')).toBeInTheDocument();
      });
      
      // Both should show "Today" initially
      const todayElements = screen.getAllByText('Today');
      expect(todayElements).toHaveLength(2);
      
      // Click on Thread 1
      const thread1Element = screen.getByText('Thread 1');
      await userEvent.click(thread1Element);
      
      // Update mock to show Thread 1 as selected
      useThreadStore.mockReturnValue({
        threads: [thread1, thread2],
        currentThreadId: 'thread-1',
        setThreads: jest.fn(),
        setCurrentThread: mockSetCurrentThread,
        addThread: jest.fn(),
        updateThread: jest.fn(),
        deleteThread: jest.fn(),
        setLoading: jest.fn(),
        setError: jest.fn(),
      });
      
      rerender(<ChatHistorySection />);
      
      // Timestamps should still be correct
      const todayElementsAfter = screen.getAllByText('Today');
      expect(todayElementsAfter).toHaveLength(2);
      
      // No invalid dates should appear
      expect(screen.queryByText('Invalid date')).not.toBeInTheDocument();
      expect(screen.queryByText('Invalid Date')).not.toBeInTheDocument();
    });
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});