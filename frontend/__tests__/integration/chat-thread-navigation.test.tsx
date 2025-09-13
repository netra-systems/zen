/**
 * Integration Test for Chat Thread Navigation
 * 
 * Business Value Justification (BVJ):
 * - Segment: All (Free, Early, Mid, Enterprise) 
 * - Business Goal: Ensure seamless thread navigation experience
 * - Value Impact: Users can navigate between chat threads without errors
 * - Strategic Impact: Core chat functionality for conversation continuity
 * 
 * Tests complete thread navigation flow including React Error #438 scenarios
 */

import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useRouter } from 'next/navigation';
import ThreadPage from '@/app/chat/[threadId]/page';

// Mock Next.js router
const mockPush = jest.fn();
const mockReplace = jest.fn();

jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    replace: mockReplace,
    prefetch: jest.fn(),
    back: jest.fn(),
    forward: jest.fn(),
    refresh: jest.fn(),
  }),
}));

// Mock store with realistic behavior
const mockSwitchToThread = jest.fn();
const mockStoreActions = {
  activeThreadId: null,
  setActiveThread: jest.fn(),
  setThreadLoading: jest.fn(),
  startThreadLoading: jest.fn(),
  completeThreadLoading: jest.fn(),
  clearMessages: jest.fn(),
  loadMessages: jest.fn(),
  handleWebSocketEvent: jest.fn(),
};

jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: (selector: any) => {
    if (typeof selector === 'function') {
      return selector(mockStoreActions);
    }
    return null;
  },
}));

jest.mock('@/hooks/useThreadSwitching', () => ({
  useThreadSwitching: () => ({
    switchToThread: mockSwitchToThread,
  }),
}));

jest.mock('@/services/urlSyncService', () => ({
  validateThreadId: jest.fn((id) => id && id.length > 0 && !id.includes('invalid')),
}));

jest.mock('@/components/chat/MainChat', () => {
  return function MockMainChat() {
    return <div data-testid="main-chat">Main Chat Component</div>;
  };
});

jest.mock('@/components/AuthGuard', () => ({
  AuthGuard: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, className, initial, animate, ...props }: any) => (
      <div className={className} {...props}>
        {children}
      </div>
    ),
  },
}));

jest.mock('lucide-react', () => ({
  Loader2: ({ className }: { className?: string }) => (
    <div data-testid="loader" className={className}>Loading...</div>
  ),
  AlertCircle: ({ className }: { className?: string }) => (
    <div data-testid="alert-circle" className={className}>Alert</div>
  ),
}));

describe('Chat Thread Navigation Integration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSwitchToThread.mockResolvedValue(true);
  });

  describe('FAILING SCENARIOS - Promise Params (Next.js 15)', () => {
    it('should FAIL to navigate with Promise-based params', async () => {
      const promiseParams = Promise.resolve({ threadId: 'thread_integration_123' });
      
      // This should fail with current React.use() implementation
      expect(() => {
        render(<ThreadPage params={promiseParams} />);
      }).toThrow();
    });

    it('should FAIL thread switching when params Promise fails', async () => {
      const failingPromise = Promise.reject(new Error('Params loading failed'));
      
      expect(() => {
        render(<ThreadPage params={failingPromise} />);
      }).toThrow();
    });

    it('should FAIL when Promise resolves with malformed data', async () => {
      const malformedParams = Promise.resolve({ wrongKey: 'thread_123' });
      
      expect(() => {
        render(<ThreadPage params={malformedParams as any} />);
      }).toThrow();
    });
  });

  describe('Thread Loading Flow Integration', () => {
    it('should show validating state initially with sync params', () => {
      const syncParams = { threadId: 'thread_loading_test' } as any;
      
      render(<ThreadPage params={syncParams} />);
      
      expect(screen.getByText(/validating thread/i)).toBeInTheDocument();
    });

    it('should transition to loading state when thread switching starts', async () => {
      const syncParams = { threadId: 'thread_loading_transition' } as any;
      mockSwitchToThread.mockImplementation(() => 
        new Promise(resolve => setTimeout(() => resolve(true), 100))
      );
      
      render(<ThreadPage params={syncParams} />);
      
      // Should show validating initially
      expect(screen.getByText(/validating thread/i)).toBeInTheDocument();
      
      // Should transition to loading
      await waitFor(() => {
        expect(screen.queryByText(/loading conversation/i)).toBeInTheDocument();
      }, { timeout: 200 });
    });

    it('should show main chat when loading completes successfully', async () => {
      const syncParams = { threadId: 'thread_success_test' } as any;
      mockStoreActions.activeThreadId = 'thread_success_test';
      
      render(<ThreadPage params={syncParams} />);
      
      await waitFor(() => {
        expect(screen.getByTestId('main-chat')).toBeInTheDocument();
      });
    });

    it('should show error state when thread loading fails', async () => {
      const syncParams = { threadId: 'thread_error_test' } as any;
      mockSwitchToThread.mockRejectedValue(new Error('Loading failed'));
      
      render(<ThreadPage params={syncParams} />);
      
      await waitFor(() => {
        expect(screen.getByTestId('alert-circle')).toBeInTheDocument();
        expect(screen.getByText(/unable to load conversation/i)).toBeInTheDocument();
      });
    });
  });

  describe('Error Handling Integration', () => {
    it('should handle invalid thread ID gracefully', async () => {
      const syncParams = { threadId: 'invalid_thread_format' } as any;
      
      render(<ThreadPage params={syncParams} />);
      
      await waitFor(() => {
        expect(screen.getByText(/invalid thread id format/i)).toBeInTheDocument();
      });
    });

    it('should redirect to chat home on error after delay', async () => {
      const syncParams = { threadId: 'invalid_thread_format' } as any;
      
      render(<ThreadPage params={syncParams} />);
      
      // Fast forward timers to trigger redirect
      jest.useFakeTimers();
      
      await waitFor(() => {
        expect(screen.getByText(/invalid thread id format/i)).toBeInTheDocument();
      });
      
      // Fast forward the 3 second timeout
      jest.advanceTimersByTime(3000);
      
      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/chat');
      });
      
      jest.useRealTimers();
    });

    it('should allow manual return to chat from error state', async () => {
      const syncParams = { threadId: 'invalid_thread_format' } as any;
      
      render(<ThreadPage params={syncParams} />);
      
      await waitFor(() => {
        const returnButton = screen.getByText(/return to chat/i);
        expect(returnButton).toBeInTheDocument();
      });
      
      const returnButton = screen.getByText(/return to chat/i);
      fireEvent.click(returnButton);
      
      expect(mockPush).toHaveBeenCalledWith('/chat');
    });
  });

  describe('Thread Switching Integration', () => {
    it('should skip switching if already on correct thread', async () => {
      const syncParams = { threadId: 'current_thread' } as any;
      mockStoreActions.activeThreadId = 'current_thread';
      
      render(<ThreadPage params={syncParams} />);
      
      await waitFor(() => {
        expect(screen.getByTestId('main-chat')).toBeInTheDocument();
      });
      
      // Should not call switchToThread since we're already on the correct thread
      expect(mockSwitchToThread).not.toHaveBeenCalled();
    });

    it('should call switchToThread when thread is different', async () => {
      const syncParams = { threadId: 'new_thread' } as any;
      mockStoreActions.activeThreadId = 'old_thread';
      
      render(<ThreadPage params={syncParams} />);
      
      await waitFor(() => {
        expect(mockSwitchToThread).toHaveBeenCalledWith('new_thread');
      });
    });
  });

  describe('URL Synchronization Integration', () => {
    it('should validate thread ID format before processing', () => {
      const syncParams = { threadId: 'valid_format_123' } as any;
      
      render(<ThreadPage params={syncParams} />);
      
      const { validateThreadId } = require('@/services/urlSyncService');
      expect(validateThreadId).toHaveBeenCalledWith('valid_format_123');
    });

    it('should handle thread ID validation failure', async () => {
      const syncParams = { threadId: 'invalid' } as any;
      
      render(<ThreadPage params={syncParams} />);
      
      await waitFor(() => {
        expect(screen.getByText(/invalid thread id format/i)).toBeInTheDocument();
      });
    });
  });
});

describe('Next.js 15 Compatibility Integration', () => {
  it('should document expected behavior with async params', async () => {
    // This test documents how the component SHOULD work after the fix
    const promiseParams = Promise.resolve({ threadId: 'future_compatible' });
    
    // After fix implementation, this flow should work:
    // 1. Component receives Promise params
    // 2. Component awaits the Promise to get threadId
    // 3. Component proceeds with normal thread loading flow
    
    // For now, we expect this to fail
    expect(() => {
      render(<ThreadPage params={promiseParams} />);
    }).toThrow();
  });
});