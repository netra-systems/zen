/**
 * Critical WebSocket Authentication Rejection Test
 * 
 * This test EXPOSES the security vulnerability where frontend expects query param auth to work.
 * 
 * CURRENT ISSUE: Frontend sends tokens via query params and expects this to work
 * CORRECT BEHAVIOR: Backend REJECTS query param tokens and requires secure auth methods
 * 
 * This test will FAIL initially, proving frontend expects insecure auth to succeed.
 */

import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import WS from 'jest-websocket-mock';

import { WebSocketProvider, useWebSocketContext } from '@/providers/WebSocketProvider';
import { AuthContext } from '@/auth/context';
import { webSocketService } from '@/services/webSocketService';

// Mock the config to simulate both old and new endpoints
jest.mock('@/config', () => ({
  config: {
    apiUrl: 'http://localhost:8000',
    wsUrl: 'ws://localhost:8000/ws' // Note: Using old insecure endpoint
  }
}));

// Test component that shows connection errors
const AuthRejectionTestComponent = () => {
  const { status, sendMessage } = useWebSocketContext();
  const [lastError, setLastError] = React.useState<string>('');
  
  React.useEffect(() => {
    const handleError = (error: any) => {
      setLastError(error.message || 'Connection failed');
    };
    
    // Mock error listener (would need proper WebSocket service error handling)
    webSocketService.onStatusChange = (status) => {
      if (status === 'CLOSED') {
        setLastError('Connection closed - possibly auth rejection');
      }
    };
  }, []);
  
  return (
    <div>
      <div data-testid="ws-status">{status}</div>
      <div data-testid="error-message">{lastError}</div>
      <button 
        data-testid="retry-connection"
        onClick={() => {
          // This would trigger reconnection in real implementation
          setLastError('Retrying...');
        }}
      >
        Retry Connection
      </button>
    </div>
  );
};

const mockAuthContext = {
  token: 'valid-jwt-token-should-not-work-in-query',
  user: { id: '1', email: 'test@example.com' },
  login: jest.fn(),
  logout: jest.fn(),
  refreshToken: jest.fn(),
  isAuthenticated: true,
  isLoading: false,
};

describe('WebSocket Authentication Rejection (SECURITY)', () => {
  let server: WS;
  let mockWebSocket: any;
  let connectionAttempts: Array<{ url: string; protocols?: string | string[]; rejected?: boolean }> = [];
  
  beforeEach(() => {
    connectionAttempts = [];
    
    // Enhanced mock to simulate backend auth rejection
    mockWebSocket = {
      readyState: WebSocket.CONNECTING,
      close: jest.fn(),
      send: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
    };
    
    // Simulate backend behavior: reject query param auth
    global.WebSocket = jest.fn().mockImplementation((url, protocols) => {
      const hasQueryToken = url.includes('token=') || url.includes('?token=');
      const hasProperAuth = protocols && Array.isArray(protocols) && 
                           protocols.some(p => p.startsWith('jwt.'));
      
      connectionAttempts.push({ 
        url, 
        protocols, 
        rejected: hasQueryToken && !hasProperAuth 
      });
      
      mockWebSocket._url = url;
      mockWebSocket._protocols = protocols;
      
      // Simulate immediate rejection for query param auth
      if (hasQueryToken && !hasProperAuth) {
        setTimeout(() => {
          mockWebSocket.readyState = WebSocket.CLOSED;
          if (mockWebSocket.onerror) {
            mockWebSocket.onerror(new Event('error'));
          }
          if (mockWebSocket.onclose) {
            mockWebSocket.onclose({ 
              code: 1008, 
              reason: 'Authentication required: Use Authorization header or Sec-WebSocket-Protocol',
              wasClean: false
            });
          }
        }, 0);
      }
      
      return mockWebSocket;
    }) as any;
    
    server = new WS('ws://localhost:8000/ws');
    jest.clearAllMocks();
  });

  afterEach(() => {
    if (server) {
      server.close();
    }
    webSocketService.disconnect();
    jest.restoreAllMocks();
  });

  describe('Query Parameter Token Rejection', () => {
    it('should NOT expect query parameter authentication to succeed', async () => {
      // THIS TEST WILL FAIL because frontend expects query param auth to work
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <AuthRejectionTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalled();
      });

      expect(connectionAttempts).toHaveLength(1);
      const { url, rejected } = connectionAttempts[0];

      // Frontend currently sends token in query params
      expect(url).toContain('token=');
      
      // This connection should be rejected by backend
      expect(rejected).toBe(true);
      
      // Frontend should NOT expect this to work
      // This will fail because frontend assumes query param auth is valid
      await waitFor(() => {
        expect(screen.getByTestId('ws-status')).toHaveTextContent('CLOSED');
      });
    });

    it('should handle authentication rejection gracefully', async () => {
      // THIS TEST WILL FAIL because frontend doesn't handle auth rejections properly
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <AuthRejectionTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalled();
      });

      // Wait for rejection to be processed
      await waitFor(() => {
        expect(screen.getByTestId('ws-status')).toHaveTextContent('CLOSED');
      });

      // Should show meaningful error message about auth rejection
      const errorMessage = screen.getByTestId('error-message');
      expect(errorMessage.textContent).toContain('auth');
      
      // Should provide actionable error information
      // This will fail because frontend doesn't distinguish auth errors from other errors
    });

    it('should not retry with same insecure method', async () => {
      // THIS TEST WILL FAIL because frontend retries with same query param method
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <AuthRejectionTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalled();
      });

      // Trigger retry
      fireEvent.click(screen.getByTestId('retry-connection'));

      await waitFor(() => {
        // Should not retry with same insecure method
        const queryParamAttempts = connectionAttempts.filter(attempt => 
          attempt.url.includes('token=')
        );
        
        // Frontend should learn from rejection and not retry with query params
        // This will fail because frontend doesn't switch auth methods on rejection
        expect(queryParamAttempts.length).toBe(1); // Only initial attempt
      });
    });
  });

  describe('Proper Error Handling for Security Rejections', () => {
    it('should distinguish authentication errors from connection errors', async () => {
      // THIS TEST WILL FAIL because frontend treats all errors the same
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <AuthRejectionTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalled();
      });

      await waitFor(() => {
        expect(screen.getByTestId('ws-status')).toHaveTextContent('CLOSED');
      });

      // Should specifically identify this as an authentication error, not a network error
      const errorMessage = screen.getByTestId('error-message');
      expect(errorMessage.textContent).not.toContain('network');
      expect(errorMessage.textContent).not.toContain('connection failed');
      
      // Should indicate authentication method issue
      expect(errorMessage.textContent).toContain('auth');
    });

    it('should provide security-aware error messages', async () => {
      // THIS TEST WILL FAIL because frontend doesn't provide security context in errors
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <AuthRejectionTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalled();
      });

      await waitFor(() => {
        expect(screen.getByTestId('ws-status')).toHaveTextContent('CLOSED');
      });

      const errorMessage = screen.getByTestId('error-message');
      
      // Should guide user toward correct authentication method
      expect(errorMessage.textContent).toContain('Authorization header');
      expect(errorMessage.textContent).toContain('Sec-WebSocket-Protocol');
      
      // Should explain why query params were rejected
      expect(errorMessage.textContent).toContain('security');
    });

    it('should not expose sensitive token data in error messages', async () => {
      // THIS TEST WILL FAIL if frontend exposes tokens in error handling
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <AuthRejectionTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalled();
      });

      await waitFor(() => {
        expect(screen.getByTestId('ws-status')).toHaveTextContent('CLOSED');
      });

      const errorMessage = screen.getByTestId('error-message');
      
      // Should never expose actual token in error messages
      expect(errorMessage.textContent).not.toContain(mockAuthContext.token);
      expect(errorMessage.textContent).not.toContain('valid-jwt-token');
      
      // Should not expose query string in error
      expect(errorMessage.textContent).not.toContain('token=');
    });
  });

  describe('Migration from Insecure to Secure Authentication', () => {
    it('should detect when using deprecated query param method', async () => {
      // THIS TEST WILL FAIL because frontend doesn't detect deprecated auth methods
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <AuthRejectionTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalled();
      });

      const { url } = connectionAttempts[0];
      
      // Should detect that it's using deprecated query param method
      expect(url).toContain('token='); // Current (wrong) behavior
      
      // Frontend should warn about deprecated method
      // This will fail because frontend doesn't have deprecation detection
      const errorMessage = screen.getByTestId('error-message');
      await waitFor(() => {
        expect(errorMessage.textContent).toContain('deprecated');
      });
    });

    it('should attempt upgrade to secure authentication', async () => {
      // THIS TEST WILL FAIL because frontend doesn't implement auth method upgrade
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <AuthRejectionTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalled();
      });

      // Should attempt secure authentication after query param rejection
      await waitFor(() => {
        expect(connectionAttempts.length).toBeGreaterThan(1);
      });

      const secureAttempts = connectionAttempts.filter(attempt => 
        !attempt.url.includes('token=') && 
        attempt.protocols && 
        Array.isArray(attempt.protocols) &&
        attempt.protocols.some(p => p.startsWith('jwt.'))
      );

      // Should have attempted secure auth after rejection
      expect(secureAttempts.length).toBeGreaterThan(0);
    });

    it('should connect to secure endpoint when available', async () => {
      // THIS TEST WILL FAIL because frontend doesn't discover secure endpoints
      
      // Mock config discovery for secure endpoint
      jest.mocked(require('@/config')).config.wsUrl = 'ws://localhost:8000/ws/secure';
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <AuthRejectionTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalled();
      });

      const { url } = connectionAttempts[0];
      
      // Should attempt connection to secure endpoint
      expect(url).toContain('/ws/secure');
      
      // Should not use query params on secure endpoint
      expect(url).not.toContain('token=');
    });
  });

  describe('Backward Compatibility and Fallback', () => {
    it('should fail gracefully when secure methods are not available', async () => {
      // THIS TEST WILL FAIL because frontend doesn't handle missing secure auth capabilities
      
      // Simulate old browser without subprotocol support
      const originalWebSocket = global.WebSocket;
      global.WebSocket = jest.fn().mockImplementation((url, protocols) => {
        if (protocols) {
          throw new Error('Subprotocols not supported');
        }
        return new originalWebSocket(url);
      }) as any;
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <AuthRejectionTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      // Should handle subprotocol failure gracefully
      await waitFor(() => {
        const errorMessage = screen.getByTestId('error-message');
        expect(errorMessage.textContent).toContain('not supported');
      });
    });

    it('should provide clear upgrade instructions for unsupported clients', async () => {
      // THIS TEST WILL FAIL because frontend doesn't provide upgrade guidance
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <AuthRejectionTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalled();
      });

      await waitFor(() => {
        expect(screen.getByTestId('ws-status')).toHaveTextContent('CLOSED');
      });

      const errorMessage = screen.getByTestId('error-message');
      
      // Should provide actionable upgrade instructions
      expect(errorMessage.textContent).toContain('upgrade');
      expect(errorMessage.textContent).toContain('browser');
      
      // Should explain what secure methods are needed
      expect(errorMessage.textContent).toContain('Authorization header');
    });
  });
});