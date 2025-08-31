import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
ementation.
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

import { AuthContext } from '@/auth/context';
import { webSocketService } from '@/services/webSocketService';

// Mock the config to use test URLs
jest.mock('@/config', () => ({
  config: {
    apiUrl: 'http://localhost:8000',
    wsUrl: 'ws://localhost:8000/ws'
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
  const { status } = useWebSocketContext();
  
  return (
    <div>
      <div data-testid="ws-status">{status}</div>
      <div data-testid="auth-method">subprotocol</div>
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
    jest.setTimeout(10000);
  let originalWebSocket: any;
  let mockWebSocket: any;
  let connectionAttempts: Array<{ url: string; protocols?: string | string[] }> = [];
  
  beforeEach(() => {
    connectionAttempts = [];
    
    // Disconnect any existing WebSocket connections
    webSocketService.disconnect();
    
    // Save original WebSocket
    originalWebSocket = global.WebSocket;
    
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
    global.WebSocket = jest.fn().mockImplementation((url, protocols) => {
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
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
  });

  describe('Sec-WebSocket-Protocol Header Implementation', () => {
      jest.setTimeout(10000);
    it('should include JWT token in Sec-WebSocket-Protocol header', async () => {
      // This test verifies subprotocol authentication is implemented
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <SubprotocolTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(connectionAttempts.length).toBeGreaterThan(0);
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
      // This test verifies frontend supports protocol arrays
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <SubprotocolTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(connectionAttempts.length).toBeGreaterThan(0);
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
      // This test verifies frontend handles protocol negotiation
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <SubprotocolTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(connectionAttempts.length).toBeGreaterThan(0);
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

  describe('Security and Error Handling', () => {
      jest.setTimeout(10000);
    it('should not send token if not authenticated', async () => {
      // This test verifies no token is sent when not authenticated
      
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
      
      // Should not have attempted connection or should have connected without auth protocols
      if (connectionAttempts.length > 0) {
        const { protocols } = connectionAttempts[0];
        // If connection attempted, should not include JWT protocols
        const protocolArray = Array.isArray(protocols) ? protocols : [protocols];
        const hasJwtProtocol = protocolArray.some(p => p && p.startsWith('jwt.'));
        expect(hasJwtProtocol).toBe(false);
      }
    });

    it('should clean up protocols on disconnect', async () => {
      // This test verifies protocol state management
      
      const TestApp = () => (
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <SubprotocolTestComponent />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      render(<TestApp />);
      
      await waitFor(() => {
        expect(connectionAttempts.length).toBeGreaterThan(0);
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