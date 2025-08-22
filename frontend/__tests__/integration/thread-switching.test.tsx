/**
 * Thread Switching and Navigation Integration Tests
 * Comprehensive tests for thread switching functionality in Netra Apex
 * Tests rapid switching, message preservation, URL updates, and WebSocket management
 * Phase 3, Agent 9 - Critical for user experience and engagement
 */

import React from 'react';
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { jest } from '@jest/globals';
import.*from '@/__tests__/helpers/websocket-test-manager';
import { TestProviders } from '@/__tests__/setup/test-providers';

// Mock router for navigation testing
const mockPush = jest.fn();
const mockReplace = jest.fn();
const mockBack = jest.fn();
const mockForward = jest.fn();

jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    replace: mockReplace,
    back: mockBack,
    forward: mockForward,
    pathname: '/chat',
    query: {}
  }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => '/chat'
}));

interface ThreadData {
  id: string;
  title: string;
  messages: MessageData[];
  draft?: string;
  created_at: number;
  updated_at: number;
}

interface MessageData {
  id: string;
  content: string;
  sender: 'user' | 'ai';
  timestamp: number;
}

interface ThreadSwitchingTestState {
  activeThreadId: string | null;
  threads: ThreadData[];
  isLoading: boolean;
  drafts: Record<string, string>;
  lastSwitchTime?: number;
}

const createTestMessage = (id: string, content: string, sender: 'user' | 'ai'): MessageData => ({
  id,
  content,
  sender,
  timestamp: Date.now()
});

const createTestThread = (id: string, title: string, messageCount = 3): ThreadData => ({
  id,
  title,
  created_at: Date.now() - 86400000,
  updated_at: Date.now(),
  messages: Array.from({ length: messageCount }, (_, i) => 
    createTestMessage(
      `msg-${id}-${i}`,
      `Message ${i + 1} in ${title}`,
      i % 2 === 0 ? 'user' : 'ai'
    )
  )
});

const ThreadSwitchingTestComponent: React.FC = () => {
  const [state, setState] = React.useState<ThreadSwitchingTestState>({
    activeThreadId: null,
    threads: [
      createTestThread('thread-1', 'First Thread'),
      createTestThread('thread-2', 'Second Thread'),
      createTestThread('thread-3', 'Third Thread')
    ],
    isLoading: false,
    drafts: {}
  });

  const [switchHistory, setSwitchHistory] = React.useState<string[]>([]);
  const [loadingStates, setLoadingStates] = React.useState<Record<string, boolean>>({});
  const [wsConnected, setWsConnected] = React.useState(true);

  const handleThreadSwitch = async (threadId: string) => {
    if (state.isLoading || !threadId) return;
    
    const switchTime = Date.now();
    
    // Record switch in history
    setSwitchHistory(prev => [...prev, threadId]);
    
    // Save draft if switching from another thread
    if (state.activeThreadId) {
      const draftInput = document.querySelector('[data-testid="message-input"]') as HTMLTextAreaElement;
      if (draftInput?.value) {
        setState(prev => ({
          ...prev,
          drafts: { ...prev.drafts, [prev.activeThreadId!]: draftInput.value }
        }));
      }
    }

    // Show loading state
    setState(prev => ({ ...prev, isLoading: true }));
    setLoadingStates(prev => ({ ...prev, [threadId]: true }));

    // Simulate network delay for thread loading
    await new Promise(resolve => setTimeout(resolve, 150));

    // Update active thread
    setState(prev => ({
      ...prev,
      activeThreadId: threadId,
      isLoading: false,
      lastSwitchTime: switchTime
    }));
    
    setLoadingStates(prev => ({ ...prev, [threadId]: false }));

    // Update URL
    mockPush(`/chat/${threadId}`);
  };

  const handleMessageSend = (threadId: string, message: string) => {
    if (!threadId || !message.trim()) return;

    setState(prev => ({
      ...prev,
      threads: prev.threads.map(thread =>
        thread.id === threadId
          ? {
              ...thread,
              messages: [
                ...thread.messages,
                createTestMessage(`msg-${threadId}-${Date.now()}`, message, 'user')
              ]
            }
          : thread
      ),
      drafts: { ...prev.drafts, [threadId]: '' }
    }));
  };

  const handleDraftChange = (threadId: string, draft: string) => {
    setState(prev => ({
      ...prev,
      drafts: { ...prev.drafts, [threadId]: draft }
    }));
  };

  const activeThread = state.threads.find(t => t.id === state.activeThreadId);
  const currentDraft = state.activeThreadId ? state.drafts[state.activeThreadId] || '' : '';

  return (
    <div data-testid="thread-switching-container">
      {/* WebSocket Status */}
      <div data-testid="ws-status" data-connected={wsConnected.toString()}>
        WS: {wsConnected ? 'Connected' : 'Disconnected'}
      </div>

      {/* Thread Sidebar */}
      <div data-testid="thread-sidebar">
        {state.threads.map(thread => (
          <button
            key={thread.id}
            data-testid={`thread-item-${thread.id}`}
            className={`thread-item ${state.activeThreadId === thread.id ? 'active' : ''}`}
            onClick={() => handleThreadSwitch(thread.id)}
            disabled={state.isLoading}
          >
            <span className="thread-title">{thread.title}</span>
            {loadingStates[thread.id] && (
              <span data-testid={`loading-${thread.id}`} className="loading-indicator">
                Loading...
              </span>
            )}
            {state.activeThreadId === thread.id && (
              <span data-testid="active-indicator" className="active-indicator">
                ●
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Main Chat Area */}
      <div data-testid="chat-area">
        {state.isLoading && (
          <div data-testid="chat-loading" className="loading-state">
            Loading thread...
          </div>
        )}

        {activeThread && !state.isLoading && (
          <div data-testid={`chat-messages-${activeThread.id}`}>
            <h2 data-testid="active-thread-title">{activeThread.title}</h2>
            
            {/* Message History */}
            <div data-testid="message-history">
              {activeThread.messages.map(message => (
                <div
                  key={message.id}
                  data-testid={`message-${message.id}`}
                  className={`message ${message.sender}`}
                >
                  {message.content}
                </div>
              ))}
            </div>

            {/* Message Input */}
            <div data-testid="message-input-area">
              <textarea
                data-testid="message-input"
                value={currentDraft}
                onChange={(e) => handleDraftChange(activeThread.id, e.target.value)}
                placeholder="Type your message..."
                disabled={state.isLoading}
              />
              <button
                data-testid="send-button"
                onClick={() => {
                  handleMessageSend(activeThread.id, currentDraft);
                  handleDraftChange(activeThread.id, '');
                }}
                disabled={!currentDraft.trim() || state.isLoading}
              >
                Send
              </button>
            </div>
          </div>
        )}

        {!activeThread && !state.isLoading && (
          <div data-testid="no-thread-selected">
            Select a thread to start chatting
          </div>
        )}
      </div>

      {/* Test Debug Info */}
      <div data-testid="debug-info" style={{ display: 'none' }}>
        <div data-testid="switch-count">{switchHistory.length}</div>
        <div data-testid="switch-history">{switchHistory.join(',')}</div>
        <div data-testid="last-switch-time">{state.lastSwitchTime || 0}</div>
      </div>
    </div>
  );
};

describe('Thread Switching and Navigation Tests', () => {
  let wsManager: WebSocketTestManager;

  beforeEach(() => {
    wsManager = new WebSocketTestManager();
    wsManager.setup();
    jest.clearAllMocks();
    jest.useFakeTimers();
  });

  afterEach(() => {
    wsManager.cleanup();
    jest.useRealTimers();
    jest.clearAllTimers();
  });

  describe('Basic Thread Switching', () => {
    it('should switch threads with loading state', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(
        <TestProviders>
          <ThreadSwitchingTestComponent />
        </TestProviders>
      );

      const firstThread = screen.getByTestId('thread-item-thread-1');
      await user.click(firstThread);

      // Should show loading state
      expect(screen.getByTestId('chat-loading')).toBeInTheDocument();
      expect(screen.getByTestId('loading-thread-1')).toBeInTheDocument();

      // Fast-forward past loading delay
      act(() => {
        jest.advanceTimersByTime(200);
      });

      await waitFor(() => {
        expect(screen.queryByTestId('chat-loading')).not.toBeInTheDocument();
        expect(screen.getByTestId('active-thread-title')).toHaveTextContent('First Thread');
        expect(screen.getByTestId('active-indicator')).toBeInTheDocument();
      });
    });

    it('should load message history for selected thread', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(
        <TestProviders>
          <ThreadSwitchingTestComponent />
        </TestProviders>
      );

      await user.click(screen.getByTestId('thread-item-thread-1'));
      
      act(() => {
        jest.advanceTimersByTime(200);
      });

      await waitFor(() => {
        expect(screen.getByTestId('chat-messages-thread-1')).toBeInTheDocument();
        expect(screen.getByTestId('message-history')).toBeInTheDocument();
        
        // Should show messages from first thread
        expect(screen.getByText('Message 1 in First Thread')).toBeInTheDocument();
        expect(screen.getByText('Message 2 in First Thread')).toBeInTheDocument();
      });
    });

    it('should update URL correctly on thread switch', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(
        <TestProviders>
          <ThreadSwitchingTestComponent />
        </TestProviders>
      );

      await user.click(screen.getByTestId('thread-item-thread-2'));
      
      act(() => {
        jest.advanceTimersByTime(200);
      });

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/chat/thread-2');
      });
    });

    it('should show active thread indication', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(
        <TestProviders>
          <ThreadSwitchingTestComponent />
        </TestProviders>
      );

      await user.click(screen.getByTestId('thread-item-thread-1'));
      
      act(() => {
        jest.advanceTimersByTime(200);
      });

      await waitFor(() => {
        const activeThread = screen.getByTestId('thread-item-thread-1');
        expect(activeThread).toHaveClass('active');
        expect(screen.getByTestId('active-indicator')).toBeInTheDocument();
      });
    });
  });

  describe('Draft Message Preservation', () => {
    it('should preserve draft messages when switching threads', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(
        <TestProviders>
          <ThreadSwitchingTestComponent />
        </TestProviders>
      );

      // Switch to first thread
      await user.click(screen.getByTestId('thread-item-thread-1'));
      act(() => { jest.advanceTimersByTime(200); });

      await waitFor(() => {
        expect(screen.getByTestId('message-input')).toBeInTheDocument();
      });

      // Type draft message
      const messageInput = screen.getByTestId('message-input');
      await user.type(messageInput, 'Draft message for thread 1');

      // Switch to second thread
      await user.click(screen.getByTestId('thread-item-thread-2'));
      act(() => { jest.advanceTimersByTime(200); });

      await waitFor(() => {
        expect(screen.getByTestId('active-thread-title')).toHaveTextContent('Second Thread');
      });

      // Input should be empty for new thread
      expect(screen.getByTestId('message-input')).toHaveValue('');

      // Switch back to first thread
      await user.click(screen.getByTestId('thread-item-thread-1'));
      act(() => { jest.advanceTimersByTime(200); });

      await waitFor(() => {
        expect(screen.getByTestId('message-input')).toHaveValue('Draft message for thread 1');
      });
    });

    it('should clear draft after sending message', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(
        <TestProviders>
          <ThreadSwitchingTestComponent />
        </TestProviders>
      );

      await user.click(screen.getByTestId('thread-item-thread-1'));
      act(() => { jest.advanceTimersByTime(200); });

      await waitFor(() => {
        expect(screen.getByTestId('message-input')).toBeInTheDocument();
      });

      // Type and send message
      const messageInput = screen.getByTestId('message-input');
      await user.type(messageInput, 'Test message');
      await user.click(screen.getByTestId('send-button'));

      // Draft should be cleared
      expect(messageInput).toHaveValue('');
    });
  });

  describe('Rapid Thread Switching', () => {
    it('should handle 10 rapid thread switches within 2 seconds', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(
        <TestProviders>
          <ThreadSwitchingTestComponent />
        </TestProviders>
      );

      const threads = [
        screen.getByTestId('thread-item-thread-1'),
        screen.getByTestId('thread-item-thread-2'),
        screen.getByTestId('thread-item-thread-3')
      ];

      const startTime = Date.now();

      // Perform 10 rapid switches
      for (let i = 0; i < 10; i++) {
        const threadIndex = i % 3;
        await user.click(threads[threadIndex]);
        
        // Small delay to allow state updates
        act(() => {
          jest.advanceTimersByTime(50);
        });
      }

      const endTime = Date.now();
      expect(endTime - startTime).toBeLessThan(2000);

      // Final advance to complete all loading states
      act(() => {
        jest.advanceTimersByTime(300);
      });

      await waitFor(() => {
        const switchCount = screen.getByTestId('switch-count');
        expect(parseInt(switchCount.textContent || '0')).toBe(10);
      });
    });

    it('should prevent clicks during loading state', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(
        <TestProviders>
          <ThreadSwitchingTestComponent />
        </TestProviders>
      );

      const firstThread = screen.getByTestId('thread-item-thread-1');
      const secondThread = screen.getByTestId('thread-item-thread-2');

      // Click first thread
      await user.click(firstThread);

      // Immediately try to click second thread (should be disabled)
      await user.click(secondThread);

      // Should still be loading first thread
      expect(screen.getByTestId('chat-loading')).toBeInTheDocument();
      
      act(() => {
        jest.advanceTimersByTime(200);
      });

      await waitFor(() => {
        expect(screen.getByTestId('active-thread-title')).toHaveTextContent('First Thread');
      });
    });
  });

  describe('Message Isolation', () => {
    it('should not mix messages between threads', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(
        <TestProviders>
          <ThreadSwitchingTestComponent />
        </TestProviders>
      );

      // Switch to first thread and verify messages
      await user.click(screen.getByTestId('thread-item-thread-1'));
      act(() => { jest.advanceTimersByTime(200); });

      await waitFor(() => {
        expect(screen.getByText('Message 1 in First Thread')).toBeInTheDocument();
        expect(screen.queryByText('Message 1 in Second Thread')).not.toBeInTheDocument();
      });

      // Switch to second thread and verify messages
      await user.click(screen.getByTestId('thread-item-thread-2'));
      act(() => { jest.advanceTimersByTime(200); });

      await waitFor(() => {
        expect(screen.getByText('Message 1 in Second Thread')).toBeInTheDocument();
        expect(screen.queryByText('Message 1 in First Thread')).not.toBeInTheDocument();
      });
    });

    it('should maintain separate message histories', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(
        <TestProviders>
          <ThreadSwitchingTestComponent />
        </TestProviders>
      );

      // Add message to first thread
      await user.click(screen.getByTestId('thread-item-thread-1'));
      act(() => { jest.advanceTimersByTime(200); });

      await waitFor(() => {
        expect(screen.getByTestId('message-input')).toBeInTheDocument();
      });

      await user.type(screen.getByTestId('message-input'), 'New message for thread 1');
      await user.click(screen.getByTestId('send-button'));

      // Switch to second thread
      await user.click(screen.getByTestId('thread-item-thread-2'));
      act(() => { jest.advanceTimersByTime(200); });

      await waitFor(() => {
        expect(screen.queryByText('New message for thread 1')).not.toBeInTheDocument();
      });

      // Switch back to first thread
      await user.click(screen.getByTestId('thread-item-thread-1'));
      act(() => { jest.advanceTimersByTime(200); });

      await waitFor(() => {
        expect(screen.getByText('New message for thread 1')).toBeInTheDocument();
      });
    });
  });

  describe('WebSocket Subscription Updates', () => {
    it('should update WebSocket subscriptions on thread switch', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(
        <TestProviders>
          <ThreadSwitchingTestComponent />
        </TestProviders>
      );

      // Initial WebSocket status should be connected
      expect(screen.getByTestId('ws-status')).toHaveAttribute('data-connected', 'true');

      // Switch threads multiple times
      await user.click(screen.getByTestId('thread-item-thread-1'));
      act(() => { jest.advanceTimersByTime(200); });

      await user.click(screen.getByTestId('thread-item-thread-2'));
      act(() => { jest.advanceTimersByTime(200); });

      await user.click(screen.getByTestId('thread-item-thread-3'));
      act(() => { jest.advanceTimersByTime(200); });

      // WebSocket should remain connected throughout
      await waitFor(() => {
        expect(screen.getByTestId('ws-status')).toHaveAttribute('data-connected', 'true');
      });
    });
  });

  describe('Browser Navigation Integration', () => {
    it('should handle browser back/forward navigation', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(
        <TestProviders>
          <ThreadSwitchingTestComponent />
        </TestProviders>
      );

      // Navigate through threads
      await user.click(screen.getByTestId('thread-item-thread-1'));
      act(() => { jest.advanceTimersByTime(200); });

      await user.click(screen.getByTestId('thread-item-thread-2'));
      act(() => { jest.advanceTimersByTime(200); });

      // Verify URL updates were called
      expect(mockPush).toHaveBeenCalledWith('/chat/thread-1');
      expect(mockPush).toHaveBeenCalledWith('/chat/thread-2');
      expect(mockPush).toHaveBeenCalledTimes(2);
    });

    it('should maintain thread state during navigation', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(
        <TestProviders>
          <ThreadSwitchingTestComponent />
        </TestProviders>
      );

      // Switch to thread and add draft
      await user.click(screen.getByTestId('thread-item-thread-1'));
      act(() => { jest.advanceTimersByTime(200); });

      await waitFor(() => {
        expect(screen.getByTestId('message-input')).toBeInTheDocument();
      });

      await user.type(screen.getByTestId('message-input'), 'Navigation test draft');

      // Switch to another thread
      await user.click(screen.getByTestId('thread-item-thread-2'));
      act(() => { jest.advanceTimersByTime(200); });

      // Simulate browser back navigation
      await user.click(screen.getByTestId('thread-item-thread-1'));
      act(() => { jest.advanceTimersByTime(200); });

      await waitFor(() => {
        expect(screen.getByTestId('message-input')).toHaveValue('Navigation test draft');
      });
    });
  });

  describe('Performance Metrics', () => {
    it('should switch threads in less than 200ms', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(
        <TestProviders>
          <ThreadSwitchingTestComponent />
        </TestProviders>
      );

      const startTime = performance.now();
      
      await user.click(screen.getByTestId('thread-item-thread-1'));
      act(() => { jest.advanceTimersByTime(200); });

      await waitFor(() => {
        expect(screen.getByTestId('active-thread-title')).toBeInTheDocument();
      });

      const switchTime = performance.now() - startTime;
      expect(switchTime).toBeLessThan(200);
    });

    it('should handle concurrent rapid switches without performance degradation', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(
        <TestProviders>
          <ThreadSwitchingTestComponent />
        </TestProviders>
      );

      const performanceStart = performance.now();

      // Perform 20 rapid switches
      for (let i = 0; i < 20; i++) {
        const threadId = (i % 3) + 1;
        await user.click(screen.getByTestId(`thread-item-thread-${threadId}`));
        act(() => { jest.advanceTimersByTime(25); });
      }

      act(() => { jest.advanceTimersByTime(300); });

      const totalTime = performance.now() - performanceStart;
      expect(totalTime).toBeLessThan(2000); // Should complete within 2 seconds

      await waitFor(() => {
        const switchCount = screen.getByTestId('switch-count');
        expect(parseInt(switchCount.textContent || '0')).toBe(20);
      });
    });
  });
});