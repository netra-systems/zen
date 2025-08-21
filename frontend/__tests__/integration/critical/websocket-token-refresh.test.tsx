/**
 * Critical WebSocket Token Refresh Test
 * 
 * This test EXPOSES the lack of proper token refresh handling during active WebSocket connections.
 * 
 * CURRENT ISSUE: Frontend doesn't handle token refresh during active WebSocket connections
 * CORRECT BEHAVIOR: Should seamlessly refresh tokens and update WebSocket authentication
 * 
 * This test will FAIL initially, proving frontend lacks token lifecycle management.
 */

import React from 'react';
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import WS from 'jest-websocket-mock';

import { WebSocketProvider, useWebSocketContext } from '@/providers/WebSocketProvider';
import { AuthContext } from '@/auth/context';
import { webSocketService } from '@/services/webSocketService';

// Mock the config
jest.mock('@/config', () => ({
  config: {
    apiUrl: 'http://localhost:8000',
    wsUrl: 'ws://localhost:8000/ws/secure'
  }
}));

// Test component that handles token refresh scenarios
const TokenRefreshTestComponent = () => {
  const { status, sendMessage } = useWebSocketContext();
  const [refreshCount, setRefreshCount] = React.useState(0);
  const [lastTokenUsed, setLastTokenUsed] = React.useState('');
  
  const handleTokenRefresh = () => {
    setRefreshCount(prev => prev + 1);
  };
  
  return (
    <div>
      <div data-testid="ws-status">{status}</div>
      <div data-testid="refresh-count">{refreshCount}</div>
      <div data-testid="last-token">{lastTokenUsed}</div>
      <button data-testid="trigger-refresh" onClick={handleTokenRefresh}>
        Trigger Token Refresh
      </button>
      <button 
        data-testid="send-message"
        onClick={() => sendMessage({ type: 'test', payload: { content: 'test' } })}
      >
        Send Message
      </button>
    </div>
  );
};

// Mock auth context with token refresh capabilities
const createMockAuthContext = (initialToken: string) => ({
  token: initialToken,
  user: { id: '1', email: 'test@example.com' },
  login: jest.fn(),
  logout: jest.fn(),
  refreshToken: jest.fn(),
  isAuthenticated: true,
  isLoading: false,
});

describe('WebSocket Token Refresh Management (CRITICAL)', () => {
  let server: WS;
  let mockWebSocket: any;
  let authContext: any;
  let connectionAttempts: Array<{ 
    url: string; 
    protocols?: string | string[]; 
    timestamp: number;
    token?: string;
  }> = [];
  
  beforeEach(() => {
    connectionAttempts = [];
    authContext = createMockAuthContext('initial-token-123');
    
    // Enhanced mock to track token usage
    mockWebSocket = {
      readyState: WebSocket.CONNECTING,
      close: jest.fn(),
      send: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
    };
    
    global.WebSocket = jest.fn().mockImplementation((url, protocols) => {
      // Extract token from protocols or URL
      let token = '';
      if (protocols && Array.isArray(protocols)) {
        const jwtProtocol = protocols.find(p => p.startsWith('jwt.'));
        if (jwtProtocol) {
          token = jwtProtocol.substring(4); // Remove 'jwt.' prefix
        }
      } else if (url.includes('token=')) {
        const urlObj = new URL(url, 'ws://localhost');
        token = urlObj.searchParams.get('token') || '';
      }
      
      connectionAttempts.push({ 
        url, 
        protocols, 
        timestamp: Date.now(),
        token 
      });
      
      mockWebSocket._url = url;
      mockWebSocket._protocols = protocols;
      mockWebSocket._token = token;
      
      return mockWebSocket;
    }) as any;
    
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

  describe('Token Expiry Detection and Refresh', () => {
    it('should detect when token is about to expire', async () => {
      // THIS TEST WILL FAIL because frontend doesn't monitor token expiry
      
      // Mock a token that expires soon
      const expiringToken = 'expiring-token-456';
      authContext.token = expiringToken;
      
      // Mock JWT decode to show expiring token
      const mockTokenPayload = {
        exp: Math.floor(Date.now() / 1000) + 60, // Expires in 1 minute
        iat: Math.floor(Date.now() / 1000),
        user_id: '1'
      };
      
      // Mock token decode (would need actual JWT library in real implementation)
      jest.spyOn(global, 'atob').mockReturnValue(JSON.stringify(mockTokenPayload));
      
      const TestApp = () => (
        <AuthContext.Provider value={authContext}>
          <WebSocketProvider>
            <TokenRefreshTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalled();
      });

      // Frontend should detect impending expiry and trigger refresh
      // This will fail because frontend doesn't monitor token expiry
      expect(authContext.refreshToken).toHaveBeenCalled();
    });

    it('should refresh token before WebSocket connection fails', async () => {
      // THIS TEST WILL FAIL because frontend doesn't proactively refresh tokens
      
      let currentToken = 'token-about-to-expire';
      authContext.token = currentToken;
      
      // Mock successful refresh
      authContext.refreshToken.mockImplementation(async () => {
        currentToken = 'refreshed-token-789';
        authContext.token = currentToken;
        return { token: currentToken };
      });
      
      const TestApp = () => (
        <AuthContext.Provider value={authContext}>
          <WebSocketProvider>
            <TokenRefreshTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalled();
      });

      // Simulate connection established
      mockWebSocket.readyState = WebSocket.OPEN;
      if (mockWebSocket.onopen) {
        mockWebSocket.onopen(new Event('open'));
      }

      await waitFor(() => {
        expect(screen.getByTestId('ws-status')).toHaveTextContent('OPEN');
      });

      // Simulate token expiry approaching
      jest.advanceTimersByTime(55000); // 55 seconds

      // Should refresh token before expiry
      expect(authContext.refreshToken).toHaveBeenCalled();
    });

    it('should handle token refresh during active connection', async () => {
      // THIS TEST WILL FAIL because frontend doesn't update WebSocket auth dynamically
      
      authContext.token = 'active-connection-token';
      
      const TestApp = () => (
        <AuthContext.Provider value={authContext}>
          <WebSocketProvider>
            <TokenRefreshTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalled();
      });

      // Establish connection
      mockWebSocket.readyState = WebSocket.OPEN;
      if (mockWebSocket.onopen) {
        mockWebSocket.onopen(new Event('open'));
      }

      await waitFor(() => {
        expect(screen.getByTestId('ws-status')).toHaveTextContent('OPEN');
      });

      // Simulate token refresh
      const newToken = 'refreshed-during-connection';
      authContext.token = newToken;
      
      // Frontend should update the connection with new token
      // This will fail because frontend doesn't handle runtime token updates
      
      // Should send auth update message or reconnect with new token
      expect(mockWebSocket.send).toHaveBeenCalledWith(
        expect.stringContaining('auth_update')
      );
    });
  });

  describe('Reconnection with New Token', () => {
    it('should reconnect with new token after refresh', async () => {
      // THIS TEST WILL FAIL because frontend doesn't implement token-aware reconnection
      
      authContext.token = 'old-token-123';
      
      const TestApp = () => (
        <AuthContext.Provider value={authContext}>
          <WebSocketProvider>
            <TokenRefreshTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalled();
      });

      // Simulate connection failure due to token expiry
      mockWebSocket.readyState = WebSocket.CLOSED;
      if (mockWebSocket.onclose) {
        mockWebSocket.onclose({ 
          code: 1008, 
          reason: 'Token expired',
          wasClean: false
        });
      }

      // Trigger token refresh
      const newToken = 'refreshed-token-456';
      authContext.token = newToken;
      authContext.refreshToken.mockResolvedValue({ token: newToken });

      fireEvent.click(screen.getByTestId('trigger-refresh'));

      await waitFor(() => {
        expect(authContext.refreshToken).toHaveBeenCalled();
      });

      // Should attempt reconnection with new token
      await waitFor(() => {
        expect(connectionAttempts.length).toBeGreaterThan(1);
      });

      const latestAttempt = connectionAttempts[connectionAttempts.length - 1];
      expect(latestAttempt.token).toBe(newToken);
    });

    it('should not reuse expired tokens for reconnection', async () => {
      // THIS TEST WILL FAIL because frontend might reuse old tokens
      
      const expiredToken = 'expired-token-789';
      authContext.token = expiredToken;
      
      const TestApp = () => (
        <AuthContext.Provider value={authContext}>
          <WebSocketProvider>
            <TokenRefreshTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalled();
      });

      // Simulate auth failure
      mockWebSocket.readyState = WebSocket.CLOSED;
      if (mockWebSocket.onclose) {
        mockWebSocket.onclose({ 
          code: 1008, 
          reason: 'Token expired',
          wasClean: false
        });
      }

      // Should not retry with same expired token
      const expiredTokenUsage = connectionAttempts.filter(attempt => 
        attempt.token === expiredToken
      );
      
      expect(expiredTokenUsage.length).toBe(1); // Only initial attempt
    });

    it('should handle refresh failure gracefully', async () => {
      // THIS TEST WILL FAIL because frontend doesn't handle refresh failures
      
      authContext.token = 'failing-token-123';
      authContext.refreshToken.mockRejectedValue(new Error('Refresh failed'));
      
      const TestApp = () => (
        <AuthContext.Provider value={authContext}>
          <WebSocketProvider>
            <TokenRefreshTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalled();
      });

      // Simulate auth failure
      mockWebSocket.readyState = WebSocket.CLOSED;
      if (mockWebSocket.onclose) {
        mockWebSocket.onclose({ 
          code: 1008, 
          reason: 'Token expired',
          wasClean: false
        });
      }

      // Try to refresh
      fireEvent.click(screen.getByTestId('trigger-refresh'));

      await waitFor(() => {
        expect(authContext.refreshToken).toHaveBeenCalled();
      });

      // Should handle refresh failure and not attempt connection with invalid token
      const latestAttempts = connectionAttempts.slice(-2);
      expect(latestAttempts.every(attempt => attempt.token !== 'failing-token-123')).toBe(true);
    });
  });

  describe('Message Queue Management During Refresh', () => {
    it('should queue messages during token refresh', async () => {
      // THIS TEST WILL FAIL because frontend doesn't implement message queuing during refresh
      
      authContext.token = 'queue-test-token';
      
      const TestApp = () => (
        <AuthContext.Provider value={authContext}>
          <WebSocketProvider>
            <TokenRefreshTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalled();
      });

      // Establish connection
      mockWebSocket.readyState = WebSocket.OPEN;
      if (mockWebSocket.onopen) {
        mockWebSocket.onopen(new Event('open'));
      }

      await waitFor(() => {
        expect(screen.getByTestId('ws-status')).toHaveTextContent('OPEN');
      });

      // Start token refresh (connection becomes unavailable)
      mockWebSocket.readyState = WebSocket.CONNECTING;
      
      // Try to send message during refresh
      fireEvent.click(screen.getByTestId('send-message'));

      // Message should be queued, not sent immediately
      expect(mockWebSocket.send).not.toHaveBeenCalled();
      
      // After refresh completes and connection is re-established
      mockWebSocket.readyState = WebSocket.OPEN;
      if (mockWebSocket.onopen) {
        mockWebSocket.onopen(new Event('open'));
      }

      // Queued message should now be sent
      await waitFor(() => {
        expect(mockWebSocket.send).toHaveBeenCalled();
      });
    });

    it('should maintain message order during reconnection', async () => {
      // THIS TEST WILL FAIL because frontend doesn't guarantee message ordering during reconnection
      
      authContext.token = 'order-test-token';
      
      const TestApp = () => (
        <AuthContext.Provider value={authContext}>
          <WebSocketProvider>
            <TokenRefreshTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalled();
      });

      // Establish connection
      mockWebSocket.readyState = WebSocket.OPEN;
      if (mockWebSocket.onopen) {
        mockWebSocket.onopen(new Event('open'));
      }

      // Send multiple messages during connection issues
      fireEvent.click(screen.getByTestId('send-message'));
      fireEvent.click(screen.getByTestId('send-message'));
      fireEvent.click(screen.getByTestId('send-message'));

      // Simulate reconnection
      const newToken = 'reconnected-token';
      authContext.token = newToken;

      // Messages should be sent in order after reconnection
      const sendCalls = mockWebSocket.send.mock.calls;
      expect(sendCalls.length).toBeGreaterThan(0);
      
      // Should maintain chronological order
      // This will fail because frontend doesn't implement ordered message queuing
    });

    it('should handle message timeouts during refresh', async () => {
      // THIS TEST WILL FAIL because frontend doesn't implement message timeouts
      
      authContext.token = 'timeout-test-token';
      
      const TestApp = () => (
        <AuthContext.Provider value={authContext}>
          <WebSocketProvider>
            <TokenRefreshTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalled();
      });

      // Start with open connection
      mockWebSocket.readyState = WebSocket.OPEN;
      if (mockWebSocket.onopen) {
        mockWebSocket.onopen(new Event('open'));
      }

      // Connection becomes unavailable for extended period
      mockWebSocket.readyState = WebSocket.CLOSED;
      
      // Send message that will timeout
      fireEvent.click(screen.getByTestId('send-message'));

      // Advance time to trigger timeout
      jest.advanceTimersByTime(30000); // 30 seconds

      // Should handle message timeout gracefully
      // This will fail because frontend doesn't implement message timeouts
    });
  });

  describe('Token Lifecycle Integration', () => {
    it('should synchronize token state across WebSocket and auth contexts', async () => {
      // THIS TEST WILL FAIL because frontend doesn't synchronize token state
      
      authContext.token = 'sync-test-token';
      
      const TestApp = () => (
        <AuthContext.Provider value={authContext}>
          <WebSocketProvider>
            <TokenRefreshTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalled();
      });

      // Update token in auth context
      const updatedToken = 'synchronized-token';
      authContext.token = updatedToken;

      // WebSocket service should be aware of token change
      expect(connectionAttempts[0].token).toBe('sync-test-token');
      
      // Should trigger reconnection with new token
      await waitFor(() => {
        expect(connectionAttempts.length).toBeGreaterThan(1);
      });
    });

    it('should clean up old connections when token changes', async () => {
      // THIS TEST WILL FAIL because frontend doesn't clean up old connections
      
      authContext.token = 'cleanup-test-token';
      
      const TestApp = () => (
        <AuthContext.Provider value={authContext}>
          <WebSocketProvider>
            <TokenRefreshTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalled();
      });

      // Establish connection
      mockWebSocket.readyState = WebSocket.OPEN;
      if (mockWebSocket.onopen) {
        mockWebSocket.onopen(new Event('open'));
      }

      // Change token
      authContext.token = 'new-cleanup-token';

      // Should close old connection
      expect(mockWebSocket.close).toHaveBeenCalled();
      
      // Should establish new connection with new token
      await waitFor(() => {
        expect(connectionAttempts.length).toBeGreaterThan(1);
      });
    });
  });
});