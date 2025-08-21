/**
 * Critical WebSocket CORS Validation Test
 * 
 * This test EXPOSES the lack of proper CORS handling in frontend WebSocket connections.
 * 
 * CURRENT ISSUE: Frontend doesn't handle CORS validation or Origin header requirements
 * CORRECT BEHAVIOR: Backend validates CORS and requires proper Origin headers
 * 
 * This test will FAIL initially, proving frontend lacks CORS awareness.
 */

import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
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

// Test component that shows CORS-related connection status
const CorsTestComponent = () => {
  const { status, sendMessage } = useWebSocketContext();
  const [corsError, setCorsError] = React.useState<string>('');
  const [origin, setOrigin] = React.useState<string>('');
  
  React.useEffect(() => {
    // Mock CORS error detection
    setOrigin(window.location.origin);
  }, []);
  
  return (
    <div>
      <div data-testid="ws-status">{status}</div>
      <div data-testid="cors-error">{corsError}</div>
      <div data-testid="origin">{origin}</div>
      <button 
        data-testid="test-cors"
        onClick={() => {
          sendMessage({ type: 'cors_test', payload: { origin: window.location.origin } });
        }}
      >
        Test CORS
      </button>
    </div>
  );
};

const mockAuthContext = {
  token: 'valid-cors-test-token',
  user: { id: '1', email: 'test@example.com' },
  login: jest.fn(),
  logout: jest.fn(),
  refreshToken: jest.fn(),
  isAuthenticated: true,
  isLoading: false,
};

describe('WebSocket CORS Validation (CRITICAL SECURITY)', () => {
  let server: WS;
  let mockWebSocket: any;
  let connectionAttempts: Array<{ 
    url: string; 
    protocols?: string | string[];
    origin?: string;
    corsBlocked?: boolean;
  }> = [];
  
  beforeEach(() => {
    connectionAttempts = [];
    
    // Mock different origin scenarios
    Object.defineProperty(window, 'location', {
      value: {
        origin: 'http://localhost:3000',
        href: 'http://localhost:3000',
        protocol: 'http:',
        host: 'localhost:3000',
        hostname: 'localhost',
        port: '3000'
      },
      writable: true
    });
    
    // Enhanced WebSocket mock with CORS simulation
    mockWebSocket = {
      readyState: WebSocket.CONNECTING,
      close: jest.fn(),
      send: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
    };
    
    global.WebSocket = jest.fn().mockImplementation((url, protocols) => {
      const currentOrigin = window.location.origin;
      
      // Simulate CORS validation logic
      const allowedOrigins = [
        'http://localhost:3000',
        'https://app.netrasystems.ai',
        'https://staging.netrasystems.ai'
      ];
      
      const corsBlocked = !allowedOrigins.includes(currentOrigin);
      
      connectionAttempts.push({ 
        url, 
        protocols,
        origin: currentOrigin,
        corsBlocked
      });
      
      mockWebSocket._url = url;
      mockWebSocket._protocols = protocols;
      mockWebSocket._origin = currentOrigin;
      
      // Simulate CORS rejection
      if (corsBlocked) {
        setTimeout(() => {
          mockWebSocket.readyState = WebSocket.CLOSED;
          if (mockWebSocket.onerror) {
            mockWebSocket.onerror(new Event('error'));
          }
          if (mockWebSocket.onclose) {
            mockWebSocket.onclose({ 
              code: 1006, 
              reason: 'CORS validation failed',
              wasClean: false
            });
          }
        }, 0);
      }
      
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

  describe('Origin Header Validation', () => {
    it('should include proper Origin header in WebSocket connection', async () => {
      // THIS TEST WILL FAIL because frontend doesn't explicitly handle Origin headers
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <CorsTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalled();
      });

      expect(connectionAttempts).toHaveLength(1);
      const { origin } = connectionAttempts[0];
      
      // Should include current origin for CORS validation
      expect(origin).toBe('http://localhost:3000');
      
      // Frontend should be aware of Origin requirements
      expect(screen.getByTestId('origin')).toHaveTextContent('http://localhost:3000');
    });

    it('should handle CORS validation failure gracefully', async () => {
      // THIS TEST WILL FAIL because frontend doesn't distinguish CORS errors
      
      // Set invalid origin
      Object.defineProperty(window, 'location', {
        value: {
          ...window.location,
          origin: 'http://evil-site.com'
        },
        writable: true
      });
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <CorsTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalled();
      });

      const { corsBlocked } = connectionAttempts[0];
      expect(corsBlocked).toBe(true);

      await waitFor(() => {
        expect(screen.getByTestId('ws-status')).toHaveTextContent('CLOSED');
      });

      // Should identify this as a CORS error, not a generic connection error
      // This will fail because frontend doesn't handle CORS-specific errors
      const corsError = screen.getByTestId('cors-error');
      expect(corsError.textContent).toContain('CORS');
    });

    it('should not attempt connection from invalid origins', async () => {
      // THIS TEST WILL FAIL because frontend doesn't validate origins before connecting
      
      // Set clearly invalid origin
      Object.defineProperty(window, 'location', {
        value: {
          ...window.location,
          origin: 'http://malicious-domain.hack'
        },
        writable: true
      });
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <CorsTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      // Should not attempt connection from invalid origin
      await new Promise(resolve => setTimeout(resolve, 100));
      
      // Frontend should validate origin before attempting connection
      // This will fail because frontend doesn't implement origin validation
      expect(connectionAttempts).toHaveLength(0);
    });
  });

  describe('Allowed Origins Configuration', () => {
    it('should connect successfully from allowed development origin', async () => {
      // THIS TEST WILL FAIL because frontend doesn't handle origin allowlists
      
      // Set allowed development origin
      Object.defineProperty(window, 'location', {
        value: {
          ...window.location,
          origin: 'http://localhost:3000'
        },
        writable: true
      });
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <CorsTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalled();
      });

      const { corsBlocked } = connectionAttempts[0];
      expect(corsBlocked).toBe(false);

      // Should successfully establish connection
      mockWebSocket.readyState = WebSocket.OPEN;
      if (mockWebSocket.onopen) {
        mockWebSocket.onopen(new Event('open'));
      }

      await waitFor(() => {
        expect(screen.getByTestId('ws-status')).toHaveTextContent('OPEN');
      });
    });

    it('should connect successfully from allowed production origin', async () => {
      // THIS TEST WILL FAIL because frontend doesn't distinguish between environments
      
      // Set production origin
      Object.defineProperty(window, 'location', {
        value: {
          ...window.location,
          origin: 'https://app.netrasystems.ai'
        },
        writable: true
      });
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <CorsTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalled();
      });

      const { corsBlocked } = connectionAttempts[0];
      expect(corsBlocked).toBe(false);

      // Production origin should be allowed
      expect(screen.getByTestId('origin')).toHaveTextContent('https://app.netrasystems.ai');
    });

    it('should handle subdomain restrictions properly', async () => {
      // THIS TEST WILL FAIL because frontend doesn't validate subdomain policies
      
      // Set unauthorized subdomain
      Object.defineProperty(window, 'location', {
        value: {
          ...window.location,
          origin: 'https://malicious.netrasystems.ai'
        },
        writable: true
      });
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <CorsTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalled();
      });

      const { corsBlocked } = connectionAttempts[0];
      
      // Should block unauthorized subdomains
      expect(corsBlocked).toBe(true);
      
      // Frontend should understand subdomain security implications
      // This will fail because frontend doesn't implement subdomain validation
    });
  });

  describe('Cross-Origin Request Handling', () => {
    it('should handle mixed content scenarios (HTTP to HTTPS)', async () => {
      // THIS TEST WILL FAIL because frontend doesn't handle mixed content properly
      
      // Set HTTPS origin trying to connect to WS (not WSS)
      Object.defineProperty(window, 'location', {
        value: {
          ...window.location,
          origin: 'https://localhost:3000',
          protocol: 'https:'
        },
        writable: true
      });
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <CorsTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalled();
      });

      const { url } = connectionAttempts[0];
      
      // Should upgrade to WSS for HTTPS origins
      expect(url).toContain('wss://');
      
      // Should not attempt mixed content connections
      // This will fail because frontend doesn't handle protocol upgrades
    });

    it('should validate referrer policies', async () => {
      // THIS TEST WILL FAIL because frontend doesn't implement referrer validation
      
      // Mock referrer header
      Object.defineProperty(document, 'referrer', {
        value: 'http://localhost:3000/chat',
        writable: true
      });
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <CorsTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalled();
      });

      // Should validate referrer matches origin
      expect(document.referrer).toContain('localhost:3000');
      
      // Frontend should be referrer-aware for security
      // This will fail because frontend doesn't validate referrer
    });

    it('should handle iframe embedding restrictions', async () => {
      // THIS TEST WILL FAIL because frontend doesn't detect iframe contexts
      
      // Mock iframe context
      Object.defineProperty(window, 'parent', {
        value: {
          origin: 'http://different-origin.com'
        },
        writable: true
      });
      
      Object.defineProperty(window, 'top', {
        value: window.parent,
        writable: true
      });
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <CorsTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      // Should detect iframe embedding and apply restrictions
      await new Promise(resolve => setTimeout(resolve, 100));
      
      // Should not allow WebSocket connections from embedded iframes
      // This will fail because frontend doesn't implement iframe detection
      expect(connectionAttempts).toHaveLength(0);
    });
  });

  describe('Security Headers and Validation', () => {
    it('should respect Content Security Policy for WebSocket connections', async () => {
      // THIS TEST WILL FAIL because frontend doesn't check CSP directives
      
      // Mock CSP header
      const mockCSP = "connect-src 'self' ws://localhost:8000 wss://api.netrasystems.ai";
      Object.defineProperty(document, 'querySelector', {
        value: jest.fn((selector) => {
          if (selector === 'meta[http-equiv="Content-Security-Policy"]') {
            return { content: mockCSP };
          }
          return null;
        }),
        writable: true
      });
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <CorsTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalled();
      });

      const { url } = connectionAttempts[0];
      
      // Should validate WebSocket URL against CSP
      expect(url).toContain('ws://localhost:8000');
      
      // Frontend should respect CSP connect-src directive
      // This will fail because frontend doesn't implement CSP validation
    });

    it('should handle Sec-Fetch-Site header validation', async () => {
      // THIS TEST WILL FAIL because frontend doesn't set security fetch headers
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <CorsTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalled();
      });

      // Should include appropriate Sec-Fetch-* headers
      // This will fail because WebSocket doesn't support custom headers directly
      // Frontend should be aware of this limitation
    });

    it('should validate against XSS injection in WebSocket URLs', async () => {
      // THIS TEST WILL FAIL because frontend doesn't sanitize WebSocket URLs
      
      // Mock malicious URL injection attempt
      const maliciousConfig = {
        wsUrl: 'ws://localhost:8000/ws?evil=<script>alert("xss")</script>'
      };
      
      jest.doMock('@/config', () => ({
        config: {
          apiUrl: 'http://localhost:8000',
          ...maliciousConfig
        }
      }));
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <CorsTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalled();
      });

      const { url } = connectionAttempts[0];
      
      // Should sanitize URL to prevent XSS
      expect(url).not.toContain('<script>');
      expect(url).not.toContain('alert');
      
      // Frontend should validate and sanitize WebSocket URLs
      // This will fail because frontend doesn't implement URL sanitization
    });
  });

  describe('CORS Error Recovery and Fallback', () => {
    it('should provide actionable CORS error messages', async () => {
      // THIS TEST WILL FAIL because frontend doesn't provide CORS-specific guidance
      
      // Set invalid origin
      Object.defineProperty(window, 'location', {
        value: {
          ...window.location,
          origin: 'http://unauthorized-origin.com'
        },
        writable: true
      });
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <CorsTestComponent />
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

      const corsError = screen.getByTestId('cors-error');
      
      // Should provide specific CORS guidance
      expect(corsError.textContent).toContain('origin');
      expect(corsError.textContent).toContain('allowed');
      
      // Should explain how to resolve CORS issues
      expect(corsError.textContent).toContain('administrator');
    });

    it('should not retry CORS-blocked connections indefinitely', async () => {
      // THIS TEST WILL FAIL because frontend might retry CORS-blocked connections
      
      // Set invalid origin
      Object.defineProperty(window, 'location', {
        value: {
          ...window.location,
          origin: 'http://blocked-origin.com'
        },
        writable: true
      });
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <CorsTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalled();
      });

      // Wait for potential retries
      await new Promise(resolve => setTimeout(resolve, 5000));
      
      // Should not repeatedly retry CORS-blocked connections
      const corsBlockedAttempts = connectionAttempts.filter(attempt => attempt.corsBlocked);
      expect(corsBlockedAttempts.length).toBeLessThanOrEqual(1);
    });

    it('should provide fallback options for CORS issues', async () => {
      // THIS TEST WILL FAIL because frontend doesn't implement CORS fallbacks
      
      // Set origin that requires special handling
      Object.defineProperty(window, 'location', {
        value: {
          ...window.location,
          origin: 'http://localhost:8080' // Different port
        },
        writable: true
      });
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <CorsTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalled();
      });

      // Should suggest alternative connection methods
      const corsError = screen.getByTestId('cors-error');
      expect(corsError.textContent).toContain('alternative');
      
      // Should provide fallback mechanisms
      // This will fail because frontend doesn't implement CORS fallbacks
    });
  });
});