/**
 * WebSocket Mock Validation Integration Test
 * 
 * BUSINESS VALUE JUSTIFICATION:
 * - Segment: All (Free → Enterprise)
 * - Business Goal: Ensure WebSocket mocks work correctly in tests
 * - Value Impact: Prevents test infrastructure failures that block deployments
 * - Revenue Impact: Maintains CI/CD reliability for continuous delivery
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MockWebSocket } from '../helpers/websocket-test-helpers';
import { mockWebSocketConnection } from '../helpers/websocket-test-helpers';

// Test component that uses WebSocket
const WebSocketTestComponent: React.FC = () => {
  const [status, setStatus] = React.useState<string>('disconnected');
  const [messages, setMessages] = React.useState<string[]>([]);
  const wsRef = React.useRef<MockWebSocket | null>(null);

  const handleConnect = () => {
    wsRef.current = new MockWebSocket('ws://localhost:8000/ws');
    
    wsRef.current.onopen = () => {
      setStatus('connected');
    };
    
    wsRef.current.onmessage = (event) => {
      setMessages(prev => [...prev, event.data]);
    };
    
    wsRef.current.onclose = () => {
      setStatus('disconnected');
    };
    
    wsRef.current.onerror = () => {
      setStatus('error');
    };
  };

  const handleDisconnect = () => {
    if (wsRef.current) {
      wsRef.current.close();
    }
  };

  const handleSendMessage = () => {
    if (wsRef.current && wsRef.current.readyState === MockWebSocket.OPEN) {
      wsRef.current.send('Hello WebSocket');
    }
  };

  const handleSimulateMessage = () => {
    if (wsRef.current) {
      wsRef.current.simulateMessage('Simulated message from server');
    }
  };

  return (
    <div>
      <div data-testid="status">Status: {status}</div>
      <div data-testid="message-count">Messages: {messages.length}</div>
      <div data-testid="messages">
        {messages.map((msg, index) => (
          <div key={index} data-testid={`message-${index}`}>{msg}</div>
        ))}
      </div>
      <button data-testid="connect-btn" onClick={handleConnect}>Connect</button>
      <button data-testid="disconnect-btn" onClick={handleDisconnect}>Disconnect</button>
      <button data-testid="send-btn" onClick={handleSendMessage}>Send Message</button>
      <button data-testid="simulate-btn" onClick={handleSimulateMessage}>Simulate Message</button>
    </div>
  );
};

describe('WebSocket Mock Validation Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('MockWebSocket Basic Functionality', () => {
    it('should initialize with CONNECTING state and auto-connect to OPEN', async () => {
      render(<WebSocketTestComponent />);
      
      await act(async () => {
        fireEvent.click(screen.getByTestId('connect-btn'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('status')).toHaveTextContent('Status: connected');
      }, { timeout: 1000 });
    });

    it('should handle message sending and receiving', async () => {
      render(<WebSocketTestComponent />);
      
      // Connect first
      await act(async () => {
        fireEvent.click(screen.getByTestId('connect-btn'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('status')).toHaveTextContent('Status: connected');
      });

      // Send a message
      await act(async () => {
        fireEvent.click(screen.getByTestId('send-btn'));
      });

      // Simulate receiving a message
      await act(async () => {
        fireEvent.click(screen.getByTestId('simulate-btn'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('message-count')).toHaveTextContent('Messages: 1');
        expect(screen.getByTestId('message-0')).toHaveTextContent('Simulated message from server');
      });
    });

    it('should handle connection close properly', async () => {
      render(<WebSocketTestComponent />);
      
      // Connect first
      await act(async () => {
        fireEvent.click(screen.getByTestId('connect-btn'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('status')).toHaveTextContent('Status: connected');
      });

      // Disconnect
      await act(async () => {
        fireEvent.click(screen.getByTestId('disconnect-btn'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('status')).toHaveTextContent('Status: disconnected');
      }, { timeout: 1000 });
    });
  });

  describe('mockWebSocketConnection Helper', () => {
    it('should create connected mock with proper structure', () => {
      const mockConnection = mockWebSocketConnection(true);
      
      expect(mockConnection.connected).toBe(true);
      expect(mockConnection.readyState).toBe(WebSocket.OPEN);
      expect(mockConnection.send).toBeDefined();
      expect(mockConnection.close).toBeDefined();
      expect(mockConnection.addEventListener).toBeDefined();
      expect(mockConnection.removeEventListener).toBeDefined();
      expect(mockConnection.url).toBe('ws://localhost:8000/ws');
    });

    it('should create disconnected mock with proper structure', () => {
      const mockConnection = mockWebSocketConnection(false);
      
      expect(mockConnection.connected).toBe(false);
      expect(mockConnection.readyState).toBe(WebSocket.CLOSED);
      expect(mockConnection.send).toBeDefined();
      expect(mockConnection.close).toBeDefined();
    });
  });

  describe('Global WebSocket Mock from jest.setup.js', () => {
    it('should have MockWebSocket available globally', () => {
      expect(global.WebSocket).toBeDefined();
      expect(global.WebSocket.CONNECTING).toBe(0);
      expect(global.WebSocket.OPEN).toBe(1);
      expect(global.WebSocket.CLOSING).toBe(2);
      expect(global.WebSocket.CLOSED).toBe(3);
    });

    it('should create WebSocket instances with proper properties', () => {
      const ws = new WebSocket('ws://test.com');
      
      expect(ws.url).toContain('ws://test.com');
      expect(ws.readyState).toBe(WebSocket.CONNECTING);
      expect(ws.send).toBeDefined();
      expect(ws.close).toBeDefined();
      expect(ws.addEventListener).toBeDefined();
      expect(ws.removeEventListener).toBeDefined();
      expect(ws.dispatchEvent).toBeDefined();
    });

    it('should auto-connect WebSocket after creation', async () => {
      const ws = new WebSocket('ws://test.com');
      let connected = false;
      
      ws.onopen = () => {
        connected = true;
      };

      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 50));
      });

      expect(connected).toBe(true);
      expect(ws.readyState).toBe(WebSocket.OPEN);
    });
  });

  describe('Error Handling', () => {
    it('should handle WebSocket errors gracefully', async () => {
      const ws = new WebSocket('ws://test.com');
      let errorReceived = false;
      
      ws.onerror = () => {
        errorReceived = true;
      };

      await act(async () => {
        (ws as any).simulateError(new Error('Test error'));
      });

      expect(errorReceived).toBe(true);
    });
  });
});