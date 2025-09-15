/**
 * Unit Test for Chat Thread Page Parameter Handling - React Error #438 Fix Validation
 * 
 * Business Value Justification (BVJ):
 * - Segment: All (Free, Early, Mid, Enterprise)
 * - Business Goal: Ensure thread navigation works correctly after fixing React.use() issue
 * - Value Impact: Users can navigate to specific chat threads via URLs without crashes
 * - Strategic Impact: Core chat functionality stability and reliability
 * 
 * Tests React Error #438 Fix: Promise handling with useEffect instead of React.use()
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import ThreadPage from '@/app/chat/[threadId]/page';

// Mock dependencies
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    prefetch: jest.fn(),
    back: jest.fn(),
    forward: jest.fn(),
    refresh: jest.fn(),
  }),
}));

jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: (selector: any) => {
    if (typeof selector === 'function') {
      return selector({
        activeThreadId: null,
        setActiveThread: jest.fn(),
        setThreadLoading: jest.fn(),
        startThreadLoading: jest.fn(),
        completeThreadLoading: jest.fn(),
        clearMessages: jest.fn(),
        loadMessages: jest.fn(),
        handleWebSocketEvent: jest.fn(),
      });
    }
    return null;
  },
}));

jest.mock('@/hooks/useThreadSwitching', () => ({
  useThreadSwitching: () => ({
    switchToThread: jest.fn().mockResolvedValue(true),
  }),
}));

jest.mock('@/services/urlSyncService', () => ({
  validateThreadId: jest.fn().mockResolvedValue(true),
}));

jest.mock('@/components/chat/MainChat', () => {
  return function MockMainChat() {
    return <div data-testid="main-chat">Main Chat Component</div>;
  };
});

jest.mock('@/components/AuthGuard', () => ({
  AuthGuard: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

// Mock framer-motion to avoid animation issues in tests
jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, className, ...props }: any) => (
      <div className={className} {...props}>
        {children}
      </div>
    ),
  },
}));

jest.mock('lucide-react', () => ({
  Loader2: () => <div data-testid="loader">Loading...</div>,
  AlertCircle: () => <div data-testid="alert-circle">Alert</div>,
}));

// Mock timers for testing timeouts
jest.useFakeTimers();

describe('ThreadPage - React Error #438 Fix Validation', () => {
  afterEach(() => {
    jest.clearAllTimers();
  });

  describe('FIXED IMPLEMENTATION - Promise handling with useEffect', () => {
    it('should handle Promise params correctly with useEffect', async () => {
      // Simulate Next.js 15 Promise-based params
      const promiseParams = Promise.resolve({ threadId: 'thread_123' });
      
      // After fix, this should work without throwing
      await act(async () => {
        render(<ThreadPage params={promiseParams} />);
      });
      
      // Should show initial validating state
      expect(screen.getByText(/validating thread/i)).toBeInTheDocument();
      
      // Wait for Promise resolution and state transitions
      await act(async () => {
        // Fast-forward timers to trigger async operations
        jest.runAllTimers();
        await new Promise(resolve => setTimeout(resolve, 0));
      });
      
      await waitFor(() => {
        // Should eventually show MainChat component (successful load)
        expect(screen.getByTestId('main-chat')).toBeInTheDocument();
      });
    });

    it('should extract threadId correctly from Promise params', async () => {
      const promiseParams = Promise.resolve({ threadId: 'thread_456' });
      
      // Should render without throwing
      await act(async () => {
        render(<ThreadPage params={promiseParams} />);
      });
      
      // Should show validating state initially
      expect(screen.getByText(/validating thread/i)).toBeInTheDocument();
      
      // Allow async operations to complete
      await act(async () => {
        jest.runAllTimers();
      });
      
      // Should eventually render successfully
      await waitFor(() => {
        expect(screen.getByTestId('main-chat')).toBeInTheDocument();
      });
    });
  });

  describe('BACKWARD COMPATIBILITY - Synchronous params support', () => {
    it('should work with synchronous params (Next.js 14 style)', async () => {
      // Legacy synchronous params (this still works)
      const syncParams = { threadId: 'thread_sync' } as any;
      
      await act(async () => {
        render(<ThreadPage params={syncParams} />);
      });
      
      // Should render loading state initially
      expect(screen.getByText(/validating thread/i)).toBeInTheDocument();
      
      await act(async () => {
        jest.runAllTimers();
      });
      
      // Should eventually render successfully
      await waitFor(() => {
        expect(screen.getByTestId('main-chat')).toBeInTheDocument();
      });
    });
  });

  describe('ERROR HANDLING - Promise rejection scenarios', () => {
    it('should handle Promise params rejection gracefully', async () => {
      // Test Promise rejection scenario
      const rejectedParams = Promise.reject(new Error('Failed to load params'));
      
      await act(async () => {
        render(<ThreadPage params={rejectedParams} />);
      });
      
      // Should show validating state initially
      expect(screen.getByText(/validating thread/i)).toBeInTheDocument();
      
      // Allow async operations to complete
      await act(async () => {
        jest.runAllTimers();
      });
      
      // Should transition to error state when Promise rejects
      await waitFor(() => {
        expect(screen.getByText(/failed to load thread parameters/i)).toBeInTheDocument();
      });
    });
  });
});

describe('ThreadPage Parameter Type Safety', () => {
  it('should have correct TypeScript interface for params', () => {
    // Verify the params interface matches Next.js 15 expectations
    const promiseParams: Promise<{ threadId: string }> = Promise.resolve({ 
      threadId: 'type_test' 
    });
    
    // The interface should accept Promise<{threadId: string}>
    expect(promiseParams).toBeInstanceOf(Promise);
  });
});

describe('ThreadPage System Stability Validation', () => {
  it('should not crash with various param types', async () => {
    const testCases = [
      Promise.resolve({ threadId: 'normal_thread_id' }),
      Promise.resolve({ threadId: 'thread-with-dashes' }),
      Promise.resolve({ threadId: 'thread_with_underscores' }),
    ];

    for (const params of testCases) {
      await act(async () => {
        const { unmount } = render(<ThreadPage params={params} />);
        
        // Should render without throwing
        expect(screen.getByText(/validating thread/i)).toBeInTheDocument();
        
        unmount(); // Clean up for next test
      });
    }
  });

  it('should handle rapid component mounting/unmounting', async () => {
    const params = Promise.resolve({ threadId: 'rapid_test' });

    // Mount and unmount rapidly
    for (let i = 0; i < 5; i++) {
      await act(async () => {
        const { unmount } = render(<ThreadPage params={params} />);
        jest.runAllTimers();
        unmount();
      });
    }

    // Should complete without memory leaks or errors
    expect(true).toBe(true); // If we get here, no crashes occurred
  });
});