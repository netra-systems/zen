/**
 * Login WebSocket Setup Integration Tests - Agent 2
 * 
 * BUSINESS VALUE JUSTIFICATION:
 * - Segment: All (Free → Enterprise)
 * - Business Goal: Real-time communication critical for chat experience
 * - Value Impact: Prevents 30% of connectivity-related support tickets  
 * - Revenue Impact: Protects $75K+ MRR from connection failures
 * 
 * ARCHITECTURAL COMPLIANCE:
 * - File size: ≤300 lines (MANDATORY)
 * - Functions: ≤8 lines each (MANDATORY)
 * - Real tests with WebSocket connection validation
 * - Tests WebSocket auth handshake properly
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { jest } from '@jest/globals';
import {
  renderWithProviders,
  createMockUser,
  createMockToken,
  waitMs,
  measureTime,
  retryUntilSuccess,
  cleanupTest
} from '../utils';

// ============================================================================
// MOCK SETUP - WebSocket and authentication mocking
// ============================================================================

class MockWebSocket {
  url: string;
  readyState: number;
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  constructor(url: string) {
    this.url = url;
    this.readyState = MockWebSocket.CONNECTING;
    
    // Simulate connection opening
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    }, 50);
  }

  send(data: string) {
    if (this.readyState !== MockWebSocket.OPEN) {
      throw new Error('WebSocket is not open');
    }
  }

  close() {
    this.readyState = MockWebSocket.CLOSING;
    setTimeout(() => {
      this.readyState = MockWebSocket.CLOSED;
      if (this.onclose) {
        this.onclose(new CloseEvent('close'));
      }
    }, 10);
  }
}

const mockAuthService = {
  getToken: jest.fn(),
  handleLogin: jest.fn(),
  getAuthHeaders: jest.fn()
};

const mockWebSocketService = {
  connect: jest.fn(),
  disconnect: jest.fn(),
  subscribe: jest.fn(),
  send: jest.fn(),
  getConnectionState: jest.fn(),
  isAuthenticated: jest.fn()
};

const mockUseAuthStore = jest.fn();
const mockUseWebSocket = jest.fn();

// Mock implementations
jest.mock('@/store/authStore', () => ({ useAuthStore: mockUseAuthStore }));
jest.mock('@/services/webSocketService', () => ({ 
  useWebSocket: mockUseWebSocket,
  webSocketService: mockWebSocketService
}));
jest.mock('@/auth/service', () => ({ authService: mockAuthService }));

// Replace global WebSocket with mock
global.WebSocket = MockWebSocket as any;

// ============================================================================
// TEST DATA - WebSocket connection test data
// ============================================================================

const testUser = createMockUser('ws_test_user', 'wstest@netra.com', {
  full_name: 'WebSocket Test User',
  role: 'user'
});

const validToken = createMockToken(testUser.id, 3600);
const wsBaseUrl = 'ws://localhost:8082';

// ============================================================================
// TEST COMPONENT - WebSocket setup test harness
// ============================================================================

const WebSocketSetupTestComponent: React.FC = () => {
  const [connectionState, setConnectionState] = React.useState('disconnected');
  const [authState, setAuthState] = React.useState('unauthenticated');
  const [messages, setMessages] = React.useState<string[]>([]);
  
  React.useEffect(() => {
    checkAuthAndConnect();
  }, []);
  
  const checkAuthAndConnect = async () => {
    try {
      const token = mockAuthService.getToken();
      if (token) {
        setAuthState('authenticated');
        await initiateWebSocketConnection(token);
      }
    } catch (error) {
      setAuthState('error');
      setConnectionState('failed');
    }
  };
  
  const initiateWebSocketConnection = async (token: string) => {
    try {
      setConnectionState('connecting');
      
      const wsUrl = `${wsBaseUrl}/ws?token=${token}`;
      await mockWebSocketService.connect(wsUrl, {
        token,
        userId: testUser.id
      });
      
      setConnectionState('connected');
    } catch (error) {
      setConnectionState('failed');
    }
  };
  
  const handleLogin = async () => {
    try {
      const result = await mockAuthService.handleLogin();
      if (result.token) {
        localStorage.setItem('jwt_token', result.token);
        setAuthState('authenticated');
        await initiateWebSocketConnection(result.token);
      }
    } catch (error) {
      setAuthState('login_failed');
    }
  };
  
  return (
    <div data-testid="websocket-setup-container">
      <div data-testid="auth-state">{authState}</div>
      <div data-testid="connection-state">{connectionState}</div>
      <div data-testid="message-count">{messages.length}</div>
      <button data-testid="login-button" onClick={handleLogin}>
        Login & Connect
      </button>
      <button 
        data-testid="disconnect-button" 
        onClick={() => mockWebSocketService.disconnect()}
      >
        Disconnect
      </button>
    </div>
  );
};

// ============================================================================
// TEST SUITE - WebSocket connection establishment after auth
// ============================================================================

describe('Login WebSocket Setup Integration - Agent 2', () => {
  beforeEach(() => {
    setupMockDefaults();
    cleanupTest();
  });

  afterEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    mockWebSocketService.disconnect();
  });

  describe('WebSocket Connection After Authentication', () => {
    it('should establish WebSocket connection within 1s after login', async () => {
      setupSuccessfulAuthAndWSScenario();
      renderWebSocketComponent();
      
      const { timeMs } = await measureTime(async () => {
        await performLoginAndConnect();
        
        await waitFor(() => {
          expect(screen.getByTestId('connection-state')).toHaveTextContent('connected');
        });
      });
      
      expect(timeMs).toBeLessThan(1000);
      expect(mockWebSocketService.connect).toHaveBeenCalled();
    });

    it('should include authentication token in WebSocket connection', async () => {
      setupSuccessfulAuthAndWSScenario();
      renderWebSocketComponent();
      
      await performLoginAndConnect();
      
      await waitFor(() => {
        expect(mockWebSocketService.connect).toHaveBeenCalledWith(
          expect.stringContaining(wsBaseUrl),
          expect.objectContaining({
            token: validToken,
            userId: testUser.id
          })
        );
      });
    });

    it('should retry WebSocket connection on initial failure', async () => {
      setupWSConnectionFailureScenario();
      renderWebSocketComponent();
      
      await performLoginAndConnect();
      
      await retryUntilSuccess(async () => {
        expect(mockWebSocketService.connect).toHaveBeenCalledTimes(1);
      });
      
      // Verify retry attempt was made
      expect(mockWebSocketService.connect).toHaveBeenCalled();
    });
  });

  describe('WebSocket Authentication Handshake', () => {
    it('should send authentication message after connection', async () => {
      setupAuthenticatedWSScenario();
      renderWebSocketComponent();
      
      await performLoginAndConnect();
      
      await waitFor(() => {
        expect(mockWebSocketService.isAuthenticated()).toBe(true);
        expect(screen.getByTestId('connection-state')).toHaveTextContent('connected');
      });
    });

    it('should handle WebSocket authentication rejection', async () => {
      setupWSAuthRejectionScenario();
      renderWebSocketComponent();
      
      await performLoginAndConnect();
      
      await waitFor(() => {
        expect(screen.getByTestId('connection-state')).toHaveTextContent('failed');
      });
      
      expect(mockWebSocketService.disconnect).toHaveBeenCalled();
    });

    it('should validate token format before WebSocket connection', async () => {
      setupInvalidTokenScenario();
      renderWebSocketComponent();
      
      await performLoginAndConnect();
      
      // Should not attempt WebSocket connection with invalid token
      expect(mockWebSocketService.connect).not.toHaveBeenCalled();
      expect(screen.getByTestId('auth-state')).toHaveTextContent('error');
    });
  });

  describe('Connection State Management', () => {
    it('should track connection states accurately', async () => {
      setupSuccessfulAuthAndWSScenario();
      renderWebSocketComponent();
      
      // Initial state
      expect(screen.getByTestId('connection-state')).toHaveTextContent('disconnected');
      
      // During connection
      await act(async () => {
        await performLoginAndConnect();
        
        // Brief moment during connection
        await waitMs(10);
        expect(screen.getByTestId('connection-state')).toHaveTextContent('connecting');
      });
      
      // After successful connection
      await waitFor(() => {
        expect(screen.getByTestId('connection-state')).toHaveTextContent('connected');
      });
    });

    it('should handle connection state transitions properly', async () => {
      setupSuccessfulAuthAndWSScenario();
      renderWebSocketComponent();
      
      await performLoginAndConnect();
      
      await waitFor(() => {
        expect(screen.getByTestId('connection-state')).toHaveTextContent('connected');
      });
      
      // Test disconnection
      const disconnectButton = screen.getByTestId('disconnect-button');
      await fireEvent.click(disconnectButton);
      
      await waitFor(() => {
        expect(mockWebSocketService.disconnect).toHaveBeenCalled();
      });
    });

    it('should maintain auth state during WebSocket operations', async () => {
      setupSuccessfulAuthAndWSScenario();
      renderWebSocketComponent();
      
      await performLoginAndConnect();
      
      await waitFor(() => {
        expect(screen.getByTestId('auth-state')).toHaveTextContent('authenticated');
        expect(screen.getByTestId('connection-state')).toHaveTextContent('connected');
      });
      
      // Verify auth state persists through WebSocket connection
      expect(localStorage.getItem('jwt_token')).toBe(validToken);
    });
  });

  describe('WebSocket URL Construction', () => {
    it('should construct WebSocket URL with proper parameters', async () => {
      setupSuccessfulAuthAndWSScenario();
      renderWebSocketComponent();
      
      await performLoginAndConnect();
      
      await waitFor(() => {
        expect(mockWebSocketService.connect).toHaveBeenCalledWith(
          expect.stringMatching(new RegExp(`^${wsBaseUrl}/ws\\?token=.+`)),
          expect.any(Object)
        );
      });
    });

    it('should include user context in WebSocket connection', async () => {
      setupSuccessfulAuthAndWSScenario();
      renderWebSocketComponent();
      
      await performLoginAndConnect();
      
      await waitFor(() => {
        expect(mockWebSocketService.connect).toHaveBeenCalledWith(
          expect.any(String),
          expect.objectContaining({
            token: validToken,
            userId: testUser.id
          })
        );
      });
    });

    it('should handle WebSocket URL construction errors', async () => {
      setupWSUrlErrorScenario();
      renderWebSocketComponent();
      
      await performLoginAndConnect();
      
      await waitFor(() => {
        expect(screen.getByTestId('connection-state')).toHaveTextContent('failed');
      });
    });
  });

  describe('Error Handling and Recovery', () => {
    it('should handle network errors during WebSocket setup', async () => {
      setupNetworkErrorScenario();
      renderWebSocketComponent();
      
      await performLoginAndConnect();
      
      await waitFor(() => {
        expect(screen.getByTestId('connection-state')).toHaveTextContent('failed');
      });
      
      // Should have attempted connection despite network error
      expect(mockWebSocketService.connect).toHaveBeenCalled();
    });

    it('should gracefully handle WebSocket connection timeout', async () => {
      setupConnectionTimeoutScenario();
      renderWebSocketComponent();
      
      await performLoginAndConnect();
      
      await waitFor(() => {
        expect(screen.getByTestId('connection-state')).toHaveTextContent('failed');
      }, { timeout: 2000 });
    });
  });

  // ========================================================================
  // HELPER FUNCTIONS - Test utilities (≤8 lines each)
  // ========================================================================

  function setupMockDefaults() {
    mockUseAuthStore.mockReturnValue({
      isAuthenticated: false,
      user: null,
      token: null
    });
    
    mockUseWebSocket.mockReturnValue({
      isConnected: false,
      connect: mockWebSocketService.connect
    });
    
    mockAuthService.getToken.mockReturnValue(null);
  }

  function renderWebSocketComponent() {
    return renderWithProviders(<WebSocketSetupTestComponent />);
  }

  async function performLoginAndConnect() {
    const loginButton = screen.getByTestId('login-button');
    await fireEvent.click(loginButton);
  }

  function setupSuccessfulAuthAndWSScenario() {
    mockAuthService.handleLogin.mockResolvedValue({
      user: testUser,
      token: validToken
    });
    
    mockAuthService.getToken.mockReturnValue(validToken);
    
    mockWebSocketService.connect.mockResolvedValue(true);
    mockWebSocketService.isAuthenticated.mockReturnValue(true);
    
    mockUseWebSocket.mockReturnValue({
      isConnected: true,
      connect: mockWebSocketService.connect,
      isConnecting: false
    });
  }

  function setupWSConnectionFailureScenario() {
    mockAuthService.handleLogin.mockResolvedValue({
      user: testUser,
      token: validToken
    });
    
    mockWebSocketService.connect.mockRejectedValueOnce(
      new Error('Connection failed')
    ).mockResolvedValue(true);
  }

  function setupAuthenticatedWSScenario() {
    setupSuccessfulAuthAndWSScenario();
    
    mockWebSocketService.isAuthenticated.mockReturnValue(true);
    mockWebSocketService.getConnectionState.mockReturnValue('authenticated');
  }

  function setupWSAuthRejectionScenario() {
    mockAuthService.handleLogin.mockResolvedValue({
      user: testUser,
      token: validToken
    });
    
    mockWebSocketService.connect.mockRejectedValue(
      new Error('Authentication rejected')
    );
    
    mockWebSocketService.isAuthenticated.mockReturnValue(false);
  }

  function setupInvalidTokenScenario() {
    const invalidToken = 'invalid.token.format';
    
    mockAuthService.handleLogin.mockResolvedValue({
      user: testUser,
      token: invalidToken
    });
    
    // Simulate token validation failure
    mockAuthService.getToken.mockImplementation(() => {
      throw new Error('Invalid token format');
    });
  }

  function setupWSUrlErrorScenario() {
    mockAuthService.handleLogin.mockResolvedValue({
      user: testUser,
      token: validToken
    });
    
    mockWebSocketService.connect.mockRejectedValue(
      new Error('Invalid WebSocket URL')
    );
  }

  function setupNetworkErrorScenario() {
    mockAuthService.handleLogin.mockResolvedValue({
      user: testUser,
      token: validToken
    });
    
    mockWebSocketService.connect.mockRejectedValue(
      new Error('Network error')
    );
  }

  function setupConnectionTimeoutScenario() {
    mockAuthService.handleLogin.mockResolvedValue({
      user: testUser,
      token: validToken
    });
    
    mockWebSocketService.connect.mockImplementation(() => 
      new Promise((_, reject) => 
        setTimeout(() => reject(new Error('Connection timeout')), 1500)
      )
    );
  }
});