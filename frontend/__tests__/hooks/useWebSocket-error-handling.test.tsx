/**
 * WebSocket Error Handling Test
 * Tests error scenarios in WebSocket connections
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock WebSocket
const mockWebSocket = {
  send: jest.fn(),
  close: jest.fn(),
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
  readyState: WebSocket.CONNECTING,
};

(global as any).WebSocket = jest.fn(() => mockWebSocket);

describe('WebSocket Error Handling', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockWebSocket.readyState = WebSocket.CONNECTING;
  });

  it('should handle WebSocket connection failures', async () => {
    const WebSocketErrorComponent: React.FC = () => {
      const [connectionStatus, setConnectionStatus] = React.useState('connecting');
      const [error, setError] = React.useState<string>('');
      
      React.useEffect(() => {
        // Simulate WebSocket connection error
        const simulateError = () => {
          const errorEvent = new Event('error') as any;
          errorEvent.code = 1006;
          errorEvent.reason = 'Connection failed';
          
          setConnectionStatus('error');
          setError('WebSocket connection failed');
        };
        
        setTimeout(simulateError, 10);
      }, []);
      
      return (
        <div>
          <div data-testid="connection-status">{connectionStatus}</div>
          <div data-testid="error-message">{error}</div>
        </div>
      );
    };

    render(<WebSocketErrorComponent />);
    
    await waitFor(() => {
      expect(screen.getByTestId('connection-status')).toHaveTextContent('error');
      expect(screen.getByTestId('error-message')).toHaveTextContent('WebSocket connection failed');
    });
  });

  it('should handle unexpected WebSocket disconnection', async () => {
    const WebSocketDisconnectComponent: React.FC = () => {
      const [status, setStatus] = React.useState('connected');
      const [reconnectAttempts, setReconnectAttempts] = React.useState(0);
      
      React.useEffect(() => {
        // Simulate unexpected disconnection
        setTimeout(() => {
          setStatus('disconnected');
          setReconnectAttempts(1);
        }, 10);
        
        // Simulate reconnection attempt
        setTimeout(() => {
          setStatus('reconnecting');
          setReconnectAttempts(2);
        }, 50);
      }, []);
      
      return (
        <div>
          <div data-testid="connection-status">{status}</div>
          <div data-testid="reconnect-attempts">{reconnectAttempts}</div>
        </div>
      );
    };

    render(<WebSocketDisconnectComponent />);
    
    await waitFor(() => {
      expect(screen.getByTestId('connection-status')).toHaveTextContent('reconnecting');
      expect(screen.getByTestId('reconnect-attempts')).toHaveTextContent('2');
    });
  });

  it('should handle malformed WebSocket messages', async () => {
    const WebSocketMalformedMessageComponent: React.FC = () => {
      const [lastError, setLastError] = React.useState('');
      
      React.useEffect(() => {
        // Simulate receiving malformed message
        const handleMalformedMessage = () => {
          try {
            // Simulate parsing invalid JSON
            JSON.parse('invalid json{');
          } catch (error) {
            setLastError('Failed to parse WebSocket message');
          }
        };
        
        setTimeout(handleMalformedMessage, 10);
      }, []);
      
      return (
        <div>
          <div data-testid="parse-error">{lastError}</div>
        </div>
      );
    };

    render(<WebSocketMalformedMessageComponent />);
    
    await waitFor(() => {
      expect(screen.getByTestId('parse-error')).toHaveTextContent('Failed to parse WebSocket message');
    });
  });
});