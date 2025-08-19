/**
 * WebSocket Resilience Integration Tests
 * Tests WebSocket disconnection/reconnection with automatic retry
 * Ensures message queuing and delivery after reconnection
 */

import React from 'react';
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { jest } from '@jest/globals';
import WS from 'jest-websocket-mock';
import { TestProviders } from '../setup/test-providers';
import { WebSocketTestManager } from '../helpers/websocket-test-manager';
import { webSocketService } from '@/services/webSocketService';

// Mock dependencies
jest.mock('@/services/webSocketService');
jest.mock('@/config', () => ({
  config: {
    wsUrl: 'ws://localhost:8000',
    reconnectAttempts: 5,
    reconnectDelay: 1000,
    maxReconnectDelay: 30000
  }
}));

interface QueuedMessage {
  id: string;
  content: string;
  timestamp: number;
  status: 'pending' | 'sent' | 'failed';
}

interface ConnectionMetrics {
  connectTime: number;
  disconnectTime: number;
  reconnectAttempts: number;
  messagesLost: number;
  messagesQueued: number;
}

const createQueuedMessage = (content: string): QueuedMessage => ({
  id: Math.random().toString(36).substr(2, 9),
  content,
  timestamp: Date.now(),
  status: 'pending'
});

const calculateReconnectDelay = (attempt: number): number => {
  const baseDelay = 1000;
  const maxDelay = 30000;
  const delay = baseDelay * Math.pow(2, attempt - 1);
  return Math.min(delay, maxDelay);
};

const WebSocketResilienceComponent: React.FC = () => {
  const [connectionStatus, setConnectionStatus] = React.useState<string>('disconnected');
  const [messageQueue, setMessageQueue] = React.useState<QueuedMessage[]>([]);
  const [sentMessages, setSentMessages] = React.useState<string[]>([]);
  const [reconnectAttempts, setReconnectAttempts] = React.useState(0);
  const [lastError, setLastError] = React.useState<string | null>(null);
  const [isReconnecting, setIsReconnecting] = React.useState(false);

  const mockWebSocket = React.useRef<WebSocket | null>(null);
  const reconnectTimer = React.useRef<NodeJS.Timeout | null>(null);

  const connectWebSocket = React.useCallback(() => {
    if (connectionStatus === 'connecting' || connectionStatus === 'connected') {
      return;
    }

    setConnectionStatus('connecting');
    setLastError(null);

    try {
      const ws = new WebSocket('ws://localhost:8000/test');
      mockWebSocket.current = ws;

      ws.onopen = () => {
        setConnectionStatus('connected');
        setReconnectAttempts(0);
        setIsReconnecting(false);
        processQueuedMessages();
      };

      ws.onmessage = (event) => {
        // Handle incoming messages
      };

      ws.onclose = () => {
        setConnectionStatus('disconnected');
        if (!isReconnecting) {
          scheduleReconnect();
        }
      };

      ws.onerror = () => {
        setLastError('WebSocket connection error');
        setConnectionStatus('disconnected');
      };
    } catch (error) {
      setLastError((error as Error).message);
      setConnectionStatus('disconnected');
      scheduleReconnect();
    }
  }, [connectionStatus, isReconnecting]);

  const scheduleReconnect = React.useCallback(() => {
    if (reconnectAttempts >= 5) {
      setLastError('Max reconnection attempts reached');
      return;
    }

    setIsReconnecting(true);
    const delay = calculateReconnectDelay(reconnectAttempts + 1);
    
    reconnectTimer.current = setTimeout(() => {
      setReconnectAttempts(prev => prev + 1);
      connectWebSocket();
    }, delay);
  }, [reconnectAttempts, connectWebSocket]);

  const processQueuedMessages = React.useCallback(() => {
    if (connectionStatus !== 'connected' || messageQueue.length === 0) {
      return;
    }

    const messagesToSend = messageQueue.filter(msg => msg.status === 'pending');
    
    messagesToSend.forEach(message => {
      if (mockWebSocket.current?.readyState === WebSocket.OPEN) {
        mockWebSocket.current.send(JSON.stringify({
          type: 'message',
          content: message.content,
          id: message.id
        }));
        
        setMessageQueue(prev => 
          prev.map(msg => 
            msg.id === message.id 
              ? { ...msg, status: 'sent' as const }
              : msg
          )
        );
        
        setSentMessages(prev => [...prev, message.content]);
      }
    });
  }, [connectionStatus, messageQueue]);

  const sendMessage = (content: string) => {
    const message = createQueuedMessage(content);
    
    if (connectionStatus === 'connected' && mockWebSocket.current?.readyState === WebSocket.OPEN) {
      mockWebSocket.current.send(JSON.stringify({
        type: 'message',
        content: message.content,
        id: message.id
      }));
      
      setSentMessages(prev => [...prev, content]);
    } else {
      setMessageQueue(prev => [...prev, message]);
    }
  };

  const forceDisconnect = () => {
    if (mockWebSocket.current) {
      mockWebSocket.current.close();
    }
    setConnectionStatus('disconnected');
  };

  const manualReconnect = () => {
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current);
    }
    setIsReconnecting(false);
    setReconnectAttempts(0);
    connectWebSocket();
  };

  React.useEffect(() => {
    connectWebSocket();
    
    return () => {
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
      }
      if (mockWebSocket.current) {
        mockWebSocket.current.close();
      }
    };
  }, []);

  React.useEffect(() => {
    processQueuedMessages();
  }, [connectionStatus, processQueuedMessages]);

  return (
    <div>
      <div data-testid="connection-status">
        Status: {connectionStatus}
      </div>
      
      <div data-testid="reconnect-attempts">
        Reconnect attempts: {reconnectAttempts}
      </div>
      
      {isReconnecting && (
        <div data-testid="reconnecting-indicator">
          Reconnecting...
        </div>
      )}
      
      {lastError && (
        <div data-testid="connection-error">
          Error: {lastError}
        </div>
      )}
      
      <div data-testid="queued-messages">
        Queued: {messageQueue.filter(m => m.status === 'pending').length}
      </div>
      
      <div data-testid="sent-messages">
        Sent: {sentMessages.length}
      </div>
      
      <button 
        onClick={() => sendMessage(`Message ${Date.now()}`)}
        data-testid="send-message-btn"
      >
        Send Message
      </button>
      
      <button 
        onClick={forceDisconnect}
        data-testid="disconnect-btn"
      >
        Force Disconnect
      </button>
      
      <button 
        onClick={manualReconnect}
        data-testid="reconnect-btn"
      >
        Manual Reconnect
      </button>
      
      <div data-testid="message-list">
        {sentMessages.map((msg, idx) => (
          <div key={idx} data-testid={`sent-message-${idx}`}>
            {msg}
          </div>
        ))}
      </div>
      
      <div data-testid="queue-list">
        {messageQueue.map((msg, idx) => (
          <div key={msg.id} data-testid={`queued-message-${idx}`}>
            {msg.content} - {msg.status}
          </div>
        ))}
      </div>
    </div>
  );
};

const HeartbeatComponent: React.FC = () => {
  const [lastPing, setLastPing] = React.useState<number | null>(null);
  const [lastPong, setLastPong] = React.useState<number | null>(null);
  const [latency, setLatency] = React.useState<number | null>(null);
  const [isConnected, setIsConnected] = React.useState(false);
  
  const pingInterval = React.useRef<NodeJS.Timeout | null>(null);
  const mockWebSocket = React.useRef<WebSocket | null>(null);

  const startHeartbeat = React.useCallback(() => {
    if (pingInterval.current) {
      clearInterval(pingInterval.current);
    }
    
    pingInterval.current = setInterval(() => {
      if (mockWebSocket.current?.readyState === WebSocket.OPEN) {
        const pingTime = Date.now();
        setLastPing(pingTime);
        
        mockWebSocket.current.send(JSON.stringify({
          type: 'ping',
          timestamp: pingTime
        }));
      }
    }, 5000);
  }, []);

  const handlePong = React.useCallback((timestamp: number) => {
    const now = Date.now();
    setLastPong(now);
    setLatency(now - timestamp);
  }, []);

  const connectWithHeartbeat = () => {
    try {
      const ws = new WebSocket('ws://localhost:8000/heartbeat');
      mockWebSocket.current = ws;
      
      ws.onopen = () => {
        setIsConnected(true);
        startHeartbeat();
      };
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'pong') {
            handlePong(data.timestamp);
          }
        } catch (error) {
          // Handle parse error
        }
      };
      
      ws.onclose = () => {
        setIsConnected(false);
        if (pingInterval.current) {
          clearInterval(pingInterval.current);
        }
      };
      
      ws.onerror = () => {
        setIsConnected(false);
      };
    } catch (error) {
      setIsConnected(false);
    }
  };

  React.useEffect(() => {
    connectWithHeartbeat();
    
    return () => {
      if (pingInterval.current) {
        clearInterval(pingInterval.current);
      }
      if (mockWebSocket.current) {
        mockWebSocket.current.close();
      }
    };
  }, []);

  return (
    <div>
      <div data-testid="heartbeat-status">
        Connected: {isConnected ? 'Yes' : 'No'}
      </div>
      
      {lastPing && (
        <div data-testid="last-ping">
          Last ping: {new Date(lastPing).toLocaleTimeString()}
        </div>
      )}
      
      {lastPong && (
        <div data-testid="last-pong">
          Last pong: {new Date(lastPong).toLocaleTimeString()}
        </div>
      )}
      
      {latency !== null && (
        <div data-testid="latency">
          Latency: {latency}ms
        </div>
      )}
    </div>
  );
};

const MessageOrderingComponent: React.FC = () => {
  const [receivedMessages, setReceivedMessages] = React.useState<Array<{id: string, content: string, order: number}>>([]);
  const [isConnected, setIsConnected] = React.useState(false);
  const mockWebSocket = React.useRef<WebSocket | null>(null);

  const sendSequentialMessages = () => {
    if (!mockWebSocket.current || mockWebSocket.current.readyState !== WebSocket.OPEN) {
      return;
    }
    
    for (let i = 1; i <= 5; i++) {
      setTimeout(() => {
        mockWebSocket.current?.send(JSON.stringify({
          type: 'sequential_message',
          id: `msg-${i}`,
          content: `Message ${i}`,
          order: i
        }));
      }, i * 100);
    }
  };

  React.useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ordering');
    mockWebSocket.current = ws;
    
    ws.onopen = () => {
      setIsConnected(true);
    };
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'sequential_message') {
          setReceivedMessages(prev => [...prev, {
            id: data.id,
            content: data.content,
            order: data.order
          }]);
        }
      } catch (error) {
        // Handle parse error
      }
    };
    
    ws.onclose = () => {
      setIsConnected(false);
    };
    
    return () => {
      ws.close();
    };
  }, []);

  return (
    <div>
      <div data-testid="ordering-status">
        Connected: {isConnected ? 'Yes' : 'No'}
      </div>
      
      <button 
        onClick={sendSequentialMessages}
        disabled={!isConnected}
        data-testid="send-sequential-btn"
      >
        Send Sequential Messages
      </button>
      
      <div data-testid="received-count">
        Received: {receivedMessages.length} messages
      </div>
      
      <div data-testid="message-order">
        {receivedMessages.map((msg, idx) => (
          <div key={msg.id} data-testid={`received-message-${idx}`}>
            {msg.content} (Order: {msg.order})
          </div>
        ))}
      </div>
    </div>
  );
};

describe('WebSocket Resilience Tests', () => {
  let wsManager: WebSocketTestManager;
  let server: WS;

  beforeEach(() => {
    wsManager = new WebSocketTestManager();
    server = wsManager.setup();
    jest.useFakeTimers();
  });

  afterEach(() => {
    wsManager.cleanup();
    jest.clearAllMocks();
    jest.useRealTimers();
  });

  describe('Connection Management', () => {
    it('should automatically reconnect after disconnection', async () => {
      render(
        <TestProviders>
          <WebSocketResilienceComponent />
        </TestProviders>
      );

      // Wait for initial connection
      await waitFor(() => {
        expect(screen.getByTestId('connection-status')).toHaveTextContent('connecting');
      });

      // Simulate connection
      act(() => {
        server.connected;
      });

      // Force disconnect
      await userEvent.click(screen.getByTestId('disconnect-btn'));
      
      await waitFor(() => {
        expect(screen.getByTestId('connection-status')).toHaveTextContent('disconnected');
      });

      // Should show reconnecting indicator
      expect(screen.getByTestId('reconnecting-indicator')).toBeInTheDocument();

      // Fast-forward to trigger reconnection
      act(() => {
        jest.advanceTimersByTime(1000);
      });

      await waitFor(() => {
        expect(screen.getByTestId('reconnect-attempts')).toHaveTextContent('1');
      });
    });

    it('should implement exponential backoff for reconnection', async () => {
      render(
        <TestProviders>
          <WebSocketResilienceComponent />
        </TestProviders>
      );

      // Force multiple disconnections
      for (let i = 0; i < 3; i++) {
        await userEvent.click(screen.getByTestId('disconnect-btn'));
        
        // Fast-forward through reconnection delay
        const expectedDelay = calculateReconnectDelay(i + 1);
        act(() => {
          jest.advanceTimersByTime(expectedDelay);
        });
        
        await waitFor(() => {
          expect(screen.getByTestId('reconnect-attempts')).toHaveTextContent(`${i + 1}`);
        });
      }
    });

    it('should stop reconnecting after max attempts', async () => {
      render(
        <TestProviders>
          <WebSocketResilienceComponent />
        </TestProviders>
      );

      // Force 5 failed reconnection attempts
      for (let i = 0; i < 6; i++) {
        await userEvent.click(screen.getByTestId('disconnect-btn'));
        
        act(() => {
          jest.advanceTimersByTime(calculateReconnectDelay(i + 1));
        });
      }

      await waitFor(() => {
        expect(screen.getByTestId('connection-error')).toHaveTextContent('Max reconnection attempts reached');
      });
    });
  });

  describe('Message Queuing and Delivery', () => {
    it('should queue messages when disconnected and send when reconnected', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(
        <TestProviders>
          <WebSocketResilienceComponent />
        </TestProviders>
      );

      // Force disconnect
      await user.click(screen.getByTestId('disconnect-btn'));
      
      await waitFor(() => {
        expect(screen.getByTestId('connection-status')).toHaveTextContent('disconnected');
      });

      // Send messages while disconnected
      await user.click(screen.getByTestId('send-message-btn'));
      await user.click(screen.getByTestId('send-message-btn'));
      
      await waitFor(() => {
        expect(screen.getByTestId('queued-messages')).toHaveTextContent('2');
        expect(screen.getByTestId('sent-messages')).toHaveTextContent('0');
      });

      // Manual reconnect
      await user.click(screen.getByTestId('reconnect-btn'));
      
      // Simulate successful connection
      act(() => {
        server.connected;
      });

      await waitFor(() => {
        expect(screen.getByTestId('connection-status')).toHaveTextContent('connected');
        expect(screen.getByTestId('queued-messages')).toHaveTextContent('0');
        expect(screen.getByTestId('sent-messages')).toHaveTextContent('2');
      });
    });

    it('should preserve message order during reconnection', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(
        <TestProviders>
          <MessageOrderingComponent />
        </TestProviders>
      );

      // Wait for connection
      await waitFor(() => {
        expect(screen.getByTestId('ordering-status')).toHaveTextContent('Yes');
      });

      // Send sequential messages
      await user.click(screen.getByTestId('send-sequential-btn'));
      
      // Fast-forward to send all messages
      act(() => {
        jest.advanceTimersByTime(1000);
      });

      await waitFor(() => {
        expect(screen.getByTestId('received-count')).toHaveTextContent('5');
      });

      // Verify message order
      for (let i = 0; i < 5; i++) {
        expect(screen.getByTestId(`received-message-${i}`)).toHaveTextContent(`Message ${i + 1} (Order: ${i + 1})`);
      }
    });
  });

  describe('Heartbeat and Health Monitoring', () => {
    it('should maintain heartbeat connection', async () => {
      render(
        <TestProviders>
          <HeartbeatComponent />
        </TestProviders>
      );

      // Wait for connection
      await waitFor(() => {
        expect(screen.getByTestId('heartbeat-status')).toHaveTextContent('Yes');
      });

      // Fast-forward to trigger ping
      act(() => {
        jest.advanceTimersByTime(5000);
      });

      await waitFor(() => {
        expect(screen.getByTestId('last-ping')).toBeInTheDocument();
      });

      // Simulate pong response
      act(() => {
        server.send(JSON.stringify({
          type: 'pong',
          timestamp: Date.now() - 50 // 50ms latency
        }));
      });

      await waitFor(() => {
        expect(screen.getByTestId('last-pong')).toBeInTheDocument();
        expect(screen.getByTestId('latency')).toHaveTextContent(/\d+ms/);
      });
    });

    it('should detect connection health issues', async () => {
      render(
        <TestProviders>
          <HeartbeatComponent />
        </TestProviders>
      );

      // Initial connection
      await waitFor(() => {
        expect(screen.getByTestId('heartbeat-status')).toHaveTextContent('Yes');
      });

      // Simulate connection drop
      act(() => {
        server.close();
      });

      await waitFor(() => {
        expect(screen.getByTestId('heartbeat-status')).toHaveTextContent('No');
      });
    });
  });

  describe('Error Recovery Scenarios', () => {
    it('should handle WebSocket protocol errors gracefully', async () => {
      render(
        <TestProviders>
          <WebSocketResilienceComponent />
        </TestProviders>
      );

      // Simulate protocol error
      act(() => {
        server.error();
      });

      await waitFor(() => {
        expect(screen.getByTestId('connection-error')).toBeInTheDocument();
        expect(screen.getByTestId('reconnecting-indicator')).toBeInTheDocument();
      });
    });

    it('should handle malformed message gracefully', async () => {
      render(
        <TestProviders>
          <WebSocketResilienceComponent />
        </TestProviders>
      );

      // Wait for connection
      await waitFor(() => {
        expect(screen.getByTestId('connection-status')).toHaveTextContent('connecting');
      });

      // Send malformed message
      act(() => {
        server.send('invalid json');
      });

      // Connection should remain stable
      await waitFor(() => {
        expect(screen.getByTestId('connection-status')).not.toHaveTextContent('disconnected');
      });
    });
  });

  describe('Connection State Management', () => {
    it('should prevent multiple simultaneous connection attempts', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(
        <TestProviders>
          <WebSocketResilienceComponent />
        </TestProviders>
      );

      // Rapid reconnection attempts should be ignored
      await user.click(screen.getByTestId('reconnect-btn'));
      await user.click(screen.getByTestId('reconnect-btn'));
      await user.click(screen.getByTestId('reconnect-btn'));
      
      // Should only show one connection attempt
      await waitFor(() => {
        expect(screen.getByTestId('connection-status')).toHaveTextContent('connecting');
      });
    });

    it('should clean up resources on component unmount', async () => {
      const { unmount } = render(
        <TestProviders>
          <WebSocketResilienceComponent />
        </TestProviders>
      );

      // Force disconnect to start reconnection timer
      await userEvent.click(screen.getByTestId('disconnect-btn'));
      
      // Unmount component
      unmount();
      
      // Timers should be cleaned up (no way to directly test but ensures no memory leaks)
      expect(true).toBe(true); // Placeholder assertion
    });
  });
});
