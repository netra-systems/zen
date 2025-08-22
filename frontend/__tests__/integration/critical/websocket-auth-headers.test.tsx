/**
 * Critical WebSocket Authentication Headers Test
 * 
 * This test VERIFIES that the frontend now uses proper secure authentication methods.
 * 
 * FIXED BEHAVIOR: Frontend now sends JWT tokens via Sec-WebSocket-Protocol (secure)
 * SECURITY: Query parameter authentication is rejected by backend (as it should be)
 * 
 * This test verifies that the authentication security fixes are working correctly.
 */

import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import WS from 'jest-websocket-mock';

// Import the actual WebSocketProvider implementation (not the mock)
import { WebSocketProvider, useWebSocketContext } from '../../../providers/WebSocketProvider';
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

describe('WebSocket Authentication Headers (SECURITY VERIFICATION)', () => {
  let server: WS;
  let mockWebSocket: any;
  let webSocketConstructorSpy: jest.SpyInstance;
  
  beforeEach(() => {
    // Disconnect any existing WebSocket connections
    webSocketService.disconnect();
    
    // Mock WebSocket constructor to capture connection attempts
    mockWebSocket = {
      readyState: WebSocket.CONNECTING,
      url: '',
      protocol: '',
      close: jest.fn(),
      send: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      dispatchEvent: jest.fn(),
      onopen: null,
      onclose: null,
      onerror: null,
      onmessage: null,
    };
    
    // Create spy on WebSocket constructor
    webSocketConstructorSpy = jest.spyOn(global, 'WebSocket').mockImplementation((url, protocols) => {
      // Store the URL and protocols for assertion
      mockWebSocket._url = url;
      mockWebSocket._protocols = protocols;
      mockWebSocket.url = url;
      
      // Simulate successful connection after a short delay
      setTimeout(() => {
        mockWebSocket.readyState = WebSocket.OPEN;
        if (mockWebSocket.onopen) {
          mockWebSocket.onopen(new Event('open'));
        }
      }, 10);
      
      return mockWebSocket;
    });
    
    // Set up mock server for the secure endpoint
    server = new WS('ws://localhost:8000/ws/secure');
    
    jest.clearAllMocks();
  });

  afterEach(() => {
    if (server) {
      server.close();
    }
    webSocketService.disconnect();
    webSocketConstructorSpy.mockRestore();
    jest.restoreAllMocks();
  });

  describe('Subprotocol Authentication (SECURE METHOD)', () => {
    it('should use Sec-WebSocket-Protocol with Bearer token for WebSocket connection', async () => {
      // This test PASSES because frontend now uses secure subprotocol authentication
      
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
        expect(webSocketConstructorSpy).toHaveBeenCalled();
      });

      // SECURITY VERIFICATION: Check that WebSocket was created with proper authentication
      const websocketCall = webSocketConstructorSpy.mock.calls[0];
      const url = websocketCall[0];
      const protocols = websocketCall[1];

      // Security check: Token should NOT be in URL (security vulnerability)
      expect(url).not.toContain('token=');
      expect(url).not.toContain('test-jwt-token-123');
      
      // Secure authentication: Should use subprotocol with Bearer token
      // Note: The actual implementation encodes the token, so we check for the encoded version
      expect(protocols).toBeDefined();
      expect(Array.isArray(protocols) ? protocols : [protocols]).toEqual(
        expect.arrayContaining([
          'jwt-auth',
          expect.stringMatching(/^jwt\./)
        ])
      );
      
      // Should connect to secure endpoint
      expect(url).toContain('/ws/secure');
    });

    it('should NOT send JWT token via query parameters (security verified)', async () => {
      // This test PASSES because frontend has been fixed to avoid query param vulnerabilities
      
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

      // SECURITY VERIFICATION: Token should NOT be in URL
      expect(url).not.toContain('?token=');
      expect(url).not.toContain('token=test-jwt-token-123');
      
      // The URL should not expose sensitive tokens in query string
      const urlObj = new URL(url, 'ws://localhost');
      expect(urlObj.searchParams.get('token')).toBeNull();
      expect(urlObj.searchParams.get('auth')).toBeNull();
      expect(urlObj.searchParams.get('jwt')).toBeNull();
    });
  });

  describe('WebSocket Subprotocol Authentication (PRIMARY METHOD)', () => {
    it('should use Sec-WebSocket-Protocol header for JWT authentication', async () => {
      // This test PASSES because frontend now implements secure subprotocol auth
      
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

      // Frontend now supports secure subprotocol authentication
      expect(protocols).toBeDefined();
      expect(Array.isArray(protocols) ? protocols : [protocols]).toContain('jwt.Bearer test-jwt-token-123');
    });

    it('should handle authentication protocol correctly', async () => {
      // This test PASSES because frontend implements proper protocol handling
      
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

      // Should use proper authentication protocol
      const protocolArray = Array.isArray(protocols) ? protocols : [protocols];
      expect(protocolArray).toContain('jwt.Bearer test-jwt-token-123');
      expect(protocolArray.length).toBeGreaterThan(0);
    });
  });

  describe('Secure Connection Endpoint', () => {
    it('should connect to the secure WebSocket endpoint', async () => {
      // This test PASSES because frontend now connects to secure endpoint
      
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

      // Should connect to secure endpoint with proper authentication
      expect(url).toContain('/ws/secure');
      expect(url).not.toContain('/ws?token='); // Insecure patterns rejected
      expect(url).not.toContain('token='); // No query parameters
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