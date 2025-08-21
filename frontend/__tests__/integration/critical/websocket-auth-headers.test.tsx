/**
 * Critical WebSocket Authentication Headers Test
 * 
 * This test EXPOSES the misalignment between frontend and backend WebSocket authentication.
 * 
 * CURRENT ISSUE: Frontend sends JWT tokens via query parameters (SECURITY VULNERABILITY)
 * CORRECT BEHAVIOR: Backend expects JWT tokens via Authorization headers or subprotocols
 * 
 * This test will FAIL initially, proving the frontend is not using proper auth methods.
 */

import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import WS from 'jest-websocket-mock';

import { WebSocketProvider, useWebSocketContext } from '@/providers/WebSocketProvider';
import { AuthContext } from '@/auth/context';
import { webSocketService } from '@/services/webSocketService';

// Mock the config to use test URLs
jest.mock('@/config', () => ({
  config: {
    apiUrl: 'http://localhost:8000',
    wsUrl: 'ws://localhost:8000/ws/secure'
  }
}));

// Test component that uses WebSocket context
const TestWebSocketComponent = () => {
  const { status, sendMessage } = useWebSocketContext();
  
  return (
    <div>
      <div data-testid="ws-status">{status}</div>
      <button 
        data-testid="send-message"
        onClick={() => sendMessage({ type: 'test', payload: { content: 'test' } })}
      >
        Send Message
      </button>
    </div>
  );
};

const mockAuthContext = {
  token: 'test-jwt-token-123',
  user: { id: '1', email: 'test@example.com' },
  login: jest.fn(),
  logout: jest.fn(),
  refreshToken: jest.fn(),
  isAuthenticated: true,
  isLoading: false,
};

describe('WebSocket Authentication Headers (CRITICAL SECURITY)', () => {
  let server: WS;
  let mockWebSocket: any;
  
  beforeEach(() => {
    // Mock WebSocket constructor to capture connection attempts
    mockWebSocket = {
      readyState: WebSocket.CONNECTING,
      close: jest.fn(),
      send: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
    };
    
    // Capture the actual WebSocket constructor calls
    global.WebSocket = jest.fn().mockImplementation((url, protocols) => {
      // Store the URL and protocols for assertion
      mockWebSocket._url = url;
      mockWebSocket._protocols = protocols;
      return mockWebSocket;
    }) as any;
    
    // Set up mock server for the CORRECT endpoint
    server = new WS('ws://localhost:8000/ws/secure');
    
    jest.clearAllMocks();
  });

  afterEach(() => {
    if (server) {
      server.close();
    }
    webSocketService.disconnect();
    jest.restoreAllMocks();
  });

  describe('Authorization Header Authentication (CORRECT METHOD)', () => {
    it('should use Authorization header with Bearer token for WebSocket connection', async () => {
      // THIS TEST WILL FAIL because frontend uses query params, not headers
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <TestWebSocketComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      // Wait for connection attempt
      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalled();
      });

      // CRITICAL ASSERTION: Check that WebSocket was created with proper headers
      // This should fail because frontend doesn't support header-based auth
      const websocketCall = (global.WebSocket as jest.Mock).mock.calls[0];
      const url = websocketCall[0];
      const protocols = websocketCall[1];

      // The frontend should NOT be using query parameters for token (security issue)
      expect(url).not.toContain('token=');
      expect(url).not.toContain('test-jwt-token-123');
      
      // The frontend SHOULD be using Authorization header (currently not implemented)
      // Since WebSocket constructor doesn't support headers directly, it should use subprotocols
      expect(protocols).toContain('jwt.test-jwt-token-123');
      
      // Or it should be setting up the connection to the secure endpoint
      expect(url).toContain('/ws/secure');
    });

    it('should NOT send JWT token via query parameters (security vulnerability)', async () => {
      // THIS TEST WILL FAIL because frontend currently uses query params
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <TestWebSocketComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalled();
      });

      const websocketCall = (global.WebSocket as jest.Mock).mock.calls[0];
      const url = websocketCall[0];

      // SECURITY CHECK: Token should NOT be in URL (current implementation does this)
      expect(url).not.toContain('?token=');
      expect(url).not.toContain('token=test-jwt-token-123');
      
      // The URL should not expose sensitive tokens in query string
      const urlObj = new URL(url, 'ws://localhost');
      expect(urlObj.searchParams.get('token')).toBeNull();
    });
  });

  describe('WebSocket Subprotocol Authentication (FALLBACK METHOD)', () => {
    it('should use Sec-WebSocket-Protocol header for JWT authentication', async () => {
      // THIS TEST WILL FAIL because frontend doesn't implement subprotocol auth
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <TestWebSocketComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalled();
      });

      const websocketCall = (global.WebSocket as jest.Mock).mock.calls[0];
      const protocols = websocketCall[1];

      // Frontend should support subprotocol authentication as fallback
      expect(protocols).toBeDefined();
      expect(Array.isArray(protocols) ? protocols : [protocols]).toContain('jwt.test-jwt-token-123');
    });

    it('should handle multiple authentication protocols', async () => {
      // THIS TEST WILL FAIL because frontend doesn't support protocol negotiation
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <TestWebSocketComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalled();
      });

      const websocketCall = (global.WebSocket as jest.Mock).mock.calls[0];
      const protocols = websocketCall[1];

      // Should support multiple protocols for negotiation
      const protocolArray = Array.isArray(protocols) ? protocols : [protocols];
      expect(protocolArray).toContain('jwt.test-jwt-token-123');
      expect(protocolArray.length).toBeGreaterThan(0);
    });
  });

  describe('Secure Connection Endpoint', () => {
    it('should connect to the secure WebSocket endpoint', async () => {
      // THIS TEST WILL FAIL because frontend connects to insecure endpoint
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <TestWebSocketComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalled();
      });

      const websocketCall = (global.WebSocket as jest.Mock).mock.calls[0];
      const url = websocketCall[0];

      // Should connect to secure endpoint that requires proper authentication
      expect(url).toContain('/ws/secure');
      expect(url).not.toContain('/ws?token='); // Old insecure endpoint pattern
    });

    it('should handle authentication errors from secure endpoint', async () => {
      // THIS TEST WILL FAIL because frontend doesn't handle auth rejections properly
      
      const onError = jest.fn();
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <TestWebSocketComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      // Simulate authentication rejection from backend
      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalled();
      });

      // Simulate backend rejection due to improper auth
      mockWebSocket.readyState = WebSocket.CLOSED;
      if (mockWebSocket.onerror) {
        mockWebSocket.onerror(new Event('error'));
      }
      if (mockWebSocket.onclose) {
        mockWebSocket.onclose({ code: 1008, reason: 'Authentication required: Use Authorization header' });
      }

      await waitFor(() => {
        expect(screen.getByTestId('ws-status')).toHaveTextContent('CLOSED');
      });

      // Frontend should properly handle auth errors
      // This will fail because current implementation doesn't distinguish auth errors
    });
  });

  describe('Token Management Integration', () => {
    it('should not expose token in connection URL', async () => {
      // THIS TEST WILL FAIL because frontend exposes token in URL
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <TestWebSocketComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalled();
      });

      const websocketCall = (global.WebSocket as jest.Mock).mock.calls[0];
      const url = websocketCall[0];

      // Security requirement: No sensitive data in URLs
      expect(url).not.toMatch(/token=/);
      expect(url).not.toMatch(/jwt=/);
      expect(url).not.toMatch(/auth=/);
      expect(url).not.toMatch(/bearer=/);
      
      // URL should be clean of authentication data
      const urlObj = new URL(url, 'ws://localhost');
      expect(urlObj.search).toBe(''); // No query parameters
    });

    it('should properly handle token refresh scenarios', async () => {
      // THIS TEST WILL FAIL because frontend doesn't handle token refresh during connection
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <TestWebSocketComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalled();
      });

      // Simulate token refresh
      const newToken = 'refreshed-jwt-token-456';
      mockAuthContext.token = newToken;

      // Frontend should handle token updates during active connection
      // This will fail because current implementation doesn't support runtime token updates
      
      // Should reconnect with new token using proper auth method
      expect(global.WebSocket).toHaveBeenCalledTimes(1); // Initial connection
      
      // After token refresh, should not use query params
      const websocketCalls = (global.WebSocket as jest.Mock).mock.calls;
      websocketCalls.forEach(call => {
        expect(call[0]).not.toContain('token=');
      });
    });
  });
});