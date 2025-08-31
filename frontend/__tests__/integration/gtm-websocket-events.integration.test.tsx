import React from 'react';
import { render, screen, waitFor, act, fireEvent } from '@testing-library/react';
import { GTMProvider } from '@/providers/GTMProvider';
import { useGTM } from '@/hooks/useGTM';

// Mock Next.js Script component
jest.mock('next/script', () => {
  return function MockScript({ onLoad, onReady, ...props }: any) {
    React.useEffect(() => {
      if (onReady) onReady();
      const timer = setTimeout(() => {
        if (onLoad) onLoad();
      }, 50);
      return () => clearTimeout(timer);
    }, [onLoad, onReady]);
    return <script {...props} data-testid="gtm-script" />;
  };
});

// Mock logger
jest.mock('@/lib/logger', () => ({
  logger: {
    debug: jest.fn(),
    error: jest.fn(),
    info: jest.fn(),
  },
}));

// Mock WebSocket for realistic testing
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  public readyState = MockWebSocket.CONNECTING;
  public onopen: ((event: Event) => void) | null = null;
  public onmessage: ((event: MessageEvent) => void) | null = null;
  public onclose: ((event: CloseEvent) => void) | null = null;
  public onerror: ((event: Event) => void) | null = null;

  constructor(public url: string, public protocols?: string | string[]) {
    // Simulate connection opening
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    }, 100);
  }

  send(data: string | ArrayBufferLike | Blob | ArrayBufferView) {
    if (this.readyState !== MockWebSocket.OPEN) {
      throw new Error('WebSocket is not open');
    }
    // Simulate echo or response
    setTimeout(() => {
      if (this.onmessage) {
        const message = typeof data === 'string' ? data : 'binary data';
        this.onmessage(new MessageEvent('message', { data: message }));
      }
    }, 50);
  }

  close(code?: number, reason?: string) {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close', { code, reason }));
    }
  }

  // Method to simulate receiving messages from server
  simulateMessage(data: any) {
    if (this.onmessage && this.readyState === MockWebSocket.OPEN) {
      this.onmessage(new MessageEvent('message', { data: JSON.stringify(data) }));
    }
  }

  // Method to simulate connection error
  simulateError() {
    if (this.onerror) {
      this.onerror(new Event('error'));
    }
  }
}

// Set up WebSocket mock
global.WebSocket = MockWebSocket as any;

// WebSocket integration test component
const WebSocketGTMTestComponent: React.FC = () => {
  const gtm = useGTM();
  const [ws, setWs] = React.useState<MockWebSocket | null>(null);
  const [connectionStatus, setConnectionStatus] = React.useState<'disconnected' | 'connecting' | 'connected'>('disconnected');
  const [messages, setMessages] = React.useState<any[]>([]);
  const [threads, setThreads] = React.useState<any[]>([]);
  const [currentThread, setCurrentThread] = React.useState<string | null>(null);

  const connectWebSocket = () => {
    setConnectionStatus('connecting');
    
    // Track WebSocket connection attempt
    gtm.events.trackCustom({
      event: 'websocket_connect_attempt',
      event_category: 'connection',
      event_action: 'connect_start'
    });

    const websocket = new MockWebSocket('ws://localhost:8000/ws');
    
    websocket.onopen = () => {
      setConnectionStatus('connected');
      setWs(websocket);
      
      // Track successful connection
      gtm.events.trackEngagement('chat_started', {
        session_duration: 0
      });
    };

    websocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setMessages(prev => [...prev, data]);
        
        // Track different message types
        switch (data.type) {
          case 'thread_created':
            setThreads(prev => [...prev, data.thread]);
            setCurrentThread(data.thread.id);
            gtm.events.trackEngagement('thread_created', {
              thread_id: data.thread.id
            });
            break;
            
          case 'message_received':
            gtm.events.trackEngagement('message_sent', {
              thread_id: data.thread_id,
              message_length: data.content?.length || 0,
              agent_type: data.agent_type
            });
            break;
            
          case 'agent_activated':
            gtm.events.trackEngagement('agent_activated', {
              agent_type: data.agent_type,
              thread_id: data.thread_id
            });
            break;
            
          case 'feature_used':
            gtm.events.trackEngagement('feature_used', {
              feature_type: data.feature_type,
              thread_id: data.thread_id
            });
            break;
        }
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
        
        // Track parsing errors
        gtm.events.trackCustom({
          event: 'websocket_error',
          event_category: 'error',
          event_action: 'message_parse_failed',
          error_type: 'json_parse_error'
        });
      }
    };

    websocket.onclose = () => {
      setConnectionStatus('disconnected');
      setWs(null);
      
      // Track disconnection
      gtm.events.trackCustom({
        event: 'websocket_disconnect',
        event_category: 'connection',
        event_action: 'disconnect'
      });
    };

    websocket.onerror = () => {
      setConnectionStatus('disconnected');
      
      // Track connection errors
      gtm.events.trackCustom({
        event: 'websocket_error',
        event_category: 'error',
        event_action: 'connection_failed'
      });
    };
  };

  const sendMessage = (content: string) => {
    if (ws && connectionStatus === 'connected') {
      const message = {
        type: 'send_message',
        thread_id: currentThread,
        content,
        timestamp: new Date().toISOString()
      };
      
      ws.send(JSON.stringify(message));
      
      // Track message sending
      gtm.events.trackEngagement('message_sent', {
        thread_id: currentThread || undefined,
        message_length: content.length
      });
    }
  };

  const createThread = () => {
    if (ws && connectionStatus === 'connected') {
      const message = {
        type: 'create_thread',
        title: 'New Chat Thread',
        timestamp: new Date().toISOString()
      };
      
      ws.send(JSON.stringify(message));
    }
  };

  const activateAgent = (agentType: string) => {
    if (ws && connectionStatus === 'connected') {
      const message = {
        type: 'activate_agent',
        agent_type: agentType,
        thread_id: currentThread,
        timestamp: new Date().toISOString()
      };
      
      ws.send(JSON.stringify(message));
    }
  };

  const disconnect = () => {
    if (ws) {
      ws.close();
    }
  };

  return (
    <div data-testid="websocket-gtm-component">
      <div data-testid="connection-status">{connectionStatus}</div>
      <div data-testid="gtm-status">{gtm.isLoaded ? 'ready' : 'loading'}</div>
      <div data-testid="total-events">{gtm.debug.totalEvents}</div>
      <div data-testid="message-count">{messages.length}</div>
      <div data-testid="thread-count">{threads.length}</div>
      <div data-testid="current-thread">{currentThread || 'none'}</div>
      
      <button data-testid="connect-btn" onClick={connectWebSocket}>
        Connect WebSocket
      </button>
      <button data-testid="disconnect-btn" onClick={disconnect}>
        Disconnect
      </button>
      <button data-testid="create-thread-btn" onClick={createThread}>
        Create Thread
      </button>
      <button data-testid="send-message-btn" onClick={() => sendMessage('Test message')}>
        Send Message
      </button>
      <button data-testid="activate-agent-btn" onClick={() => activateAgent('code_generator')}>
        Activate Code Agent
      </button>
      
      {/* Test helper - allows simulating server messages */}
      <button 
        data-testid="simulate-thread-created" 
        onClick={() => {
          if (ws) {
            (ws as any).simulateMessage({
              type: 'thread_created',
              thread: { id: 'thread_123', title: 'New Thread' },
              timestamp: new Date().toISOString()
            });
          }
        }}
      >
        Simulate Thread Created
      </button>
      
      <button 
        data-testid="simulate-message-received" 
        onClick={() => {
          if (ws) {
            (ws as any).simulateMessage({
              type: 'message_received',
              thread_id: 'thread_123',
              content: 'Hello from agent',
              agent_type: 'assistant',
              timestamp: new Date().toISOString()
            });
          }
        }}
      >
        Simulate Message Received
      </button>
      
      <button 
        data-testid="simulate-agent-activated" 
        onClick={() => {
          if (ws) {
            (ws as any).simulateMessage({
              type: 'agent_activated',
              agent_type: 'code_generator',
              thread_id: 'thread_123',
              timestamp: new Date().toISOString()
            });
          }
        }}
      >
        Simulate Agent Activated
      </button>
    </div>
  );
};

describe('GTM WebSocket Events Integration', () => {
      setupAntiHang();
    jest.setTimeout(10000);
  let mockDataLayer: any[];

  beforeEach(() => {
    mockDataLayer = [];
    
    // Safely set window properties without redefining the window object
    if (typeof window === 'undefined') {
      // If window doesn't exist, create it
      (global as any).window = {
        dataLayer: mockDataLayer,
        location: {
          pathname: '/chat',
          origin: 'https://app.netra.com'
        }
      };
    } else {
      // If window exists, just set the properties we need
      (window as any).dataLayer = mockDataLayer;
      (window as any).location = {
        pathname: '/chat',
        origin: 'https://app.netra.com'
      };
    }

    jest.clearAllMocks();
  });

  const renderWithGTM = (component: React.ReactElement) => {
    return render(
      <GTMProvider enabled={true} config={{ debug: true }}>
        {component}
      </GTMProvider>
    );
  };

  describe('WebSocket Connection Events', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should track WebSocket connection attempts and success', async () => {
      renderWithGTM(<WebSocketGTMTestComponent />);

      // Wait for GTM to be ready
      await waitFor(() => {
        expect(screen.getByTestId('gtm-status')).toHaveTextContent('ready');
      });

      // Connect WebSocket
      fireEvent.click(screen.getByTestId('connect-btn'));

      // Verify connection attempt tracking
      await waitFor(() => {
        const connectAttempt = mockDataLayer.find(item => 
          item.event === 'websocket_connect_attempt'
        );
        expect(connectAttempt).toBeDefined();
        expect(connectAttempt.event_category).toBe('connection');
        expect(connectAttempt.event_action).toBe('connect_start');
      });

      // Wait for connection to be established
      await waitFor(() => {
        expect(screen.getByTestId('connection-status')).toHaveTextContent('connected');
      });

      // Verify chat started event
      await waitFor(() => {
        const chatStarted = mockDataLayer.find(item => 
          item.event === 'chat_started'
        );
        expect(chatStarted).toBeDefined();
        expect(chatStarted.event_category).toBe('engagement');
        expect(chatStarted.session_duration).toBe(0);
      });
    });

    it('should track WebSocket disconnection events', async () => {
      renderWithGTM(<WebSocketGTMTestComponent />);

      await waitFor(() => {
        expect(screen.getByTestId('gtm-status')).toHaveTextContent('ready');
      });

      // Connect then disconnect
      fireEvent.click(screen.getByTestId('connect-btn'));
      
      await waitFor(() => {
        expect(screen.getByTestId('connection-status')).toHaveTextContent('connected');
      });

      fireEvent.click(screen.getByTestId('disconnect-btn'));

      await waitFor(() => {
        expect(screen.getByTestId('connection-status')).toHaveTextContent('disconnected');
      });

      // Verify disconnect event
      await waitFor(() => {
        const disconnectEvent = mockDataLayer.find(item => 
          item.event === 'websocket_disconnect'
        );
        expect(disconnectEvent).toBeDefined();
        expect(disconnectEvent.event_category).toBe('connection');
        expect(disconnectEvent.event_action).toBe('disconnect');
      });
    });

    it('should track WebSocket connection errors', async () => {
      renderWithGTM(<WebSocketGTMTestComponent />);

      await waitFor(() => {
        expect(screen.getByTestId('gtm-status')).toHaveTextContent('ready');
      });

      fireEvent.click(screen.getByTestId('connect-btn'));

      await waitFor(() => {
        expect(screen.getByTestId('connection-status')).toHaveTextContent('connected');
      });

      // Simulate connection error
      const wsInstance = (global as any).lastWebSocketInstance;
      if (wsInstance) {
        act(() => {
          wsInstance.simulateError();
        });
      }

      await waitFor(() => {
        const errorEvent = mockDataLayer.find(item => 
          item.event === 'websocket_error'
        );
        expect(errorEvent).toBeDefined();
        expect(errorEvent.event_category).toBe('error');
        expect(errorEvent.event_action).toBe('connection_failed');
      });
    });
  });

  describe('Thread Management Events', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should track thread creation events', async () => {
      renderWithGTM(<WebSocketGTMTestComponent />);

      await waitFor(() => {
        expect(screen.getByTestId('gtm-status')).toHaveTextContent('ready');
      });

      // Connect WebSocket
      fireEvent.click(screen.getByTestId('connect-btn'));
      
      await waitFor(() => {
        expect(screen.getByTestId('connection-status')).toHaveTextContent('connected');
      });

      // Simulate thread creation from server
      fireEvent.click(screen.getByTestId('simulate-thread-created'));

      await waitFor(() => {
        expect(screen.getByTestId('thread-count')).toHaveTextContent('1');
        expect(screen.getByTestId('current-thread')).toHaveTextContent('thread_123');
      });

      // Verify thread creation event
      await waitFor(() => {
        const threadEvent = mockDataLayer.find(item => 
          item.event === 'thread_created'
        );
        expect(threadEvent).toBeDefined();
        expect(threadEvent.event_category).toBe('engagement');
        expect(threadEvent.thread_id).toBe('thread_123');
      });
    });

    it('should track multiple thread operations', async () => {
      renderWithGTM(<WebSocketGTMTestComponent />);

      await waitFor(() => {
        expect(screen.getByTestId('gtm-status')).toHaveTextContent('ready');
      });

      fireEvent.click(screen.getByTestId('connect-btn'));
      
      await waitFor(() => {
        expect(screen.getByTestId('connection-status')).toHaveTextContent('connected');
      });

      // Create multiple threads
      fireEvent.click(screen.getByTestId('simulate-thread-created'));
      
      await waitFor(() => {
        expect(screen.getByTestId('thread-count')).toHaveTextContent('1');
      });

      // Simulate another thread
      act(() => {
        const ws = (global as any).lastWebSocketInstance;
        if (ws) {
          ws.simulateMessage({
            type: 'thread_created',
            thread: { id: 'thread_456', title: 'Second Thread' },
            timestamp: new Date().toISOString()
          });
        }
      });

      await waitFor(() => {
        expect(screen.getByTestId('thread-count')).toHaveTextContent('2');
      });

      // Verify multiple thread events
      await waitFor(() => {
        const threadEvents = mockDataLayer.filter(item => 
          item.event === 'thread_created'
        );
        expect(threadEvents).toHaveLength(2);
        
        const threadIds = threadEvents.map(e => e.thread_id);
        expect(threadIds).toContain('thread_123');
        expect(threadIds).toContain('thread_456');
      });
    });
  });

  describe('Message Flow Events', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should track outgoing message events', async () => {
      renderWithGTM(<WebSocketGTMTestComponent />);

      await waitFor(() => {
        expect(screen.getByTestId('gtm-status')).toHaveTextContent('ready');
      });

      fireEvent.click(screen.getByTestId('connect-btn'));
      
      await waitFor(() => {
        expect(screen.getByTestId('connection-status')).toHaveTextContent('connected');
      });

      // Set up thread context
      fireEvent.click(screen.getByTestId('simulate-thread-created'));
      
      await waitFor(() => {
        expect(screen.getByTestId('current-thread')).toHaveTextContent('thread_123');
      });

      // Send message
      fireEvent.click(screen.getByTestId('send-message-btn'));

      // Verify message sent event
      await waitFor(() => {
        const messageEvents = mockDataLayer.filter(item => 
          item.event === 'message_sent'
        );
        expect(messageEvents.length).toBeGreaterThanOrEqual(1);
        
        const lastMessageEvent = messageEvents[messageEvents.length - 1];
        expect(lastMessageEvent.event_category).toBe('engagement');
        expect(lastMessageEvent.thread_id).toBe('thread_123');
        expect(lastMessageEvent.message_length).toBe(12); // "Test message".length
      });
    });

    it('should track incoming message events', async () => {
      renderWithGTM(<WebSocketGTMTestComponent />);

      await waitFor(() => {
        expect(screen.getByTestId('gtm-status')).toHaveTextContent('ready');
      });

      fireEvent.click(screen.getByTestId('connect-btn'));
      
      await waitFor(() => {
        expect(screen.getByTestId('connection-status')).toHaveTextContent('connected');
      });

      // Simulate incoming message
      fireEvent.click(screen.getByTestId('simulate-message-received'));

      await waitFor(() => {
        expect(screen.getByTestId('message-count')).toHaveTextContent('1');
      });

      // Verify message received event
      await waitFor(() => {
        const messageEvent = mockDataLayer.find(item => 
          item.event === 'message_sent' && item.agent_type === 'assistant'
        );
        expect(messageEvent).toBeDefined();
        expect(messageEvent.thread_id).toBe('thread_123');
        expect(messageEvent.message_length).toBe(16); // "Hello from agent".length
        expect(messageEvent.agent_type).toBe('assistant');
      });
    });

    it('should handle message parsing errors gracefully', async () => {
      renderWithGTM(<WebSocketGTMTestComponent />);

      await waitFor(() => {
        expect(screen.getByTestId('gtm-status')).toHaveTextContent('ready');
      });

      fireEvent.click(screen.getByTestId('connect-btn'));
      
      await waitFor(() => {
        expect(screen.getByTestId('connection-status')).toHaveTextContent('connected');
      });

      // Simulate malformed message
      act(() => {
        const ws = (global as any).lastWebSocketInstance;
        if (ws && ws.onmessage) {
          ws.onmessage(new MessageEvent('message', { 
            data: 'invalid json {' 
          }));
        }
      });

      // Verify error tracking
      await waitFor(() => {
        const errorEvent = mockDataLayer.find(item => 
          item.event === 'websocket_error' && item.error_type === 'json_parse_error'
        );
        expect(errorEvent).toBeDefined();
        expect(errorEvent.event_category).toBe('error');
        expect(errorEvent.event_action).toBe('message_parse_failed');
      });
    });
  });

  describe('Agent Activation Events', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should track agent activation events', async () => {
      renderWithGTM(<WebSocketGTMTestComponent />);

      await waitFor(() => {
        expect(screen.getByTestId('gtm-status')).toHaveTextContent('ready');
      });

      fireEvent.click(screen.getByTestId('connect-btn'));
      
      await waitFor(() => {
        expect(screen.getByTestId('connection-status')).toHaveTextContent('connected');
      });

      // Simulate agent activation
      fireEvent.click(screen.getByTestId('simulate-agent-activated'));

      // Verify agent activation event
      await waitFor(() => {
        const agentEvent = mockDataLayer.find(item => 
          item.event === 'agent_activated'
        );
        expect(agentEvent).toBeDefined();
        expect(agentEvent.event_category).toBe('engagement');
        expect(agentEvent.agent_type).toBe('code_generator');
        expect(agentEvent.thread_id).toBe('thread_123');
      });
    });

    it('should track different agent types', async () => {
      renderWithGTM(<WebSocketGTMTestComponent />);

      await waitFor(() => {
        expect(screen.getByTestId('gtm-status')).toHaveTextContent('ready');
      });

      fireEvent.click(screen.getByTestId('connect-btn'));
      
      await waitFor(() => {
        expect(screen.getByTestId('connection-status')).toHaveTextContent('connected');
      });

      // Simulate different agent types
      const agentTypes = ['code_generator', 'data_analyst', 'content_writer'];
      
      for (const agentType of agentTypes) {
        act(() => {
          const ws = (global as any).lastWebSocketInstance;
          if (ws) {
            ws.simulateMessage({
              type: 'agent_activated',
              agent_type: agentType,
              thread_id: 'thread_123',
              timestamp: new Date().toISOString()
            });
          }
        });
      }

      // Verify all agent types were tracked
      await waitFor(() => {
        const agentEvents = mockDataLayer.filter(item => 
          item.event === 'agent_activated'
        );
        expect(agentEvents).toHaveLength(agentTypes.length);
        
        const trackedAgentTypes = agentEvents.map(e => e.agent_type);
        agentTypes.forEach(type => {
          expect(trackedAgentTypes).toContain(type);
        });
      });
    });
  });

  describe('Feature Usage Events', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should track feature usage through WebSocket', async () => {
      renderWithGTM(<WebSocketGTMTestComponent />);

      await waitFor(() => {
        expect(screen.getByTestId('gtm-status')).toHaveTextContent('ready');
      });

      fireEvent.click(screen.getByTestId('connect-btn'));
      
      await waitFor(() => {
        expect(screen.getByTestId('connection-status')).toHaveTextContent('connected');
      });

      // Simulate feature usage events
      const features = ['file_upload', 'code_execution', 'data_visualization'];
      
      for (const feature of features) {
        act(() => {
          const ws = (global as any).lastWebSocketInstance;
          if (ws) {
            ws.simulateMessage({
              type: 'feature_used',
              feature_type: feature,
              thread_id: 'thread_123',
              timestamp: new Date().toISOString()
            });
          }
        });
      }

      // Verify feature usage tracking
      await waitFor(() => {
        const featureEvents = mockDataLayer.filter(item => 
          item.event === 'feature_used'
        );
        expect(featureEvents).toHaveLength(features.length);
        
        const trackedFeatures = featureEvents.map(e => e.feature_type);
        features.forEach(feature => {
          expect(trackedFeatures).toContain(feature);
        });
      });
    });
  });

  describe('Complex Integration Flows', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should track complete chat session flow', async () => {
      renderWithGTM(<WebSocketGTMTestComponent />);

      await waitFor(() => {
        expect(screen.getByTestId('gtm-status')).toHaveTextContent('ready');
      });

      // Step 1: Connect WebSocket
      fireEvent.click(screen.getByTestId('connect-btn'));
      
      await waitFor(() => {
        expect(screen.getByTestId('connection-status')).toHaveTextContent('connected');
      });

      // Step 2: Create thread
      fireEvent.click(screen.getByTestId('simulate-thread-created'));
      
      await waitFor(() => {
        expect(screen.getByTestId('thread-count')).toHaveTextContent('1');
      });

      // Step 3: Send message
      fireEvent.click(screen.getByTestId('send-message-btn'));

      // Step 4: Receive response
      fireEvent.click(screen.getByTestId('simulate-message-received'));

      // Step 5: Activate agent
      fireEvent.click(screen.getByTestId('simulate-agent-activated'));

      // Step 6: Use feature
      act(() => {
        const ws = (global as any).lastWebSocketInstance;
        if (ws) {
          ws.simulateMessage({
            type: 'feature_used',
            feature_type: 'code_generation',
            thread_id: 'thread_123',
            timestamp: new Date().toISOString()
          });
        }
      });

      // Verify complete flow was tracked
      await waitFor(() => {
        const expectedEvents = [
          'websocket_connect_attempt',
          'chat_started',
          'thread_created',
          'message_sent',
          'agent_activated',
          'feature_used'
        ];

        expectedEvents.forEach(eventName => {
          const event = mockDataLayer.find(item => item.event === eventName);
          expect(event).toBeDefined();
        });

        // Verify event correlation
        const threadId = 'thread_123';
        const threadRelatedEvents = mockDataLayer.filter(item => 
          item.thread_id === threadId
        );
        expect(threadRelatedEvents.length).toBeGreaterThanOrEqual(4);
      });
    });

    it('should handle session persistence across reconnections', async () => {
      renderWithGTM(<WebSocketGTMTestComponent />);

      await waitFor(() => {
        expect(screen.getByTestId('gtm-status')).toHaveTextContent('ready');
      });

      // Initial connection and activity
      fireEvent.click(screen.getByTestId('connect-btn'));
      
      await waitFor(() => {
        expect(screen.getByTestId('connection-status')).toHaveTextContent('connected');
      });

      fireEvent.click(screen.getByTestId('simulate-thread-created'));

      // Disconnect
      fireEvent.click(screen.getByTestId('disconnect-btn'));
      
      await waitFor(() => {
        expect(screen.getByTestId('connection-status')).toHaveTextContent('disconnected');
      });

      // Reconnect
      fireEvent.click(screen.getByTestId('connect-btn'));
      
      await waitFor(() => {
        expect(screen.getByTestId('connection-status')).toHaveTextContent('connected');
      });

      // Continue activity
      fireEvent.click(screen.getByTestId('send-message-btn'));

      // Verify session events
      await waitFor(() => {
        const connectionAttempts = mockDataLayer.filter(item => 
          item.event === 'websocket_connect_attempt'
        );
        const chatStarted = mockDataLayer.filter(item => 
          item.event === 'chat_started'
        );
        const disconnects = mockDataLayer.filter(item => 
          item.event === 'websocket_disconnect'
        );

        expect(connectionAttempts).toHaveLength(2);
        expect(chatStarted).toHaveLength(2);
        expect(disconnects).toHaveLength(1);
      });
    });
  });

  describe('Performance and Reliability', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle high-frequency WebSocket events', async () => {
      renderWithGTM(<WebSocketGTMTestComponent />);

      await waitFor(() => {
        expect(screen.getByTestId('gtm-status')).toHaveTextContent('ready');
      });

      fireEvent.click(screen.getByTestId('connect-btn'));
      
      await waitFor(() => {
        expect(screen.getByTestId('connection-status')).toHaveTextContent('connected');
      });

      // Simulate rapid message flow
      act(() => {
        const ws = (global as any).lastWebSocketInstance;
        if (ws) {
          for (let i = 0; i < 20; i++) {
            ws.simulateMessage({
              type: 'message_received',
              thread_id: 'thread_123',
              content: `Message ${i}`,
              agent_type: 'assistant',
              timestamp: new Date().toISOString()
            });
          }
        }
      });

      // Verify all events were tracked
      await waitFor(() => {
        const messageEvents = mockDataLayer.filter(item => 
          item.event === 'message_sent'
        );
        expect(messageEvents.length).toBeGreaterThanOrEqual(20);
      });
    });

    it('should maintain event integrity during network issues', async () => {
      renderWithGTM(<WebSocketGTMTestComponent />);

      await waitFor(() => {
        expect(screen.getByTestId('gtm-status')).toHaveTextContent('ready');
      });

      fireEvent.click(screen.getByTestId('connect-btn'));
      
      await waitFor(() => {
        expect(screen.getByTestId('connection-status')).toHaveTextContent('connected');
      });

      // Track events before network issue
      fireEvent.click(screen.getByTestId('simulate-thread-created'));
      fireEvent.click(screen.getByTestId('send-message-btn'));

      // Simulate network error
      act(() => {
        const ws = (global as any).lastWebSocketInstance;
        if (ws) {
          ws.simulateError();
        }
      });

      // Verify error tracking and previous events remain intact
      await waitFor(() => {
        const errorEvent = mockDataLayer.find(item => 
          item.event === 'websocket_error'
        );
        const threadEvent = mockDataLayer.find(item => 
          item.event === 'thread_created'
        );
        const messageEvent = mockDataLayer.find(item => 
          item.event === 'message_sent'
        );

        expect(errorEvent).toBeDefined();
        expect(threadEvent).toBeDefined();
        expect(messageEvent).toBeDefined();
      });
    });
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});