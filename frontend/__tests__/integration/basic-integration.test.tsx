/**
 * Basic Frontend Integration Tests
 * Essential integration tests for core functionality
 */

import React from 'react';
import { render, waitFor, screen, fireEvent, act } from '@testing-library/react';
import { renderHook } from '@testing-library/react';
import '@testing-library/jest-dom';
import WS from 'jest-websocket-mock';

import { AgentProvider } from '@/providers/AgentProvider';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useAgent } from '@/hooks/useAgent';
import { useAuthStore } from '@/store/authStore';
import { useChatStore } from '@/store/chatStore';
import { useThreadStore } from '@/store/threadStore';
import apiClient from '@/services/apiClient';

import { TestProviders } from '../test-utils/providers';

// Mock Next.js
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    refresh: jest.fn(),
    back: jest.fn(),
    forward: jest.fn(),
    pathname: '/',
    query: {},
    asPath: '/',
  }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
}));

describe('Basic Frontend Integration Tests', () => {
  let server: WS;
  
  beforeEach(() => {
    process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000';
    process.env.NEXT_PUBLIC_WS_URL = 'ws://localhost:8000';
    server = new WS('ws://localhost:8000/ws');
    jest.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
    
    // Reset stores
    useAuthStore.setState({ user: null, token: null, isAuthenticated: false });
    useChatStore.setState({ messages: [], currentThread: null });
    useThreadStore.setState({ threads: [], currentThread: null, currentThreadId: null });
    
    global.fetch = jest.fn();
  });

  afterEach(() => {
    WS.clean();
    jest.restoreAllMocks();
  });

  describe('Authentication Flow', () => {
    it('should handle login and authentication', async () => {
      const mockUser = { id: '123', email: 'test@example.com', name: 'Test User' };
      const mockToken = 'test-jwt-token';
      
      const LoginComponent = () => {
        const { login, isAuthenticated, user } = useAuthStore();
        
        const handleLogin = async () => {
          await login(mockUser, mockToken);
        };
        
        return (
          <div>
            <button onClick={handleLogin}>Login</button>
            <div data-testid="auth-status">
              {isAuthenticated ? `Logged in as ${user?.email}` : 'Not logged in'}
            </div>
          </div>
        );
      };
      
      const { getByText, getByTestId } = render(<LoginComponent />);
      
      expect(getByTestId('auth-status')).toHaveTextContent('Not logged in');
      
      fireEvent.click(getByText('Login'));
      
      await waitFor(() => {
        expect(getByTestId('auth-status')).toHaveTextContent('Logged in as test@example.com');
      });
      
      expect(useAuthStore.getState().isAuthenticated).toBe(true);
      expect(useAuthStore.getState().token).toBe(mockToken);
    });

    it('should handle logout and cleanup', async () => {
      // Set initial authenticated state
      useAuthStore.setState({
        user: { id: '123', email: 'test@example.com' },
        token: 'test-token',
        isAuthenticated: true
      });
      
      const LogoutComponent = () => {
        const { logout, isAuthenticated } = useAuthStore();
        
        return (
          <div>
            <button onClick={logout}>Logout</button>
            <div data-testid="auth-status">
              {isAuthenticated ? 'Logged in' : 'Logged out'}
            </div>
          </div>
        );
      };
      
      const { getByText, getByTestId } = render(<LogoutComponent />);
      
      expect(getByTestId('auth-status')).toHaveTextContent('Logged in');
      
      fireEvent.click(getByText('Logout'));
      
      await waitFor(() => {
        expect(getByTestId('auth-status')).toHaveTextContent('Logged out');
      });
      
      expect(useAuthStore.getState().isAuthenticated).toBe(false);
      expect(useAuthStore.getState().token).toBeNull();
    });
  });

  describe('WebSocket Connection', () => {
    it('should establish WebSocket connection', async () => {
      const TestComponent = () => {
        const [connected, setConnected] = React.useState(false);
        
        React.useEffect(() => {
          const ws = new WebSocket('ws://localhost:8000/ws');
          
          ws.onopen = () => {
            setConnected(true);
          };
          
          ws.onclose = () => {
            setConnected(false);
          };
          
          return () => ws.close();
        }, []);
        
        return (
          <div data-testid="connection-status">
            {connected ? 'Connected' : 'Disconnected'}
          </div>
        );
      };
      
      const { getByTestId } = render(<TestComponent />);
      
      await server.connected;
      
      await waitFor(() => {
        expect(getByTestId('connection-status')).toHaveTextContent('Connected');
      });
    });

    it('should handle WebSocket messages', async () => {
      const TestComponent = () => {
        const [message, setMessage] = React.useState('');
        
        React.useEffect(() => {
          const ws = new WebSocket('ws://localhost:8000/ws');
          
          ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            setMessage(data.content);
          };
          
          return () => ws.close();
        }, []);
        
        return <div data-testid="message">{message}</div>;
      };
      
      const { getByTestId } = render(<TestComponent />);
      
      await server.connected;
      
      act(() => {
        server.send(JSON.stringify({ content: 'Hello from server' }));
      });
      
      await waitFor(() => {
        expect(getByTestId('message')).toHaveTextContent('Hello from server');
      });
    });
  });

  describe('Chat Functionality', () => {
    it('should send and receive messages', async () => {
      const ChatComponent = () => {
        const { messages, addMessage } = useChatStore();
        const [input, setInput] = React.useState('');
        
        const sendMessage = () => {
          if (input.trim()) {
            addMessage({
              id: Date.now().toString(),
              content: input,
              role: 'user',
              timestamp: new Date().toISOString()
            });
            setInput('');
          }
        };
        
        return (
          <div>
            <div data-testid="message-list">
              {messages.map(msg => (
                <div key={msg.id} data-testid={`message-${msg.id}`}>
                  {msg.content}
                </div>
              ))}
            </div>
            <input
              data-testid="message-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
            />
            <button onClick={sendMessage}>Send</button>
          </div>
        );
      };
      
      const { getByText, getByTestId } = render(<ChatComponent />);
      
      const input = getByTestId('message-input');
      
      fireEvent.change(input, { target: { value: 'Test message' } });
      fireEvent.click(getByText('Send'));
      
      await waitFor(() => {
        const messageList = getByTestId('message-list');
        expect(messageList).toHaveTextContent('Test message');
      });
      
      expect(useChatStore.getState().messages).toHaveLength(1);
      expect(useChatStore.getState().messages[0].content).toBe('Test message');
    });

    it('should handle streaming messages', async () => {
      const StreamingComponent = () => {
        const [streamingContent, setStreamingContent] = React.useState('');
        
        React.useEffect(() => {
          const ws = new WebSocket('ws://localhost:8000/ws');
          
          ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'stream_chunk') {
              setStreamingContent(prev => prev + data.chunk);
            }
          };
          
          return () => ws.close();
        }, []);
        
        return (
          <div data-testid="streaming-content">{streamingContent}</div>
        );
      };
      
      const { getByTestId } = render(<StreamingComponent />);
      
      await server.connected;
      
      // Simulate streaming chunks
      act(() => {
        server.send(JSON.stringify({ type: 'stream_chunk', chunk: 'Hello ' }));
      });
      
      await waitFor(() => {
        expect(getByTestId('streaming-content')).toHaveTextContent('Hello ');
      });
      
      act(() => {
        server.send(JSON.stringify({ type: 'stream_chunk', chunk: 'World!' }));
      });
      
      await waitFor(() => {
        expect(getByTestId('streaming-content')).toHaveTextContent('Hello World!');
      });
    });
  });

  describe('Thread Management', () => {
    it('should create and switch threads', async () => {
      const ThreadComponent = () => {
        const { threads, currentThread, addThread, setCurrentThread } = useThreadStore();
        
        const handleCreateThread = () => {
          const newThread = {
            id: Date.now().toString(),
            title: 'New Thread',
            created_at: Date.now()
          };
          addThread(newThread);
        };
        
        return (
          <div>
            <button onClick={handleCreateThread}>Create Thread</button>
            <div data-testid="thread-count">{threads.length} threads</div>
            <div data-testid="active-thread">
              {currentThread ? currentThread.title : 'No active thread'}
            </div>
            {threads.map(thread => (
              <button
                key={thread.id}
                data-testid={`thread-${thread.id}`}
                onClick={() => setCurrentThread(thread.id)}
              >
                {thread.title || 'Untitled'}
              </button>
            ))}
          </div>
        );
      };
      
      const { getByText, getByTestId } = render(<ThreadComponent />);
      
      expect(getByTestId('thread-count')).toHaveTextContent('0 threads');
      
      fireEvent.click(getByText('Create Thread'));
      
      await waitFor(() => {
        expect(getByTestId('thread-count')).toHaveTextContent('1 threads');
      });
      
      const thread = useThreadStore.getState().threads[0];
      fireEvent.click(getByTestId(`thread-${thread.id}`));
      
      await waitFor(() => {
        expect(getByTestId('active-thread')).toHaveTextContent('New Thread');
      });
    });

    it('should delete threads', async () => {
      // Create initial thread
      useThreadStore.getState().addThread({
        id: 'thread-1',
        title: 'Test Thread',
        created_at: Date.now()
      });
      
      const DeleteThreadComponent = () => {
        const { threads, deleteThread } = useThreadStore();
        
        return (
          <div>
            <div data-testid="thread-count">{threads.length} threads</div>
            {threads.map(thread => (
              <div key={thread.id}>
                <span>{thread.title || 'Untitled'}</span>
                <button onClick={() => deleteThread(thread.id)}>Delete</button>
              </div>
            ))}
          </div>
        );
      };
      
      const { getByText, getByTestId } = render(<DeleteThreadComponent />);
      
      expect(getByTestId('thread-count')).toHaveTextContent('1 threads');
      
      fireEvent.click(getByText('Delete'));
      
      await waitFor(() => {
        expect(getByTestId('thread-count')).toHaveTextContent('0 threads');
      });
    });
  });

  describe('Agent Integration', () => {
    it('should handle agent messages through WebSocket', async () => {
      const AgentComponent = () => {
        const [agentStatus, setAgentStatus] = React.useState('idle');
        const [agentMessage, setAgentMessage] = React.useState('');
        
        React.useEffect(() => {
          const ws = new WebSocket('ws://localhost:8000/ws');
          
          ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            if (data.type === 'agent_started') {
              setAgentStatus('processing');
            } else if (data.type === 'agent_message') {
              setAgentMessage(data.content);
            } else if (data.type === 'agent_completed') {
              setAgentStatus('completed');
            }
          };
          
          const startAgent = () => {
            ws.send(JSON.stringify({
              type: 'start_agent',
              task: 'analyze'
            }));
          };
          
          // Auto-start agent for testing
          setTimeout(startAgent, 100);
          
          return () => ws.close();
        }, []);
        
        return (
          <div>
            <div data-testid="agent-status">{agentStatus}</div>
            <div data-testid="agent-message">{agentMessage}</div>
          </div>
        );
      };
      
      const { getByTestId } = render(<AgentComponent />);
      
      await server.connected;
      
      // Wait for agent to start
      await new Promise(resolve => setTimeout(resolve, 200));
      
      // Simulate agent lifecycle
      act(() => {
        server.send(JSON.stringify({ type: 'agent_started' }));
      });
      
      await waitFor(() => {
        expect(getByTestId('agent-status')).toHaveTextContent('processing');
      });
      
      act(() => {
        server.send(JSON.stringify({
          type: 'agent_message',
          content: 'Analysis in progress...'
        }));
      });
      
      await waitFor(() => {
        expect(getByTestId('agent-message')).toHaveTextContent('Analysis in progress...');
      });
      
      act(() => {
        server.send(JSON.stringify({ type: 'agent_completed' }));
      });
      
      await waitFor(() => {
        expect(getByTestId('agent-status')).toHaveTextContent('completed');
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle network errors gracefully', async () => {
      const ErrorComponent = () => {
        const [error, setError] = React.useState(null);
        const [loading, setLoading] = React.useState(false);
        
        const fetchData = async () => {
          setLoading(true);
          setError(null);
          
          try {
            const response = await fetch('/api/data');
            if (!response.ok) {
              throw new Error('Network error');
            }
            const data = await response.json();
          } catch (err) {
            setError(err.message);
          } finally {
            setLoading(false);
          }
        };
        
        return (
          <div>
            <button onClick={fetchData}>Fetch Data</button>
            {loading && <div data-testid="loading">Loading...</div>}
            {error && <div data-testid="error">{error}</div>}
          </div>
        );
      };
      
      (fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));
      
      const { getByText, getByTestId } = render(<ErrorComponent />);
      
      fireEvent.click(getByText('Fetch Data'));
      
      await waitFor(() => {
        expect(getByTestId('error')).toHaveTextContent('Network error');
      });
    });

    it('should handle WebSocket disconnection', async () => {
      const ReconnectComponent = () => {
        const [connected, setConnected] = React.useState(false);
        const [reconnectAttempts, setReconnectAttempts] = React.useState(0);
        
        const connect = () => {
          const ws = new WebSocket('ws://localhost:8000/ws');
          
          ws.onopen = () => {
            setConnected(true);
            setReconnectAttempts(0);
          };
          
          ws.onclose = () => {
            setConnected(false);
            
            // Attempt reconnection
            setTimeout(() => {
              setReconnectAttempts(prev => prev + 1);
              connect();
            }, 1000);
          };
          
          return ws;
        };
        
        React.useEffect(() => {
          const ws = connect();
          return () => ws.close();
        }, []);
        
        return (
          <div>
            <div data-testid="connection">
              {connected ? 'Connected' : 'Disconnected'}
            </div>
            <div data-testid="attempts">
              Reconnect attempts: {reconnectAttempts}
            </div>
          </div>
        );
      };
      
      const { getByTestId } = render(<ReconnectComponent />);
      
      await server.connected;
      
      await waitFor(() => {
        expect(getByTestId('connection')).toHaveTextContent('Connected');
      });
      
      // Simulate disconnection
      act(() => {
        server.close();
      });
      
      await waitFor(() => {
        expect(getByTestId('connection')).toHaveTextContent('Disconnected');
      });
    });
  });

  describe('State Synchronization', () => {
    it('should sync state between components', async () => {
      const ComponentA = () => {
        const { messages, addMessage } = useChatStore();
        
        const sendMessage = () => {
          addMessage({
            id: 'msg-1',
            content: 'From Component A',
            role: 'user',
            timestamp: new Date().toISOString()
          });
        };
        
        return (
          <div>
            <button onClick={sendMessage}>Send from A</button>
            <div data-testid="messages-a">{messages.length} messages</div>
          </div>
        );
      };
      
      const ComponentB = () => {
        const { messages } = useChatStore();
        
        return (
          <div data-testid="messages-b">
            {messages.map(msg => (
              <div key={msg.id}>{msg.content}</div>
            ))}
          </div>
        );
      };
      
      const App = () => (
        <div>
          <ComponentA />
          <ComponentB />
        </div>
      );
      
      const { getByText, getByTestId } = render(<App />);
      
      fireEvent.click(getByText('Send from A'));
      
      await waitFor(() => {
        expect(getByTestId('messages-a')).toHaveTextContent('1 messages');
        expect(getByTestId('messages-b')).toHaveTextContent('From Component A');
      });
    });
  });

  describe('Navigation and Routing', () => {
    it('should handle navigation between views', async () => {
      const router = require('next/navigation').useRouter();
      
      const NavigationComponent = () => {
        const [currentView, setCurrentView] = React.useState('home');
        
        const navigate = (view: string) => {
          setCurrentView(view);
          router.push(`/${view}`);
        };
        
        return (
          <div>
            <nav>
              <button onClick={() => navigate('home')}>Home</button>
              <button onClick={() => navigate('chat')}>Chat</button>
              <button onClick={() => navigate('settings')}>Settings</button>
            </nav>
            <div data-testid="current-view">{currentView}</div>
          </div>
        );
      };
      
      const { getByText, getByTestId } = render(<NavigationComponent />);
      
      expect(getByTestId('current-view')).toHaveTextContent('home');
      
      fireEvent.click(getByText('Chat'));
      
      await waitFor(() => {
        expect(getByTestId('current-view')).toHaveTextContent('chat');
        expect(router.push).toHaveBeenCalledWith('/chat');
      });
      
      fireEvent.click(getByText('Settings'));
      
      await waitFor(() => {
        expect(getByTestId('current-view')).toHaveTextContent('settings');
        expect(router.push).toHaveBeenCalledWith('/settings');
      });
    });
  });

  describe('Performance and Optimization', () => {
    it('should debounce rapid input changes', async () => {
      let apiCallCount = 0;
      
      const DebouncedSearch = () => {
        const [query, setQuery] = React.useState('');
        const [results, setResults] = React.useState([]);
        
        // Debounced search
        React.useEffect(() => {
          const timer = setTimeout(async () => {
            if (query) {
              apiCallCount++;
              // Simulate API call
              setResults([`Result for ${query}`]);
            }
          }, 300);
          
          return () => clearTimeout(timer);
        }, [query]);
        
        return (
          <div>
            <input
              data-testid="search-input"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <div data-testid="results">
              {results.map((r, i) => <div key={i}>{r}</div>)}
            </div>
            <div data-testid="api-calls">{apiCallCount}</div>
          </div>
        );
      };
      
      const { getByTestId } = render(<DebouncedSearch />);
      const input = getByTestId('search-input');
      
      // Type rapidly
      fireEvent.change(input, { target: { value: 't' } });
      fireEvent.change(input, { target: { value: 'te' } });
      fireEvent.change(input, { target: { value: 'test' } });
      
      // Wait for debounce
      await new Promise(resolve => setTimeout(resolve, 400));
      
      // Should only make one API call despite multiple changes
      expect(apiCallCount).toBe(1);
      
      await waitFor(() => {
        expect(getByTestId('results')).toHaveTextContent('Result for test');
      });
    });

    it('should implement virtual scrolling for large lists', async () => {
      const VirtualList = () => {
        const items = Array.from({ length: 10000 }, (_, i) => `Item ${i}`);
        const [visibleStart, setVisibleStart] = React.useState(0);
        const itemHeight = 30;
        const containerHeight = 300;
        const visibleCount = Math.ceil(containerHeight / itemHeight);
        
        const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
          const scrollTop = e.currentTarget.scrollTop;
          const newStart = Math.floor(scrollTop / itemHeight);
          setVisibleStart(newStart);
        };
        
        const visibleItems = items.slice(visibleStart, visibleStart + visibleCount);
        
        return (
          <div
            data-testid="virtual-list"
            style={{ height: containerHeight, overflow: 'auto' }}
            onScroll={handleScroll}
          >
            <div style={{ height: items.length * itemHeight }}>
              {visibleItems.map((item, index) => (
                <div
                  key={visibleStart + index}
                  style={{
                    height: itemHeight,
                    position: 'absolute',
                    top: (visibleStart + index) * itemHeight
                  }}
                >
                  {item}
                </div>
              ))}
            </div>
            <div data-testid="visible-count">{visibleItems.length}</div>
          </div>
        );
      };
      
      const { getByTestId } = render(<VirtualList />);
      
      // Should only render visible items
      expect(parseInt(getByTestId('visible-count').textContent || '0')).toBeLessThan(20);
    });
  });
});