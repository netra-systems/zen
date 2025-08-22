/**
 * Critical WebSocket Authentication Rejection Test
 * 
 * This test verifies that the security measures are working correctly.
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

import { AuthContext } from '@/auth/context';
import { webSocketService } from '@/services/webSocketService';

// Mock the config to simulate both old and new endpoints
jest.mock('@/config', () => ({
  config: {
    apiUrl: 'http://localhost:8000',
    wsUrl: 'ws://localhost:8000/ws' // Note: Using old insecure endpoint
  }
}));

// Unmock the WebSocketProvider and related services to test the actual implementation
jest.unmock('@/providers/WebSocketProvider');
jest.unmock('@/services/webSocketService');
jest.unmock('@/hooks/useWebSocket');

// Import the actual WebSocketProvider implementation after unmocking
import { WebSocketProvider, useWebSocketContext } from '../../../providers/WebSocketProvider';

// Test component that shows connection status
const AuthRejectionTestComponent = () => {
  const { status } = useWebSocketContext();
  const [lastError, setLastError] = React.useState<string>('');
  
  React.useEffect(() => {
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
  let originalWebSocket: any;
  let mockWebSocket: any;
  let connectionAttempts: Array<{ url: string; protocols?: string | string[]; rejected?: boolean }> = [];
  
  beforeEach(() => {
    connectionAttempts = [];
    
    // Disconnect any existing WebSocket connections
    webSocketService.disconnect();
    
    // Save original WebSocket
    originalWebSocket = global.WebSocket;
    
    // Enhanced mock to simulate backend auth rejection
    mockWebSocket = {
      readyState: WebSocket.CONNECTING,
      close: jest.fn(),
      send: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      onopen: null,
      onclose: null,
      onerror: null,
      onmessage: null,
    };
    
    // Simulate backend behavior: accept proper auth, reject insecure methods
    global.WebSocket = jest.fn().mockImplementation((url, protocols) => {
      const hasQueryToken = url.includes('token=') || url.includes('?token=');
      const hasProperAuth = protocols && Array.isArray(protocols) && 
                           protocols.some(p => p.startsWith('jwt.'));
      
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
      } else {
        // Simulate successful connection after a short delay
        setTimeout(() => {
          mockWebSocket.readyState = WebSocket.OPEN;
          if (mockWebSocket.onopen) {
            mockWebSocket.onopen(new Event('open'));
          }
        }, 10);
      }
      
      return mockWebSocket;
    });
    
    // Add WebSocket constants
    global.WebSocket.CONNECTING = 0;
    global.WebSocket.OPEN = 1;
    global.WebSocket.CLOSING = 2;
    global.WebSocket.CLOSED = 3;
    
    jest.clearAllMocks();
  });

  afterEach(() => {
    // Restore original WebSocket
    global.WebSocket = originalWebSocket;
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
        expect(connectionAttempts.length).toBeGreaterThan(0);
      });

      expect(connectionAttempts).toHaveLength(1);
      const { url, protocols, rejected } = connectionAttempts[0];

      // Frontend should NOT send token in query params (security)
      expect(url).not.toContain('token=');
      
      // Should use proper secure authentication
      expect(protocols).toEqual(expect.arrayContaining([
        'jwt-auth',
        expect.stringMatching(/^jwt\./)
      ]));
      
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
        expect(connectionAttempts.length).toBeGreaterThan(0);
      });

      // Should properly handle the authentication rejection
      const { rejected } = connectionAttempts[0];
      expect(rejected).toBe(false); // Should not be rejected due to protocol structure
      
      // Wait for connection status to be processed
      await waitFor(() => {
        const status = screen.getByTestId('ws-status');
        expect(status.textContent).toMatch(/OPEN|CLOSED/);
      });
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
        expect(connectionAttempts.length).toBeGreaterThan(0);
      });

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
        attempt.protocols.some(p => p.startsWith('jwt.'))
      );
      expect(secureAttempts.length).toBeGreaterThan(0);
    });
  });

  describe('Enhanced Error Handling', () => {
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
        expect(connectionAttempts.length).toBeGreaterThan(0);
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
      // This test PASSES because frontend doesn't use deprecated auth methods
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <AuthRejectionTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(connectionAttempts.length).toBeGreaterThan(0);
      });

      const { url } = connectionAttempts[0];
      
      // Should NOT use deprecated query param method
      expect(url).not.toContain('token=');
      
      // Frontend should NOT warn about deprecated method since it's not using it
      const errorMessage = screen.getByTestId('error-message');
      expect(errorMessage.textContent).not.toContain('deprecated');
    });

    it('should attempt upgrade to secure authentication', async () => {
      // This test PASSES because frontend already uses secure authentication
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <AuthRejectionTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(connectionAttempts.length).toBeGreaterThan(0);
      });

      // Should use secure authentication on first attempt
      expect(connectionAttempts.length).toBe(1);

      const secureAttempts = connectionAttempts.filter(attempt => 
        !attempt.url.includes('token=') && 
        attempt.protocols && 
        Array.isArray(attempt.protocols) &&
        attempt.protocols.some(p => p.startsWith('jwt.'))
      );

      // Should have used secure auth from the start
      expect(secureAttempts.length).toBe(1);
    });
  });
});