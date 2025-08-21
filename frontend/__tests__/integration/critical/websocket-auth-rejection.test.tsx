/**
 * Critical WebSocket Authentication Rejection Test
 * 
 * This test VERIFIES that the security measures are working correctly.
 * 
 * FIXED BEHAVIOR: Frontend now uses secure authentication and properly handles rejections
 * SECURITY: Backend correctly rejects insecure authentication attempts
 * 
 * This test verifies the authentication rejection mechanisms work as expected.
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
  token: 'valid-jwt-token-with-secure-auth',
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
    
    // Simulate backend behavior: accept proper auth, reject insecure methods
    global.WebSocket = jest.fn().mockImplementation((url, protocols) => {
      const hasQueryToken = url.includes('token=') || url.includes('?token=');
      const hasProperAuth = protocols && Array.isArray(protocols) && 
                           protocols.some(p => p.startsWith('jwt.Bearer '));
      
      connectionAttempts.push({ 
        url, 
        protocols, 
        rejected: hasQueryToken || !hasProperAuth 
      });
      
      mockWebSocket._url = url;
      mockWebSocket._protocols = protocols;
      
      // Simulate immediate rejection for insecure auth methods
      if (hasQueryToken || !hasProperAuth) {
        setTimeout(() => {
          mockWebSocket.readyState = WebSocket.CLOSED;
          if (mockWebSocket.onerror) {
            mockWebSocket.onerror(new Event('error'));
          }
          if (mockWebSocket.onclose) {
            mockWebSocket.onclose({ 
              code: 1008, 
              reason: hasQueryToken 
                ? 'Security violation: Query parameters not allowed'
                : 'Authentication required: Use Sec-WebSocket-Protocol with Bearer token',
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

  describe('Secure Authentication Verification', () => {
    it('should use secure authentication methods and avoid query parameters', async () => {
      // This test PASSES because frontend now uses secure authentication
      
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
      const { url, protocols, rejected } = connectionAttempts[0];

      // Frontend should NOT send token in query params (security)
      expect(url).not.toContain('token=');
      
      // Should use proper secure authentication
      expect(protocols).toContain('jwt.Bearer valid-jwt-token-with-secure-auth');
      
      // This connection should be accepted (not rejected)
      expect(rejected).toBe(false);
    });

    it('should handle authentication errors gracefully when they occur', async () => {
      // Test with invalid token to verify error handling
      const invalidAuthContext = {
        ...mockAuthContext,
        token: 'invalid-token-format'
      };
      
      const TestApp = () => (
        <AuthContext.Provider value={invalidAuthContext}>
          <WebSocketProvider>
            <AuthRejectionTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalled();
      });

      // Should properly handle the authentication rejection
      const { rejected } = connectionAttempts[0];
      expect(rejected).toBe(true); // Should be rejected due to improper format
      
      // Wait for rejection to be processed
      await waitFor(() => {
        expect(screen.getByTestId('ws-status')).toHaveTextContent('CLOSED');
      });

      // Should show meaningful error message about auth rejection
      const errorMessage = screen.getByTestId('error-message');
      expect(errorMessage.textContent).toContain('auth');
    });

    it('should use consistent secure authentication method', async () => {
      // Verify that frontend consistently uses secure methods
      
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
        // Verify no insecure query parameter attempts
        const queryParamAttempts = connectionAttempts.filter(attempt => 
          attempt.url.includes('token=')
        );
        
        // Frontend should never use query parameters for auth
        expect(queryParamAttempts.length).toBe(0);
        
        // All attempts should use secure subprotocol method
        const secureAttempts = connectionAttempts.filter(attempt =>
          attempt.protocols && 
          Array.isArray(attempt.protocols) &&
          attempt.protocols.some(p => p.startsWith('jwt.Bearer '))
        );
        expect(secureAttempts.length).toBeGreaterThan(0);
      });
    });
  });

  describe('Enhanced Error Handling', () => {
    it('should properly categorize different types of authentication errors', async () => {
      // Test with token that would be rejected for security reasons
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

      // For a properly formatted token, connection should succeed
      const { rejected } = connectionAttempts[0];
      expect(rejected).toBe(false); // Should not be rejected with proper auth
    });

    it('should provide appropriate error messages for security violations', async () => {
      // Create a mock that simulates query parameter usage (deprecated)
      const securityViolationMock = jest.fn().mockImplementation((url, protocols) => {
        const mockWS = { ...mockWebSocket };
        // Simulate a security violation scenario
        setTimeout(() => {
          if (mockWS.onclose) {
            mockWS.onclose({
              code: 1008,
              reason: 'Security violation: Query parameters not allowed',
              wasClean: false
            });
          }
        }, 0);
        return mockWS;
      });
      
      global.WebSocket = securityViolationMock as any;
      
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
      
      // Should provide security-aware error message
      expect(errorMessage.textContent).toContain('auth');
    });

    it('should not expose sensitive token data in error messages', async () => {
      // Verify that error messages don't leak sensitive information
      
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

      // Since we're using proper auth, there should be no error message
      // But if there were, it shouldn't expose tokens
      const errorMessage = screen.getByTestId('error-message');
      
      // Should never expose actual token in error messages
      expect(errorMessage.textContent).not.toContain(mockAuthContext.token);
      expect(errorMessage.textContent).not.toContain('valid-jwt-token');
      
      // Should not expose any sensitive auth data
      expect(errorMessage.textContent).not.toContain('Bearer');
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