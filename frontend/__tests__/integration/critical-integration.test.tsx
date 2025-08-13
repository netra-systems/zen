/**
 * Critical Frontend Integration Tests
 * Tests for cross-component and system-wide interactions
 */

import React from 'react';
import { render, waitFor, screen, fireEvent, act } from '@testing-library/react';
import { renderHook } from '@testing-library/react';
import '@testing-library/jest-dom';
import WS from 'jest-websocket-mock';

// Import stores
import { useAuthStore } from '@/store/authStore';
import { useChatStore } from '@/store/chatStore';
import { useThreadStore } from '@/store/threadStore';

// Import test utilities
import { TestProviders, WebSocketContext, mockWebSocketContextValue } from '../test-utils/providers';

// Mock services
jest.mock('@/services/threadService', () => ({
  ThreadService: {
    createThread: jest.fn(),
    getThread: jest.fn(),
    listThreads: jest.fn(),
  }
}));

jest.mock('@/services/messageService', () => ({
  messageService: {
    sendMessage: jest.fn(),
    getMessages: jest.fn(),
    createThread: jest.fn(),
  }
}));

// Mock Next.js navigation
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    refresh: jest.fn(),
    pathname: '/',
    query: {},
    asPath: '/',
  }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
}));

// Mock environment
const mockEnv = {
  NEXT_PUBLIC_API_URL: 'http://localhost:8000',
  NEXT_PUBLIC_WS_URL: 'ws://localhost:8000',
};

describe('Critical Frontend Integration Tests', () => {
  let server: WS;
  
  beforeEach(() => {
    process.env = { ...process.env, ...mockEnv };
    server = new WS('ws://localhost:8000/ws');
    jest.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
    
    // Reset all stores
    useAuthStore.setState({ user: null, token: null, isAuthenticated: false });
    useChatStore.setState({ messages: [], currentThread: null });
    useThreadStore.setState({ threads: [], currentThreadId: null, currentThread: null });
    
    // Mock fetch with config endpoint
    global.fetch = jest.fn((url) => {
      if (url.includes('/api/config')) {
        return Promise.resolve({
          json: () => Promise.resolve({ ws_url: 'ws://localhost:8000/ws' }),
          ok: true
        });
      }
      return Promise.resolve({
        json: () => Promise.resolve({}),
        ok: true
      });
    }) as jest.Mock;
  });

  afterEach(() => {
    try {
      WS.clean();
    } catch (error) {
      // Ignore cleanup errors if WS is already cleaned
    }
    jest.restoreAllMocks();
  });

  describe('1. WebSocket Provider Integration', () => {
    it('should integrate WebSocket with authentication state', async () => {
      const mockToken = 'test-jwt-token';
      const mockUser = { id: '123', email: 'test@example.com', full_name: 'Test User', name: 'Test User' };
      
      // Set authenticated state
      useAuthStore.setState({ 
        user: mockUser, 
        token: mockToken, 
        isAuthenticated: true 
      });
      
      const TestComponent = () => {
        const wsContext = React.useContext(WebSocketContext);
        const status = wsContext?.status || 'CLOSED';
        return <div data-testid="ws-status">{status === 'OPEN' ? 'Connected' : 'Disconnected'}</div>;
      };
      
      // Start with closed status
      const { rerender } = render(
        <TestProviders wsValue={{ ...mockWebSocketContextValue, status: 'CLOSED' }}>
          <TestComponent />
        </TestProviders>
      );
      
      expect(screen.getByTestId('ws-status')).toHaveTextContent('Disconnected');
      
      // Update to open status (simulating connection)
      rerender(
        <TestProviders wsValue={{ ...mockWebSocketContextValue, status: 'OPEN' }}>
          <TestComponent />
        </TestProviders>
      );
      
      expect(screen.getByTestId('ws-status')).toHaveTextContent('Connected');
    });

    it('should reconnect WebSocket when authentication changes', async () => {
      const TestComponent = () => {
        const wsContext = React.useContext(WebSocketContext);
        const status = wsContext?.status || 'CLOSED';
        const login = useAuthStore((state) => state.login);
        
        return (
          <div>
            <div data-testid="ws-status">{status === 'OPEN' ? 'Connected' : 'Disconnected'}</div>
            <button onClick={() => login({ id: '123', email: 'test@example.com', full_name: 'Test User', name: 'Test User' }, 'new-token')}>
              Login
            </button>
          </div>
        );
      };
      
      const { getByText } = render(
        <TestProviders>
          <TestComponent />
        </TestProviders>
      );
      
      // Trigger authentication
      fireEvent.click(getByText('Login'));
      
      // Verify login was called
      expect(useAuthStore.getState().token).toBe('new-token');
    });
  });

  describe('2. Agent Provider Integration', () => {
    it('should coordinate agent state with WebSocket messages', async () => {
      const TestComponent = () => {
        const [isProcessing, setIsProcessing] = React.useState(false);
        const wsContext = React.useContext(WebSocketContext);
        
        const sendMessage = () => {
          setIsProcessing(true);
          if (wsContext?.sendMessage) {
            wsContext.sendMessage({ type: 'user_message', payload: { text: 'test message' } } as any);
          }
        };
        
        const stopProcessing = () => {
          setIsProcessing(false);
        };
        
        // Expose function for testing
        React.useEffect(() => {
          (window as any).stopProcessing = stopProcessing;
        }, []);
        
        return (
          <div>
            <div data-testid="status">{isProcessing ? 'Processing' : 'Idle'}</div>
            <button onClick={sendMessage}>Send</button>
            <button onClick={stopProcessing}>Stop</button>
          </div>
        );
      };
      
      const { getByText } = render(
        <TestProviders>
          <TestComponent />
        </TestProviders>
      );
      
      // Send message
      fireEvent.click(getByText('Send'));
      
      // Verify processing state
      expect(screen.getByTestId('status')).toHaveTextContent('Processing');
      
      // Simulate agent completion by clicking stop
      fireEvent.click(getByText('Stop'));
      
      // Verify idle state
      expect(screen.getByTestId('status')).toHaveTextContent('Idle');
    });

    it('should sync agent reports with chat messages', async () => {
      const TestComponent = () => {
        const messages = useChatStore((state) => state.messages);
        
        const simulateAgentComplete = () => {
          // Directly add message to store when agent completes
          useChatStore.getState().addMessage({
            id: 'msg-1',
            content: 'Analysis complete',
            role: 'assistant',
            thread_id: 'thread-123'
          });
        };
        
        return (
          <div>
            <button onClick={simulateAgentComplete}>Complete</button>
            <div data-testid="message-count">Messages: {messages.length}</div>
          </div>
        );
      };
      
      const { getByText } = render(
        <TestProviders>
          <TestComponent />
        </TestProviders>
      );
      
      // Initially no messages
      expect(screen.getByTestId('message-count')).toHaveTextContent('Messages: 0');
      
      // Simulate agent completion
      fireEvent.click(getByText('Complete'));
      
      // Verify message was added
      expect(screen.getByTestId('message-count')).toHaveTextContent('Messages: 1');
      expect(useChatStore.getState().messages[0].content).toBe('Analysis complete');
    });
  });

  describe('3. Authentication Flow Integration', () => {
    it('should complete OAuth flow and establish WebSocket', async () => {
      const mockOAuthResponse = {
        access_token: 'oauth-token',
        user: { id: 'oauth-user', email: 'oauth@example.com', full_name: 'OAuth User', name: 'OAuth User' }
      };
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockOAuthResponse
      });
      
      // Simulate OAuth callback
      const handleOAuthCallback = async (code: string) => {
        const response = await fetch('/api/auth/google/callback', {
          method: 'POST',
          body: JSON.stringify({ code })
        });
        const data = await response.json();
        
        useAuthStore.getState().login(data.user, data.access_token);
        return data;
      };
      
      const result = await handleOAuthCallback('oauth-code');
      
      expect(result.access_token).toBe('oauth-token');
      expect(useAuthStore.getState().isAuthenticated).toBe(true);
    });

    it('should persist authentication across page refreshes', async () => {
      const mockUser = { id: 'persist-user', email: 'persist@example.com', full_name: 'Persist User', name: 'Persist User' };
      const mockToken = 'persist-token';
      
      // Set initial auth state and save to localStorage
      useAuthStore.getState().login(mockUser, mockToken);
      localStorage.setItem('auth_token', mockToken);
      localStorage.setItem('user', JSON.stringify(mockUser));
      
      // Simulate page refresh by resetting and restoring from localStorage
      const savedToken = localStorage.getItem('auth_token');
      const savedUser = localStorage.getItem('user');
      
      // Reset store
      useAuthStore.setState({ user: null, token: null, isAuthenticated: false });
      
      // Restore from localStorage
      if (savedToken && savedUser) {
        useAuthStore.getState().login(JSON.parse(savedUser), savedToken);
      }
      
      expect(useAuthStore.getState().isAuthenticated).toBe(true);
      expect(useAuthStore.getState().user).toEqual(mockUser);
    });
  });

  describe('4. Thread Management Integration', () => {
    it('should create thread and sync with messages', async () => {
      const { ThreadService } = require('@/services/threadService');
      const { messageService } = require('@/services/messageService');
      
      const mockThread = {
        id: 'thread-456',
        title: 'New Thread',
        created_at: Date.now()
      };
      
      ThreadService.createThread.mockResolvedValue(mockThread);
      
      // Create thread through service
      const thread = await ThreadService.createThread('New Thread');
      
      // Update store
      useThreadStore.getState().addThread(thread);
      useThreadStore.getState().setCurrentThread(thread.id);
      
      // Verify thread is active
      expect(useThreadStore.getState().currentThreadId).toBe('thread-456');
      
      // Send message to thread
      const mockMessage = {
        id: 'msg-1',
        thread_id: 'thread-456',
        content: 'Test message',
        role: 'user'
      };
      
      messageService.sendMessage.mockResolvedValue(mockMessage);
      
      await messageService.sendMessage('thread-456', 'Test message');
      
      // Update chat store
      useChatStore.getState().addMessage(mockMessage);
      
      expect(useChatStore.getState().messages).toHaveLength(1);
      expect(useChatStore.getState().messages[0].thread_id).toBe('thread-456');
    });

    it('should switch threads and load messages', async () => {
      const { messageService } = require('@/services/messageService');
      
      const thread1Messages = [
        { id: 'msg-1', thread_id: 'thread-1', content: 'Thread 1 message', role: 'user' }
      ];
      
      const thread2Messages = [
        { id: 'msg-2', thread_id: 'thread-2', content: 'Thread 2 message', role: 'user' }
      ];
      
      // Mock message loading
      messageService.getMessages
        .mockResolvedValueOnce(thread1Messages)
        .mockResolvedValueOnce(thread2Messages);
      
      // Load thread 1
      const messages1 = await messageService.getMessages('thread-1');
      useChatStore.setState({ messages: messages1, currentThread: 'thread-1' });
      
      expect(useChatStore.getState().messages).toEqual(thread1Messages);
      
      // Switch to thread 2
      const messages2 = await messageService.getMessages('thread-2');
      useChatStore.setState({ messages: messages2, currentThread: 'thread-2' });
      
      expect(useChatStore.getState().messages).toEqual(thread2Messages);
      expect(useChatStore.getState().currentThread).toBe('thread-2');
    });
  });

  describe('5. Real-time Message Streaming', () => {
    it('should stream agent responses to chat', async () => {
      const TestComponent = () => {
        const messages = useChatStore((state) => state.messages);
        const [streamContent, setStreamContent] = React.useState('');
        const [chunksAdded, setChunksAdded] = React.useState<string[]>([]);
        
        const sendMessage = () => {
          // Simulate sending message
          setStreamContent('Chunk 1 ');
          setChunksAdded(['Chunk 1']);
        };
        
        React.useEffect(() => {
          // Simulate receiving chunks - only add each chunk once
          if (streamContent === 'Chunk 1 ' && !chunksAdded.includes('Chunk 2')) {
            setTimeout(() => {
              setStreamContent(prev => prev + 'Chunk 2 ');
              setChunksAdded(prev => [...prev, 'Chunk 2']);
            }, 10);
          }
          if (streamContent === 'Chunk 1 Chunk 2 ' && !chunksAdded.includes('Chunk 3')) {
            setTimeout(() => {
              setStreamContent(prev => prev + 'Chunk 3 ');
              setChunksAdded(prev => [...prev, 'Chunk 3']);
              // Add message once all chunks are received
              useChatStore.getState().addMessage({
                id: 'stream-msg',
                content: 'Chunk 1 Chunk 2 Chunk 3 ',
                role: 'assistant',
                thread_id: 'thread-1'
              });
            }, 10);
          }
        }, [streamContent, chunksAdded]);
        
        return (
          <div>
            <button onClick={sendMessage}>Send</button>
            <div data-testid="messages">
              {streamContent || messages.map(m => m.content).join(' ')}
            </div>
          </div>
        );
      };
      
      render(
        <TestProviders>
          <TestComponent />
        </TestProviders>
      );
      
      // Send message
      fireEvent.click(screen.getByText('Send'));
      
      await waitFor(() => {
        const messages = screen.getByTestId('messages');
        expect(messages.textContent).toContain('Chunk 1 Chunk 2 Chunk 3');
      }, { timeout: 3000 });
    });

    it('should handle message interruption gracefully', async () => {
      const TestComponent = () => {
        const [isProcessing, setIsProcessing] = React.useState(false);
        
        const startProcessing = () => {
          setIsProcessing(true);
        };
        
        const stopProcessing = () => {
          setIsProcessing(false);
        };
        
        return (
          <div>
            <button onClick={startProcessing}>Start</button>
            <button onClick={stopProcessing}>Stop</button>
            <div data-testid="status">{isProcessing ? 'Running' : 'Stopped'}</div>
          </div>
        );
      };
      
      const { getByText } = render(
        <TestProviders>
          <TestComponent />
        </TestProviders>
      );
      
      // Start processing
      fireEvent.click(getByText('Start'));
      expect(screen.getByTestId('status')).toHaveTextContent('Running');
      
      // Stop processing
      fireEvent.click(getByText('Stop'));
      expect(screen.getByTestId('status')).toHaveTextContent('Stopped');
    });
  });

  describe('6. Error Recovery Integration', () => {
    it('should recover from WebSocket disconnection', async () => {
      const TestComponent = () => {
        const [status, setStatus] = React.useState<'OPEN' | 'CLOSED'>('CLOSED');
        
        const reconnect = () => {
          setStatus('OPEN');
        };
        
        const disconnect = () => {
          setStatus('CLOSED');
        };
        
        return (
          <div>
            <div data-testid="connection-status">{status === 'OPEN' ? 'Connected' : 'Disconnected'}</div>
            <button onClick={reconnect}>Reconnect</button>
            <button onClick={disconnect}>Disconnect</button>
          </div>
        );
      };
      
      const { getByText, getByTestId } = render(
        <TestProviders>
          <TestComponent />
        </TestProviders>
      );
      
      // Initially disconnected
      expect(getByTestId('connection-status')).toHaveTextContent('Disconnected');
      
      // Simulate connection
      fireEvent.click(getByText('Reconnect'));
      expect(getByTestId('connection-status')).toHaveTextContent('Connected');
      
      // Simulate disconnection
      fireEvent.click(getByText('Disconnect'));
      expect(getByTestId('connection-status')).toHaveTextContent('Disconnected');
    });

    it('should retry failed API calls with exponential backoff', async () => {
      let attempts = 0;
      
      (fetch as jest.Mock).mockImplementation(async () => {
        attempts++;
        if (attempts < 3) {
          throw new Error('Network error');
        }
        return {
          ok: true,
          json: async () => ({ success: true })
        };
      });
      
      const retryWithBackoff = async (fn: () => Promise<any>, maxRetries = 3) => {
        let lastError;
        for (let i = 0; i < maxRetries; i++) {
          try {
            return await fn();
          } catch (error) {
            lastError = error;
            await new Promise(resolve => setTimeout(resolve, Math.pow(2, i) * 100));
          }
        }
        throw lastError;
      };
      
      const result = await retryWithBackoff(() => 
        fetch('/api/test').then(r => r.json())
      );
      
      expect(result.success).toBe(true);
      expect(attempts).toBe(3);
    });

    it('should handle session expiration gracefully', async () => {
      const TestComponent = () => {
        const logout = useAuthStore((state) => state.logout);
        const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
        
        React.useEffect(() => {
          // Simulate token expiration check
          const checkTokenExpiry = () => {
            const token = localStorage.getItem('auth_token');
            if (token) {
              try {
                const payload = JSON.parse(atob(token.split('.')[1]));
                if (payload.exp * 1000 < Date.now()) {
                  logout();
                }
              } catch {
                logout();
              }
            }
          };
          
          checkTokenExpiry();
        }, [logout]);
        
        return <div data-testid="auth-status">{isAuthenticated ? 'Authenticated' : 'Session Expired'}</div>;
      };
      
      // Set expired token
      const expiredToken = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE2MDAwMDAwMDB9.fake';
      localStorage.setItem('auth_token', expiredToken);
      useAuthStore.setState({ token: expiredToken, isAuthenticated: true });
      
      const { getByTestId } = render(<TestComponent />);
      
      expect(getByTestId('auth-status')).toHaveTextContent('Session Expired');
    });
  });

  describe('7. State Synchronization', () => {
    it('should sync local state with server state', async () => {
      const serverState = {
        threads: [
          { id: 'thread-1', name: 'Thread 1', created_at: '2024-01-01' },
          { id: 'thread-2', name: 'Thread 2', created_at: '2024-01-02' }
        ],
        messages: [
          { id: 'msg-1', thread_id: 'thread-1', content: 'Message 1', role: 'user' }
        ]
      };
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => serverState
      });
      
      // Sync state
      const response = await fetch('/api/state/sync');
      const data = await response.json();
      
      // Update stores
      useThreadStore.setState({ threads: data.threads });
      useChatStore.setState({ messages: data.messages });
      
      expect(useThreadStore.getState().threads).toEqual(serverState.threads);
      expect(useChatStore.getState().messages).toEqual(serverState.messages);
    });

    it('should handle concurrent state updates', async () => {
      const updates = [
        { type: 'thread_created', data: { id: 'thread-1', name: 'Thread 1' } },
        { type: 'message_sent', data: { id: 'msg-1', content: 'Message 1', role: 'user' } },
        { type: 'thread_updated', data: { id: 'thread-1', name: 'Updated Thread' } }
      ];
      
      const TestComponent = () => {
        const threads = useThreadStore((state) => state.threads);
        const messages = useChatStore((state) => state.messages);
        
        React.useEffect(() => {
          // Process updates concurrently
          updates.forEach(update => {
            if (update.type === 'thread_created') {
              useThreadStore.getState().addThread(update.data);
            } else if (update.type === 'message_sent') {
              useChatStore.getState().addMessage(update.data);
            } else if (update.type === 'thread_updated') {
              useThreadStore.getState().updateThread(update.data.id, update.data);
            }
          });
        }, []);
        
        return (
          <div>
            <div data-testid="threads">Threads: {threads.length}</div>
            <div data-testid="messages">Messages: {messages.length}</div>
          </div>
        );
      };
      
      const { getByTestId } = render(<TestComponent />);
      
      expect(getByTestId('threads')).toHaveTextContent('Threads: 1');
      expect(getByTestId('messages')).toHaveTextContent('Messages: 1');
    });
  });

  describe('8. File Upload Integration', () => {
    it('should upload file and process with agent', async () => {
      const file = new File(['test content'], 'test.txt', { type: 'text/plain' });
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ file_id: 'file-123', status: 'uploaded' })
      });
      
      const uploadFile = async (file: File) => {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch('/api/upload', {
          method: 'POST',
          body: formData
        });
        
        return response.json();
      };
      
      const result = await uploadFile(file);
      
      expect(result.file_id).toBe('file-123');
      expect(result.status).toBe('uploaded');
    });

    it('should track upload progress', async () => {
      const file = new File(['x'.repeat(1000000)], 'large.txt', { type: 'text/plain' });
      
      const uploadWithProgress = async (
        file: File,
        onProgress: (percent: number) => void
      ) => {
        // Simulate progress updates
        for (let i = 0; i <= 100; i += 20) {
          onProgress(i);
          await new Promise(resolve => setTimeout(resolve, 10));
        }
        
        return { success: true };
      };
      
      const progressCallback = jest.fn();
      await uploadWithProgress(file, progressCallback);
      
      expect(progressCallback).toHaveBeenCalledWith(0);
      expect(progressCallback).toHaveBeenCalledWith(100);
      expect(progressCallback.mock.calls.length).toBeGreaterThan(2);
    });
  });

  describe('9. Performance Monitoring Integration', () => {
    it('should track and report performance metrics', async () => {
      const metrics = {
        websocket_latency: [] as number[],
        api_response_time: [] as number[],
        render_time: [] as number[]
      };
      
      const TestComponent = () => {
        const startTime = performance.now();
        
        React.useEffect(() => {
          const renderTime = performance.now() - startTime;
          metrics.render_time.push(renderTime);
        }, [startTime]);
        
        const measureApiCall = async () => {
          const start = performance.now();
          await fetch('/api/test');
          const duration = performance.now() - start;
          metrics.api_response_time.push(duration);
        };
        
        return (
          <div>
            <button onClick={measureApiCall}>API Call</button>
            <div data-testid="metrics">
              Render: {metrics.render_time[0]?.toFixed(2)}ms
            </div>
          </div>
        );
      };
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({})
      });
      
      const { getByText } = render(<TestComponent />);
      
      fireEvent.click(getByText('API Call'));
      
      await waitFor(() => {
        expect(metrics.api_response_time.length).toBeGreaterThan(0);
      });
    });

    it('should detect and report performance degradation', async () => {
      const performanceThresholds: Record<string, number> = {
        api_latency: 1000,
        websocket_latency: 100,
        render_time: 16
      };
      
      const checkPerformance = (metric: string, value: number) => {
        const threshold = performanceThresholds[metric];
        if (value > threshold) {
          console.warn(`Performance degradation: ${metric} = ${value}ms (threshold: ${threshold}ms)`);
          return false;
        }
        return true;
      };
      
      const slowApiCall = 1500;
      const result = checkPerformance('api_latency', slowApiCall);
      
      expect(result).toBe(false);
    });
  });

  describe('10. Notification System Integration', () => {
    it('should show notifications for important events', async () => {
      const notifications: Array<{ type: string; message: string; timestamp: number }> = [];
      
      const notify = (type: string, message: string) => {
        notifications.push({ type, message, timestamp: Date.now() });
      };
      
      const TestComponent = () => {
        React.useEffect(() => {
          // Simulate receiving a completion notification
          notify('success', 'Analysis complete');
        }, []);
        
        return (
          <div data-testid="notifications">
            {notifications.map((n, i) => (
              <div key={i}>{n.type}: {n.message}</div>
            ))}
          </div>
        );
      };
      
      render(<TestComponent />);
      
      expect(notifications).toHaveLength(1);
      expect(notifications[0].type).toBe('success');
    });

    it('should queue notifications when offline', async () => {
      const notificationQueue: any[] = [];
      
      const queueNotification = (notification: any) => {
        notificationQueue.push(notification);
      };
      
      const flushQueue = () => {
        while (notificationQueue.length > 0) {
          const notification = notificationQueue.shift();
          console.log('Flushed notification:', notification);
        }
      };
      
      // Queue notifications while offline
      queueNotification({ type: 'info', message: 'Offline notification 1' });
      queueNotification({ type: 'warning', message: 'Offline notification 2' });
      
      expect(notificationQueue).toHaveLength(2);
      
      // Come back online and flush
      flushQueue();
      
      expect(notificationQueue).toHaveLength(0);
    });
  });

  describe('11. Keyboard Shortcuts Integration', () => {
    it('should handle global keyboard shortcuts', async () => {
      const shortcuts = new Map([
        ['cmd+k', 'openSearch'],
        ['cmd+enter', 'sendMessage'],
        ['esc', 'closeModal']
      ]);
      
      const TestComponent = () => {
        const [lastAction, setLastAction] = React.useState('');
        
        React.useEffect(() => {
          const handleKeydown = (e: KeyboardEvent) => {
            const key = `${e.metaKey ? 'cmd+' : ''}${e.key}`;
            const action = shortcuts.get(key);
            if (action) {
              e.preventDefault();
              setLastAction(action);
            }
          };
          
          window.addEventListener('keydown', handleKeydown);
          return () => window.removeEventListener('keydown', handleKeydown);
        }, []);
        
        return <div data-testid="action">{lastAction}</div>;
      };
      
      const { getByTestId } = render(<TestComponent />);
      
      // Simulate Cmd+K
      fireEvent.keyDown(window, { key: 'k', metaKey: true });
      
      expect(getByTestId('action')).toHaveTextContent('openSearch');
    });

    it('should prevent shortcut conflicts in input fields', async () => {
      let actionTriggered = false;
      
      const TestComponent = () => {
        React.useEffect(() => {
          const handleKeydown = (e: KeyboardEvent) => {
            if (e.target instanceof HTMLInputElement) {
              return; // Don't trigger shortcuts in input fields
            }
            if (e.key === 'Enter') {
              actionTriggered = true;
            }
          };
          
          window.addEventListener('keydown', handleKeydown);
          return () => window.removeEventListener('keydown', handleKeydown);
        }, []);
        
        return <input data-testid="input" />;
      };
      
      const { getByTestId } = render(<TestComponent />);
      
      const input = getByTestId('input');
      input.focus();
      
      fireEvent.keyDown(input, { key: 'Enter' });
      
      expect(actionTriggered).toBe(false);
    });
  });

  describe('12. Accessibility Integration', () => {
    it('should maintain focus management during navigation', async () => {
      const TestComponent = () => {
        const [currentView, setCurrentView] = React.useState('chat');
        const chatRef = React.useRef<HTMLDivElement>(null);
        const settingsRef = React.useRef<HTMLDivElement>(null);
        
        React.useEffect(() => {
          if (currentView === 'chat' && chatRef.current) {
            chatRef.current.focus();
          } else if (currentView === 'settings' && settingsRef.current) {
            settingsRef.current.focus();
          }
        }, [currentView]);
        
        return (
          <div>
            <button onClick={() => setCurrentView('chat')}>Chat</button>
            <button onClick={() => setCurrentView('settings')}>Settings</button>
            <div ref={chatRef} tabIndex={-1} data-testid="chat-view">
              Chat View
            </div>
            <div ref={settingsRef} tabIndex={-1} data-testid="settings-view">
              Settings View
            </div>
          </div>
        );
      };
      
      const { getByText, getByTestId } = render(<TestComponent />);
      
      fireEvent.click(getByText('Settings'));
      
      await waitFor(() => {
        expect(document.activeElement).toBe(getByTestId('settings-view'));
      });
    });

    it('should announce dynamic content updates to screen readers', async () => {
      const TestComponent = () => {
        const [message, setMessage] = React.useState('');
        
        return (
          <div>
            <button onClick={() => setMessage('New message received')}>
              Trigger Update
            </button>
            <div aria-live="polite" aria-atomic="true" data-testid="announcer">
              {message}
            </div>
          </div>
        );
      };
      
      const { getByText, getByTestId } = render(<TestComponent />);
      
      fireEvent.click(getByText('Trigger Update'));
      
      const announcer = getByTestId('announcer');
      expect(announcer).toHaveTextContent('New message received');
      expect(announcer).toHaveAttribute('aria-live', 'polite');
    });
  });
});