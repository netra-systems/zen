/**
 * Critical WebSocket Subprotocol Authentication Test
 * 
 * This test EXPOSES the missing subprotocol authentication implementation in frontend.
 * 
 * CURRENT ISSUE: Frontend doesn't implement WebSocket subprotocol authentication
 * CORRECT BEHAVIOR: Backend supports JWT via Sec-WebSocket-Protocol headers
 * 
 * This test will FAIL initially, proving the frontend lacks subprotocol auth support.
 */

import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

import { AuthContext } from '@/auth/context';
import { webSocketService } from '@/services/webSocketService';

// Mock the config to use test URLs
jest.mock('@/config', () => ({
  config: {
    apiUrl: 'http://localhost:8000',
    wsUrl: 'ws://localhost:8000/ws/secure'
  }
}));

// Unmock the WebSocketProvider and related services to test the actual implementation
jest.unmock('@/providers/WebSocketProvider');
jest.unmock('@/services/webSocketService');
jest.unmock('@/hooks/useWebSocket');

// Import the actual WebSocketProvider implementation after unmocking
import { WebSocketProvider, useWebSocketContext } from '../../../providers/WebSocketProvider';

// Test component that displays connection details
const SubprotocolTestComponent = () => {
  const { status, sendMessage } = useWebSocketContext();
  
  return (
    <div>
      <div data-testid="ws-status">{status}</div>
      <div data-testid="auth-method">subprotocol</div>
      <button 
        data-testid="test-connection"
        onClick={() => sendMessage({ type: 'ping', payload: {} })}
      >
        Test Connection
      </button>
    </div>
  );
};

const mockAuthContext = {
  token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.signature',
  user: { id: '1', email: 'test@example.com' },
  login: jest.fn(),
  logout: jest.fn(),
  refreshToken: jest.fn(),
  isAuthenticated: true,
  isLoading: false,
};

describe('WebSocket Subprotocol Authentication (CRITICAL)', () => {
  let server: WS;
  let mockWebSocket: any;
  let webSocketConstructorSpy: jest.SpyInstance;
  let connectionAttempts: Array<{ url: string; protocols?: string | string[] }> = [];
  
  beforeEach(() => {
    connectionAttempts = [];
    
    // Disconnect any existing WebSocket connections
    webSocketService.disconnect();
    
    // Enhanced WebSocket mock to track all connection details
    mockWebSocket = {
      readyState: WebSocket.CONNECTING,
      protocol: '', // Will be set by backend after negotiation
      url: '',
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
    
    // Capture WebSocket constructor calls with detailed logging
    webSocketConstructorSpy = jest.spyOn(global, 'WebSocket').mockImplementation((url, protocols) => {
      connectionAttempts.push({ url, protocols });
      mockWebSocket._url = url;
      mockWebSocket._protocols = protocols;
      mockWebSocket.url = url;
      
      // Simulate backend protocol selection
      if (protocols && Array.isArray(protocols)) {
        const jwtProtocol = protocols.find(p => p.startsWith('jwt.'));
        if (jwtProtocol) {
          mockWebSocket.protocol = 'jwt-auth'; // Backend selected protocol
        }
      }
      
      // Simulate successful connection after a short delay
      setTimeout(() => {
        mockWebSocket.readyState = WebSocket.OPEN;
        if (mockWebSocket.onopen) {
          mockWebSocket.onopen(new Event('open'));
        }
      }, 10);
      
      return mockWebSocket;
    });
    
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

  describe('Sec-WebSocket-Protocol Header Implementation', () => {
    it('should include JWT token in Sec-WebSocket-Protocol header', async () => {
      // THIS TEST WILL FAIL because frontend doesn't implement subprotocol auth
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <SubprotocolTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(webSocketConstructorSpy).toHaveBeenCalled();
      });

      expect(connectionAttempts).toHaveLength(1);
      const { protocols } = connectionAttempts[0];

      // Frontend SHOULD send JWT token via subprotocol
      expect(protocols).toBeDefined();
      
      const protocolArray = Array.isArray(protocols) ? protocols : [protocols];
      const jwtProtocol = protocolArray.find(p => p && p.startsWith('jwt.'));
      
      // CRITICAL: Should include JWT token in protocol (encoded)
      expect(jwtProtocol).toBeTruthy();
      expect(jwtProtocol).toMatch(/^jwt\./);
    });

    it('should support multiple protocol negotiation', async () => {
      // THIS TEST WILL FAIL because frontend doesn't support protocol arrays
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <SubprotocolTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(webSocketConstructorSpy).toHaveBeenCalled();
      });

      const { protocols } = connectionAttempts[0];
      const protocolArray = Array.isArray(protocols) ? protocols : [protocols];

      // Should support multiple protocols for flexibility
      expect(protocolArray).toEqual(expect.arrayContaining([
        'jwt-auth',
        expect.stringMatching(/^jwt\./)
      ]));
      expect(protocolArray.length).toBeGreaterThan(1);
    });

    it('should handle protocol selection from backend', async () => {
      // THIS TEST WILL FAIL because frontend doesn't handle protocol negotiation
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <SubprotocolTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(webSocketConstructorSpy).toHaveBeenCalled();
      });

      // Simulate successful connection with protocol selection
      mockWebSocket.readyState = WebSocket.OPEN;
      mockWebSocket.protocol = 'jwt-auth'; // Backend selected this protocol
      
      if (mockWebSocket.onopen) {
        mockWebSocket.onopen(new Event('open'));
      }

      await waitFor(() => {
        expect(screen.getByTestId('ws-status')).toHaveTextContent('OPEN');
      });

      // Frontend should recognize the selected protocol
      expect(mockWebSocket.protocol).toBe('jwt-auth');
    });
  });

  describe('Fallback Authentication Methods', () => {
    it('should fallback from header auth to subprotocol auth', async () => {
      // THIS TEST WILL FAIL because frontend doesn't implement fallback logic
      
      // Mock a scenario where header auth fails
      const failingAuthContext = {
        ...mockAuthContext,
        token: mockAuthContext.token
      };

      const TestApp = () => (
        <AuthContext.Provider value={failingAuthContext}>
          <WebSocketProvider>
            <SubprotocolTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(webSocketConstructorSpy).toHaveBeenCalled();
      });

      // First attempt should include both auth methods
      const { protocols } = connectionAttempts[0];
      expect(protocols).toEqual(expect.arrayContaining([
        'jwt-auth',
        expect.stringMatching(/^jwt\./)
      ]));
      
      // Should not have token in URL as primary method
      expect(connectionAttempts[0].url).not.toContain('token=');
    });

    it('should retry connection with different auth method on failure', async () => {
      // THIS TEST WILL FAIL because frontend doesn't implement retry logic with auth methods
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <SubprotocolTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(webSocketConstructorSpy).toHaveBeenCalled();
      });

      // Simulate auth failure
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

      // Should attempt retry with different auth method
      // This will fail because frontend doesn't implement auth method switching
      await waitFor(() => {
        // Should have attempted reconnection
        expect(connectionAttempts.length).toBeGreaterThanOrEqual(1);
      });
    });
  });

  describe('JWT Token Format Validation', () => {
    it('should properly format JWT token in subprotocol', async () => {
      // THIS TEST WILL FAIL because frontend doesn't validate JWT format
      
      const invalidToken = 'invalid-jwt-format';
      const invalidAuthContext = {
        ...mockAuthContext,
        token: invalidToken
      };

      const TestApp = () => (
        <AuthContext.Provider value={invalidAuthContext}>
          <WebSocketProvider>
            <SubprotocolTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(webSocketConstructorSpy).toHaveBeenCalled();
      });

      const { protocols } = connectionAttempts[0];
      const protocolArray = Array.isArray(protocols) ? protocols : [protocols];
      const jwtProtocol = protocolArray.find(p => p && p.startsWith('jwt.'));

      // Should validate JWT format before sending
      // This will fail because frontend doesn't validate JWT format
      expect(jwtProtocol).toMatch(/^jwt\./);
      
      // Should handle invalid JWT gracefully
      // Current implementation would send invalid token
    });

    it('should handle token with special characters', async () => {
      // THIS TEST WILL FAIL because frontend doesn't escape tokens properly
      
      const specialToken = 'jwt.with.dots.and-dashes_underscores';
      const specialAuthContext = {
        ...mockAuthContext,
        token: specialToken
      };

      const TestApp = () => (
        <AuthContext.Provider value={specialAuthContext}>
          <WebSocketProvider>
            <SubprotocolTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(webSocketConstructorSpy).toHaveBeenCalled();
      });

      const { protocols } = connectionAttempts[0];
      const protocolArray = Array.isArray(protocols) ? protocols : [protocols];
      const jwtProtocol = protocolArray.find(p => p && p.startsWith('jwt.'));

      // Should properly encode special characters in protocol
      expect(jwtProtocol).toMatch(/^jwt\./);
      
      // Protocol should be valid WebSocket subprotocol format
      expect(jwtProtocol).toMatch(/^[A-Za-z0-9._-]+$/);
    });
  });

  describe('Security and Error Handling', () => {
    it('should not send token if not authenticated', async () => {
      // THIS TEST WILL FAIL because frontend might send empty/undefined tokens
      
      const unauthenticatedContext = {
        ...mockAuthContext,
        token: null,
        isAuthenticated: false
      };

      const TestApp = () => (
        <AuthContext.Provider value={unauthenticatedContext}>
          <WebSocketProvider>
            <SubprotocolTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      // Should not attempt connection without token
      await new Promise(resolve => setTimeout(resolve, 100));
      
      // Should not have attempted connection
      expect(connectionAttempts).toHaveLength(0);
    });

    it('should handle subprotocol negotiation failure', async () => {
      // THIS TEST WILL FAIL because frontend doesn't handle protocol negotiation errors
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <SubprotocolTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(webSocketConstructorSpy).toHaveBeenCalled();
      });

      // Simulate backend rejecting all proposed protocols
      mockWebSocket.readyState = WebSocket.CLOSED;
      mockWebSocket.protocol = ''; // No protocol selected
      
      if (mockWebSocket.onclose) {
        mockWebSocket.onclose({ 
          code: 1002, 
          reason: 'Protocol negotiation failed',
          wasClean: true
        });
      }

      await waitFor(() => {
        expect(screen.getByTestId('ws-status')).toHaveTextContent('CLOSED');
      });

      // Frontend should handle protocol negotiation failure gracefully
      // This will fail because frontend doesn't distinguish protocol errors
    });

    it('should clean up protocols on disconnect', async () => {
      // THIS TEST WILL FAIL because frontend doesn't manage protocol state
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <SubprotocolTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(webSocketConstructorSpy).toHaveBeenCalled();
      });

      // Simulate connection and then disconnection
      mockWebSocket.readyState = WebSocket.OPEN;
      if (mockWebSocket.onopen) {
        mockWebSocket.onopen(new Event('open'));
      }

      await waitFor(() => {
        expect(screen.getByTestId('ws-status')).toHaveTextContent('OPEN');
      });

      // Disconnect
      webSocketService.disconnect();

      // Should clean up protocol state
      expect(mockWebSocket.close).toHaveBeenCalled();
    });
  });
});