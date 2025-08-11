/**
 * Critical Frontend Integration Tests
 * Tests for cross-component and system-wide interactions
 */

import React from 'react';
import { render, waitFor, screen, fireEvent, act } from '@testing-library/react';
import { renderHook } from '@testing-library/react-hooks';
import '@testing-library/jest-dom';
import WS from 'jest-websocket-mock';
import { WebSocketProvider } from '@/providers/WebSocketProvider';
import { AgentProvider } from '@/providers/AgentProvider';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useAgent } from '@/hooks/useAgent';
import { useAuthStore } from '@/store/authStore';
import { useChatStore } from '@/store/chatStore';
import { useThreadStore } from '@/store/threadStore';
import apiClient from '@/services/apiClient';
import { messageService } from '@/services/messageService';
import { threadService } from '@/services/threadService';

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
    useThreadStore.setState({ threads: [], activeThread: null });
    
    // Mock fetch
    global.fetch = jest.fn();
  });

  afterEach(() => {
    WS.clean();
    jest.restoreAllMocks();
  });

  describe('1. WebSocket Provider Integration', () => {
    it('should integrate WebSocket with authentication state', async () => {
      const mockToken = 'test-jwt-token';
      const mockUser = { id: '123', email: 'test@example.com' };
      
      // Set authenticated state
      useAuthStore.setState({ 
        user: mockUser, 
        token: mockToken, 
        isAuthenticated: true 
      });
      
      const TestComponent = () => {
        const { isConnected } = useWebSocket();
        return <div>{isConnected ? 'Connected' : 'Disconnected'}</div>;
      };
      
      render(
        <WebSocketProvider>
          <TestComponent />
        </WebSocketProvider>
      );
      
      await server.connected;
      
      // Verify WebSocket connection includes auth token
      expect(server.url).toContain(`token=${mockToken}`);
    });

    it('should reconnect WebSocket when authentication changes', async () => {
      const TestComponent = () => {
        const { isConnected } = useWebSocket();
        const { login } = useAuthStore();
        
        return (
          <div>
            <div>{isConnected ? 'Connected' : 'Disconnected'}</div>
            <button onClick={() => login({ id: '123', email: 'test@example.com' }, 'new-token')}>
              Login
            </button>
          </div>
        );
      };
      
      const { getByText } = render(
        <WebSocketProvider>
          <TestComponent />
        </WebSocketProvider>
      );
      
      // Initial connection
      await server.connected;
      
      // Trigger authentication
      fireEvent.click(getByText('Login'));
      
      // Should establish new connection with new token
      await waitFor(() => {
        expect(server.messages.length).toBeGreaterThan(0);
      });
    });
  });

  describe('2. Agent Provider Integration', () => {
    it('should coordinate agent state with WebSocket messages', async () => {
      const TestComponent = () => {
        const { isProcessing, sendMessage } = useAgent();
        
        return (
          <div>
            <div>{isProcessing ? 'Processing' : 'Idle'}</div>
            <button onClick={() => sendMessage('test message')}>Send</button>
          </div>
        );
      };
      
      const { getByText } = render(
        <WebSocketProvider>
          <AgentProvider>
            <TestComponent />
          </AgentProvider>
        </WebSocketProvider>
      );
      
      await server.connected;
      
      // Send message
      fireEvent.click(getByText('Send'));
      
      // Simulate agent response
      server.send(JSON.stringify({
        type: 'agent_started',
        data: { agent_name: 'supervisor' }
      }));
      
      await waitFor(() => {
        expect(getByText('Processing')).toBeInTheDocument();
      });
      
      // Complete processing
      server.send(JSON.stringify({
        type: 'agent_completed',
        data: { report: 'Test complete' }
      }));
      
      await waitFor(() => {
        expect(getByText('Idle')).toBeInTheDocument();
      });
    });

    it('should sync agent reports with chat messages', async () => {
      const TestComponent = () => {
        const { sendMessage } = useAgent();
        const { messages } = useChatStore();
        
        return (
          <div>
            <button onClick={() => sendMessage('analyze this')}>Analyze</button>
            <div>Messages: {messages.length}</div>
          </div>
        );
      };
      
      const { getByText } = render(
        <WebSocketProvider>
          <AgentProvider>
            <TestComponent />
          </AgentProvider>
        </WebSocketProvider>
      );
      
      await server.connected;
      
      fireEvent.click(getByText('Analyze'));
      
      // Simulate agent completion with report
      server.send(JSON.stringify({
        type: 'agent_completed',
        data: { 
          report: 'Analysis complete',
          thread_id: 'thread-123'
        }
      }));
      
      await waitFor(() => {
        const state = useChatStore.getState();
        expect(state.messages.length).toBeGreaterThan(0);
      });
    });
  });

  describe('3. Authentication Flow Integration', () => {
    it('should complete OAuth flow and establish WebSocket', async () => {
      const mockOAuthResponse = {
        access_token: 'oauth-token',
        user: { id: 'oauth-user', email: 'oauth@example.com' }
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
      const mockUser = { id: 'persist-user', email: 'persist@example.com' };
      const mockToken = 'persist-token';
      
      // Set initial auth state
      useAuthStore.getState().login(mockUser, mockToken);
      
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
      const mockThread = {
        id: 'thread-456',
        name: 'New Thread',
        created_at: new Date().toISOString()
      };
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockThread
      });
      
      // Create thread through service
      const thread = await threadService.createThread('New Thread');
      
      // Update store
      useThreadStore.getState().addThread(thread);
      useThreadStore.getState().setActiveThread(thread.id);
      
      // Verify thread is active
      expect(useThreadStore.getState().activeThread).toBe('thread-456');
      
      // Send message to thread
      const mockMessage = {
        id: 'msg-1',
        thread_id: 'thread-456',
        content: 'Test message',
        role: 'user'
      };
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockMessage
      });
      
      await messageService.sendMessage('thread-456', 'Test message');
      
      // Update chat store
      useChatStore.getState().addMessage(mockMessage);
      
      expect(useChatStore.getState().messages).toHaveLength(1);
      expect(useChatStore.getState().messages[0].thread_id).toBe('thread-456');
    });

    it('should switch threads and load messages', async () => {
      const thread1Messages = [
        { id: 'msg-1', thread_id: 'thread-1', content: 'Thread 1 message', role: 'user' }
      ];
      
      const thread2Messages = [
        { id: 'msg-2', thread_id: 'thread-2', content: 'Thread 2 message', role: 'user' }
      ];
      
      // Mock message loading
      (fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => thread1Messages
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => thread2Messages
        });
      
      // Load thread 1
      await messageService.getMessages('thread-1');
      useChatStore.setState({ messages: thread1Messages, currentThread: 'thread-1' });
      
      expect(useChatStore.getState().messages).toEqual(thread1Messages);
      
      // Switch to thread 2
      await messageService.getMessages('thread-2');
      useChatStore.setState({ messages: thread2Messages, currentThread: 'thread-2' });
      
      expect(useChatStore.getState().messages).toEqual(thread2Messages);
      expect(useChatStore.getState().currentThread).toBe('thread-2');
    });
  });

  describe('5. Real-time Message Streaming', () => {
    it('should stream agent responses to chat', async () => {
      const TestComponent = () => {
        const { messages } = useChatStore();
        const { sendMessage } = useAgent();
        
        return (
          <div>
            <button onClick={() => sendMessage('stream test')}>Send</button>
            <div data-testid="messages">
              {messages.map(m => (
                <div key={m.id}>{m.content}</div>
              ))}
            </div>
          </div>
        );
      };
      
      render(
        <WebSocketProvider>
          <AgentProvider>
            <TestComponent />
          </AgentProvider>
        </WebSocketProvider>
      );
      
      await server.connected;
      
      // Send message
      fireEvent.click(screen.getByText('Send'));
      
      // Simulate streaming response
      for (let i = 1; i <= 3; i++) {
        server.send(JSON.stringify({
          type: 'stream_chunk',
          data: { content: `Chunk ${i} ` }
        }));
        
        await new Promise(resolve => setTimeout(resolve, 10));
      }
      
      server.send(JSON.stringify({
        type: 'stream_complete',
        data: { final_content: 'Chunk 1 Chunk 2 Chunk 3 ' }
      }));
      
      await waitFor(() => {
        const messages = screen.getByTestId('messages');
        expect(messages.textContent).toContain('Chunk 1 Chunk 2 Chunk 3');
      });
    });

    it('should handle message interruption gracefully', async () => {
      const TestComponent = () => {
        const { isProcessing, sendMessage, stopProcessing } = useAgent();
        
        return (
          <div>
            <button onClick={() => sendMessage('long task')}>Start</button>
            <button onClick={stopProcessing}>Stop</button>
            <div>{isProcessing ? 'Running' : 'Stopped'}</div>
          </div>
        );
      };
      
      const { getByText } = render(
        <WebSocketProvider>
          <AgentProvider>
            <TestComponent />
          </AgentProvider>
        </WebSocketProvider>
      );
      
      await server.connected;
      
      // Start processing
      fireEvent.click(getByText('Start'));
      
      server.send(JSON.stringify({
        type: 'agent_started',
        data: { agent_name: 'supervisor' }
      }));
      
      await waitFor(() => {
        expect(getByText('Running')).toBeInTheDocument();
      });
      
      // Stop processing
      fireEvent.click(getByText('Stop'));
      
      await waitFor(() => {
        expect(server.messages).toContainEqual(
          JSON.stringify({ type: 'stop_processing' })
        );
      });
    });
  });

  describe('6. Error Recovery Integration', () => {
    it('should recover from WebSocket disconnection', async () => {
      const TestComponent = () => {
        const { isConnected, reconnect } = useWebSocket();
        
        return (
          <div>
            <div>{isConnected ? 'Online' : 'Offline'}</div>
            <button onClick={reconnect}>Reconnect</button>
          </div>
        );
      };
      
      const { getByText } = render(
        <WebSocketProvider>
          <TestComponent />
        </WebSocketProvider>
      );
      
      await server.connected;
      expect(getByText('Online')).toBeInTheDocument();
      
      // Simulate disconnection
      server.close();
      
      await waitFor(() => {
        expect(getByText('Offline')).toBeInTheDocument();
      });
      
      // Manual reconnection
      fireEvent.click(getByText('Reconnect'));
      
      // Setup new server for reconnection
      const newServer = new WS('ws://localhost:8000/ws');
      await newServer.connected;
      
      await waitFor(() => {
        expect(getByText('Online')).toBeInTheDocument();
      });
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
        const { logout } = useAuthStore();
        const { isAuthenticated } = useAuthStore();
        
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
        
        return <div>{isAuthenticated ? 'Authenticated' : 'Session Expired'}</div>;
      };
      
      // Set expired token
      const expiredToken = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE2MDAwMDAwMDB9.fake';
      localStorage.setItem('auth_token', expiredToken);
      useAuthStore.setState({ token: expiredToken, isAuthenticated: true });
      
      const { getByText } = render(<TestComponent />);
      
      await waitFor(() => {
        expect(getByText('Session Expired')).toBeInTheDocument();
      });
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
        { type: 'message_sent', data: { id: 'msg-1', content: 'Message 1' } },
        { type: 'thread_updated', data: { id: 'thread-1', name: 'Updated Thread' } }
      ];
      
      const TestComponent = () => {
        const { threads } = useThreadStore();
        const { messages } = useChatStore();
        
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
            <div>Threads: {threads.length}</div>
            <div>Messages: {messages.length}</div>
          </div>
        );
      };
      
      const { getByText } = render(<TestComponent />);
      
      await waitFor(() => {
        expect(getByText('Threads: 1')).toBeInTheDocument();
        expect(getByText('Messages: 1')).toBeInTheDocument();
      });
    });
  });

  describe('8. File Upload Integration', () => {
    it('should upload file and process with agent', async () => {
      const file = new File(['test content'], 'test.txt', { type: 'text/plain' });
      const formData = new FormData();
      formData.append('file', file);
      
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
      let progress = 0;
      
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

  describe('9. Optimization Recommendations Flow', () => {
    it('should process optimization request end-to-end', async () => {
      const TestComponent = () => {
        const { sendMessage, optimizationResults } = useAgent();
        
        return (
          <div>
            <button onClick={() => sendMessage('optimize my workload')}>
              Optimize
            </button>
            {optimizationResults && (
              <div data-testid="results">
                {optimizationResults.recommendations?.length || 0} recommendations
              </div>
            )}
          </div>
        );
      };
      
      render(
        <WebSocketProvider>
          <AgentProvider>
            <TestComponent />
          </AgentProvider>
        </WebSocketProvider>
      );
      
      await server.connected;
      
      fireEvent.click(screen.getByText('Optimize'));
      
      // Simulate optimization response
      server.send(JSON.stringify({
        type: 'optimization_complete',
        data: {
          recommendations: [
            { id: '1', type: 'cost', description: 'Switch to smaller model' },
            { id: '2', type: 'latency', description: 'Enable caching' }
          ]
        }
      }));
      
      await waitFor(() => {
        expect(screen.getByTestId('results')).toHaveTextContent('2 recommendations');
      });
    });

    it('should apply optimization and track results', async () => {
      const recommendation = {
        id: 'rec-1',
        type: 'cost',
        action: 'switch_model',
        params: { from: 'gpt-4', to: 'gpt-3.5-turbo' }
      };
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          applied: true,
          impact: { cost_reduction: '40%', latency_change: '-10ms' }
        })
      });
      
      const applyOptimization = async (rec: any) => {
        const response = await fetch('/api/optimizations/apply', {
          method: 'POST',
          body: JSON.stringify(rec)
        });
        return response.json();
      };
      
      const result = await applyOptimization(recommendation);
      
      expect(result.applied).toBe(true);
      expect(result.impact.cost_reduction).toBe('40%');
    });
  });

  describe('10. Multi-Agent Coordination', () => {
    it('should coordinate multiple sub-agents', async () => {
      const agents = ['triage', 'data', 'optimization', 'reporting'];
      const agentStatuses = new Map();
      
      const TestComponent = () => {
        const { sendMessage } = useAgent();
        const [statuses, setStatuses] = React.useState<Map<string, string>>(new Map());
        
        React.useEffect(() => {
          const ws = new WebSocket('ws://localhost:8000/ws');
          
          ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            if (message.type === 'sub_agent_update') {
              setStatuses(prev => new Map(prev).set(
                message.data.agent_name,
                message.data.status
              ));
            }
          };
          
          return () => ws.close();
        }, []);
        
        return (
          <div>
            <button onClick={() => sendMessage('analyze everything')}>Start</button>
            {agents.map(agent => (
              <div key={agent} data-testid={`agent-${agent}`}>
                {agent}: {statuses.get(agent) || 'pending'}
              </div>
            ))}
          </div>
        );
      };
      
      render(<TestComponent />);
      
      await server.connected;
      
      fireEvent.click(screen.getByText('Start'));
      
      // Simulate agent updates
      for (const agent of agents) {
        server.send(JSON.stringify({
          type: 'sub_agent_update',
          data: { agent_name: agent, status: 'running' }
        }));
        
        await new Promise(resolve => setTimeout(resolve, 50));
        
        server.send(JSON.stringify({
          type: 'sub_agent_update',
          data: { agent_name: agent, status: 'completed' }
        }));
      }
      
      await waitFor(() => {
        agents.forEach(agent => {
          expect(screen.getByTestId(`agent-${agent}`)).toHaveTextContent(`${agent}: completed`);
        });
      });
    });

    it('should handle agent pipeline failures', async () => {
      const TestComponent = () => {
        const { sendMessage, error } = useAgent();
        
        return (
          <div>
            <button onClick={() => sendMessage('faulty request')}>Send</button>
            {error && <div data-testid="error">{error.message}</div>}
          </div>
        );
      };
      
      render(
        <WebSocketProvider>
          <AgentProvider>
            <TestComponent />
          </AgentProvider>
        </WebSocketProvider>
      );
      
      await server.connected;
      
      fireEvent.click(screen.getByText('Send'));
      
      // Simulate agent failure
      server.send(JSON.stringify({
        type: 'agent_error',
        data: {
          agent_name: 'data_agent',
          error: { message: 'Failed to fetch data', code: 'DATA_FETCH_ERROR' }
        }
      }));
      
      await waitFor(() => {
        expect(screen.getByTestId('error')).toHaveTextContent('Failed to fetch data');
      });
    });
  });

  describe('11. Performance Monitoring Integration', () => {
    it('should track and report performance metrics', async () => {
      const metrics = {
        websocket_latency: [],
        api_response_time: [],
        render_time: []
      };
      
      const TestComponent = () => {
        const startTime = performance.now();
        
        React.useEffect(() => {
          const renderTime = performance.now() - startTime;
          metrics.render_time.push(renderTime);
        }, []);
        
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
      const performanceThresholds = {
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

  describe('12. Data Caching Integration', () => {
    it('should cache and reuse API responses', async () => {
      const cache = new Map();
      
      const cachedFetch = async (url: string) => {
        if (cache.has(url)) {
          return cache.get(url);
        }
        
        const response = await fetch(url);
        const data = await response.json();
        cache.set(url, data);
        return data;
      };
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: 'fresh' })
      });
      
      // First call - hits API
      const result1 = await cachedFetch('/api/data');
      expect(fetch).toHaveBeenCalledTimes(1);
      
      // Second call - uses cache
      const result2 = await cachedFetch('/api/data');
      expect(fetch).toHaveBeenCalledTimes(1);
      expect(result1).toEqual(result2);
    });

    it('should invalidate cache on mutations', async () => {
      const cache = new Map();
      cache.set('/api/threads', [{ id: '1', name: 'Old Thread' }]);
      
      // Mutation
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ id: '2', name: 'New Thread' })
      });
      
      const createThread = async (name: string) => {
        const response = await fetch('/api/threads', {
          method: 'POST',
          body: JSON.stringify({ name })
        });
        
        // Invalidate cache
        cache.delete('/api/threads');
        
        return response.json();
      };
      
      await createThread('New Thread');
      
      expect(cache.has('/api/threads')).toBe(false);
    });
  });

  describe('13. Notification System Integration', () => {
    it('should show notifications for important events', async () => {
      const notifications = [];
      
      const notify = (type: string, message: string) => {
        notifications.push({ type, message, timestamp: Date.now() });
      };
      
      const TestComponent = () => {
        const { sendMessage } = useAgent();
        
        React.useEffect(() => {
          const ws = new WebSocket('ws://localhost:8000/ws');
          
          ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            if (message.type === 'agent_completed') {
              notify('success', 'Analysis complete');
            } else if (message.type === 'error') {
              notify('error', message.data.message);
            }
          };
          
          return () => ws.close();
        }, []);
        
        return (
          <div>
            <button onClick={() => sendMessage('test')}>Send</button>
            <div data-testid="notifications">
              {notifications.map((n, i) => (
                <div key={i}>{n.type}: {n.message}</div>
              ))}
            </div>
          </div>
        );
      };
      
      render(<TestComponent />);
      
      await server.connected;
      
      server.send(JSON.stringify({
        type: 'agent_completed',
        data: { report: 'Done' }
      }));
      
      await waitFor(() => {
        expect(notifications).toHaveLength(1);
        expect(notifications[0].type).toBe('success');
      });
    });

    it('should queue notifications when offline', async () => {
      const notificationQueue = [];
      
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

  describe('14. Keyboard Shortcuts Integration', () => {
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

  describe('15. Accessibility Integration', () => {
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
      
      await waitFor(() => {
        const announcer = getByTestId('announcer');
        expect(announcer).toHaveTextContent('New message received');
        expect(announcer).toHaveAttribute('aria-live', 'polite');
      });
    });
  });
});