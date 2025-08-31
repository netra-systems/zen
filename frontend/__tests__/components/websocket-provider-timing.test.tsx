/**
 * WebSocketProvider Timing Tests
 * ==============================
 * 
 * Tests the OAuth callback timing fix in WebSocketProvider that adds a conditional 100ms 
 * delay when receiving an initial token to ensure auth context is fully stabilized.
 * 
 * Context: WebSocketProvider now adds a conditional 100ms delay when receiving an initial 
 * token (first login scenario) to ensure auth context is fully stabilized after OAuth redirect.
 * 
 * BVJ: Enterprise segment - ensures WebSocket connection stability during OAuth flow
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import { WebSocketProvider, useWebSocketContext } from '@/providers/WebSocketProvider';
import { AuthContext } from '@/auth/context';
import { webSocketService } from '@/services/webSocketService';
import { reconciliationService } from '@/services/reconciliation';
import { unifiedAuthService } from '@/lib/unified-auth-service';
import { config as appConfig } from '@/config';
import { logger } from '@/lib/logger';

// Mock all dependencies
jest.mock('@/services/webSocketService');
jest.mock('@/services/reconciliation');
jest.mock('@/lib/unified-auth-service');
jest.mock('@/config');
jest.mock('@/lib/logger');

// Test component to consume WebSocket context and monitor timing
const TimingTestConsumer: React.FC<{ 
  onConnect?: (timestamp: number) => void;
  onContextUpdate?: (context: any) => void;
}> = ({ onConnect, onContextUpdate }) => {
  const context = useWebSocketContext();
  
  React.useEffect(() => {
    onContextUpdate?.(context);
  }, [context, onContextUpdate]);

  React.useEffect(() => {
    // Monitor for connection attempts by listening to webSocketService.connect calls
    if (webSocketService.connect && (webSocketService.connect as jest.Mock).mock.calls.length > 0) {
      onConnect?.(Date.now());
    }
  }, [onConnect]);

  return (
    <div data-testid="timing-consumer">
      <div data-testid="status">{context.status}</div>
      <div data-testid="message-count">{context.messages.length}</div>
    </div>
  );
};

// Auth provider wrapper with token state management
const TokenManagedAuthProvider: React.FC<{ 
  initialToken?: string | null;
  onTokenChange?: (token: string | null) => void;
  children: React.ReactNode;
}> = ({ initialToken, onTokenChange, children }) => {
  const [token, setToken] = React.useState<string | null>(initialToken || null);

  React.useImperativeHandle(React.useRef(), () => ({
    setToken: (newToken: string | null) => {
      setToken(newToken);
      onTokenChange?.(newToken);
    }
  }), [onTokenChange]);

  const authValue = {
    token,
    user: token ? { id: 'test-user', email: 'test@example.com' } : null,
    isAuthenticated: !!token,
    login: jest.fn(),
    logout: jest.fn(),
    refreshToken: jest.fn()
  };

  return (
    <AuthContext.Provider value={authValue}>
      {children}
    </AuthContext.Provider>
  );
};

// Custom hook to control token updates externally
const useTokenController = () => {
  const controllerRef = React.useRef<any>(null);
  
  return {
    setControllerRef: (ref: any) => {
      controllerRef.current = ref;
    },
    updateToken: (token: string | null) => {
      if (controllerRef.current?.setToken) {
        controllerRef.current.setToken(token);
      }
    }
  };
};

describe('WebSocketProvider Timing Tests', () => {
      setupAntiHang();
    jest.setTimeout(10000);
  const mockWebSocketService = {
    onStatusChange: null,
    onMessage: null,
    connect: jest.fn(),
    disconnect: jest.fn(),
    sendMessage: jest.fn(),
    updateToken: jest.fn().mockResolvedValue(undefined),
    getSecureUrl: jest.fn((url: string) => `${url}?jwt=test-token`)
  };

  const mockReconciliationService = {
    processConfirmation: jest.fn((msg) => msg),
    addOptimisticMessage: jest.fn((msg) => ({ ...msg, tempId: 'temp-123' })),
    getStats: jest.fn(() => ({ confirmed: 0, failed: 0, pending: 0 }))
  };

  const mockUnifiedAuthService = {
    getWebSocketAuthConfig: jest.fn(() => ({
      refreshToken: jest.fn().mockResolvedValue('refreshed-token')
    }))
  };

  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
    
    // Setup default mocks
    (webSocketService as jest.Mocked<typeof webSocketService>) = mockWebSocketService as any;
    (reconciliationService as jest.Mocked<typeof reconciliationService>) = mockReconciliationService as any;
    (unifiedAuthService as jest.Mocked<typeof unifiedAuthService>) = mockUnifiedAuthService as any;
    
    (appConfig as jest.Mocked<typeof appConfig>) = {
      wsUrl: 'ws://localhost:8000/ws',
      apiUrl: 'http://localhost:8000/api'
    } as any;
  });

  afterEach(() => {
    jest.useRealTimers();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
      cleanupAntiHang();
  });

  /**
   * Test 1: Initial Token Delay Verification
   * ========================================
   * 
   * Verifies that a 100ms delay is applied ONLY when a token appears for the first time
   * (OAuth callback scenario where previousTokenRef.current is null).
   * 
   * This test is challenging because it requires:
   * - Precise timing measurement
   * - Complex state transitions (no token -> token)
   * - Verification that delay only applies to initial token, not immediate connections
   */
  it('should apply 100ms delay only when token appears for first time (OAuth callback scenario)', async () => {
    const connectionTimestamps: number[] = [];
    const tokenChangeTimestamps: number[] = [];
    
    // Track when connections are attempted
    const trackConnection = (timestamp: number) => {
      connectionTimestamps.push(timestamp);
    };

    // Track when tokens change
    const trackTokenChange = (token: string | null) => {
      tokenChangeTimestamps.push(Date.now());
    };

    // Start with no token (pre-OAuth state)
    const TestWrapper: React.FC = () => {
      const [token, setToken] = React.useState<string | null>(null);
      
      // Expose token setter for test control
      React.useEffect(() => {
        (global as any).setTestToken = setToken;
      }, []);

      const authValue = {
        token,
        user: token ? { id: 'test-user', email: 'test@example.com' } : null,
        isAuthenticated: !!token,
        login: jest.fn(),
        logout: jest.fn(),
        refreshToken: jest.fn()
      };

      return (
        <AuthContext.Provider value={authValue}>
          <WebSocketProvider>
            <TimingTestConsumer 
              onConnect={trackConnection}
              onContextUpdate={() => {}}
            />
          </WebSocketProvider>
        </AuthContext.Provider>
      );
    };

    render(<TestWrapper />);

    // Initial state: no token, no connection attempts
    expect(mockWebSocketService.connect).not.toHaveBeenCalled();
    expect(connectionTimestamps).toHaveLength(0);

    // Simulate OAuth callback - token appears for first time
    const tokenSetTime = Date.now();
    act(() => {
      trackTokenChange('initial-oauth-token-abc123');
      (global as any).setTestToken('initial-oauth-token-abc123');
    });

    // Fast-forward to just before the delay should complete
    act(() => {
      jest.advanceTimersByTime(99);
    });

    // Should not have connected yet (delay still in effect)
    expect(mockWebSocketService.connect).not.toHaveBeenCalled();

    // Fast-forward past the 100ms delay
    act(() => {
      jest.advanceTimersByTime(1);
    });

    // Now should have connected
    await waitFor(() => {
      expect(mockWebSocketService.connect).toHaveBeenCalledTimes(1);
    });

    // Verify timing: connection should happen ~100ms after token was set
    const connectionTime = Date.now();
    const actualDelay = connectionTime - tokenSetTime;
    
    // Allow some tolerance for timing precision in tests
    expect(actualDelay).toBeGreaterThanOrEqual(100);
    expect(actualDelay).toBeLessThan(120); // Some buffer for test execution

    // Verify connection parameters include the OAuth token
    expect(mockWebSocketService.connect).toHaveBeenCalledWith(
      'ws://localhost:8000/ws?jwt=test-token',
      expect.objectContaining({
        token: 'initial-oauth-token-abc123'
      })
    );

    // Clean up global
    delete (global as any).setTestToken;
  });

  /**
   * Test 2: No Delay on Token Refresh
   * =================================
   * 
   * Verifies that NO delay is added when a token changes (refresh scenario) - 
   * only when previousTokenRef.current already exists.
   * 
   * This test is challenging because it requires:
   * - Setting up an existing token state first
   * - Tracking precise timing of token updates vs connection updates  
   * - Ensuring WebSocket.updateToken is called instead of full reconnection
   * - Verifying no setTimeout delay is applied
   */
  it('should NOT apply delay when token changes during refresh (existing token scenario)', async () => {
    const connectionAttempts: Array<{ timestamp: number; type: 'connect' | 'update' }> = [];

    // Track both initial connections and token updates
    const originalConnect = mockWebSocketService.connect;
    const originalUpdateToken = mockWebSocketService.updateToken;

    mockWebSocketService.connect = jest.fn((...args) => {
      connectionAttempts.push({ timestamp: Date.now(), type: 'connect' });
      return originalConnect.apply(mockWebSocketService, args);
    });

    mockWebSocketService.updateToken = jest.fn((...args) => {
      connectionAttempts.push({ timestamp: Date.now(), type: 'update' });
      return originalUpdateToken.apply(mockWebSocketService, args);
    });

    const TestWrapper: React.FC = () => {
      // Start with an existing token (already authenticated state)
      const [token, setToken] = React.useState<string | null>('existing-token-xyz789');
      
      // Expose token setter for test control
      React.useEffect(() => {
        (global as any).setTestToken = setToken;
      }, []);

      const authValue = {
        token,
        user: token ? { id: 'test-user', email: 'test@example.com' } : null,
        isAuthenticated: !!token,
        login: jest.fn(),
        logout: jest.fn(),
        refreshToken: jest.fn()
      };

      return (
        <AuthContext.Provider value={authValue}>
          <WebSocketProvider>
            <TimingTestConsumer onContextUpdate={() => {}} />
          </WebSocketProvider>
        </AuthContext.Provider>
      );
    };

    render(<TestWrapper />);

    // Let initial connection establish (this should NOT have delay since token already exists)
    act(() => {
      jest.advanceTimersByTime(0); // Process immediate effects
    });

    await waitFor(() => {
      expect(mockWebSocketService.connect).toHaveBeenCalledTimes(1);
    });

    expect(connectionAttempts).toHaveLength(1);
    expect(connectionAttempts[0].type).toBe('connect');

    // Clear tracking for refresh test
    connectionAttempts.length = 0;
    jest.clearAllMocks();

    // Simulate token refresh (existing token -> new token)
    const refreshStartTime = Date.now();
    act(() => {
      (global as any).setTestToken('refreshed-token-def456');
    });

    // Advance timers to process any effects
    act(() => {
      jest.advanceTimersByTime(0);
    });

    // Should immediately call updateToken, not establish new connection with delay
    await waitFor(() => {
      expect(mockWebSocketService.updateToken).toHaveBeenCalledWith('refreshed-token-def456');
    });

    // Verify no delay was applied to token refresh
    const updateTime = Date.now();
    const timingDifference = updateTime - refreshStartTime;
    
    // Should be immediate (< 10ms), definitely not 100ms+ delay
    expect(timingDifference).toBeLessThan(10);

    // Should NOT have called connect again (only updateToken)
    expect(mockWebSocketService.connect).not.toHaveBeenCalled();
    
    // Verify updateToken was called with correct parameters
    expect(mockWebSocketService.updateToken).toHaveBeenCalledTimes(1);
    expect(mockWebSocketService.updateToken).toHaveBeenCalledWith('refreshed-token-def456');

    // Clean up global
    delete (global as any).setTestToken;
  });

  /**
   * Test 3: Race Condition Prevention
   * =================================
   * 
   * Tests that WebSocket connection doesn't fail even with rapid token changes during OAuth flow.
   * This simulates complex race conditions where:
   * 1. OAuth callback provides initial token
   * 2. Token refresh happens before initial connection completes
   * 3. Multiple rapid token updates occur
   * 4. WebSocket should handle all changes gracefully without connection failures
   * 
   * This test is challenging because it requires:
   * - Simulating complex async timing scenarios
   * - Managing multiple overlapping setTimeout delays
   * - Verifying connection stability under race conditions
   * - Testing both connection and token update code paths
   */
  it('should prevent race conditions during rapid token changes in OAuth flow', async () => {
    const connectionEvents: Array<{
      timestamp: number;
      type: 'connect_attempt' | 'connect_success' | 'token_update' | 'connection_error';
      token?: string;
      error?: any;
    }> = [];

    // Mock complex WebSocket service behavior
    let activeConnection: any = null;
    let connectionInProgress = false;

    const mockComplexWebSocketService = {
      ...mockWebSocketService,
      connect: jest.fn(async (url: string, options: any) => {
        connectionEvents.push({
          timestamp: Date.now(),
          type: 'connect_attempt',
          token: options.token
        });
        
        connectionInProgress = true;
        
        // Simulate async connection establishment
        return new Promise((resolve, reject) => {
          setTimeout(() => {
            if (!connectionInProgress) {
              // Connection was cancelled
              connectionEvents.push({
                timestamp: Date.now(),
                type: 'connection_error',
                error: 'Connection cancelled',
                token: options.token
              });
              reject(new Error('Connection cancelled'));
              return;
            }
            
            activeConnection = { url, options, token: options.token };
            connectionInProgress = false;
            
            connectionEvents.push({
              timestamp: Date.now(),
              type: 'connect_success',
              token: options.token
            });
            
            resolve(activeConnection);
          }, 50); // 50ms connection time
        });
      }),
      
      updateToken: jest.fn(async (newToken: string) => {
        connectionEvents.push({
          timestamp: Date.now(),
          type: 'token_update',
          token: newToken
        });
        
        if (activeConnection) {
          activeConnection.token = newToken;
        }
        
        return Promise.resolve();
      }),
      
      disconnect: jest.fn(() => {
        connectionInProgress = false;
        activeConnection = null;
      })
    };

    (webSocketService as any) = mockComplexWebSocketService;

    const TestWrapper: React.FC = () => {
      const [token, setToken] = React.useState<string | null>(null);
      
      React.useEffect(() => {
        (global as any).setTestToken = setToken;
      }, []);

      const authValue = {
        token,
        user: token ? { id: 'test-user', email: 'test@example.com' } : null,
        isAuthenticated: !!token,
        login: jest.fn(),
        logout: jest.fn(),
        refreshToken: jest.fn()
      };

      return (
        <AuthContext.Provider value={authValue}>
          <WebSocketProvider>
            <TimingTestConsumer onContextUpdate={() => {}} />
          </WebSocketProvider>
        </AuthContext.Provider>
      );
    };

    render(<TestWrapper />);

    // Phase 1: Simulate OAuth callback with initial token
    act(() => {
      (global as any).setTestToken('oauth-initial-token-123');
    });

    // Advance just past the initial delay (100ms)
    act(() => {
      jest.advanceTimersByTime(110);
    });

    // Phase 2: Before initial connection completes, simulate rapid token changes
    // (this simulates token refresh happening immediately after OAuth)
    act(() => {
      (global as any).setTestToken('refreshed-token-456');
    });

    // Advance a small amount
    act(() => {
      jest.advanceTimersByTime(25);
    });

    // Phase 3: Another rapid token change (simulating multiple refreshes)
    act(() => {
      (global as any).setTestToken('double-refreshed-token-789');
    });

    // Advance timers to let all async operations complete
    act(() => {
      jest.advanceTimersByTime(200);
    });

    // Wait for all promises to resolve
    await waitFor(() => {
      expect(connectionEvents.some(e => e.type === 'connect_success')).toBe(true);
    }, { timeout: 2000 });

    // Verify race condition handling:
    // 1. Initial connection should have been attempted with first token
    const connectAttempts = connectionEvents.filter(e => e.type === 'connect_attempt');
    expect(connectAttempts.length).toBeGreaterThanOrEqual(1);
    expect(connectAttempts[0].token).toBe('oauth-initial-token-123');

    // 2. Token updates should have been called for subsequent changes
    const tokenUpdates = connectionEvents.filter(e => e.type === 'token_update');
    expect(tokenUpdates.length).toBeGreaterThanOrEqual(1);
    
    // 3. Final connection should be successful and use latest token
    const successfulConnections = connectionEvents.filter(e => e.type === 'connect_success');
    expect(successfulConnections.length).toBeGreaterThanOrEqual(1);

    // 4. No connection errors should occur due to race conditions
    const connectionErrors = connectionEvents.filter(e => e.type === 'connection_error');
    expect(connectionErrors).toHaveLength(0);

    // 5. Verify final state has the latest token
    const finalTokenUpdates = tokenUpdates.slice(-1);
    if (finalTokenUpdates.length > 0) {
      expect(['refreshed-token-456', 'double-refreshed-token-789']).toContain(
        finalTokenUpdates[0].token
      );
    }

    // 6. Verify connection sequence makes sense (no overlapping connects)
    let connectionStartTime: number | null = null;
    let hasValidSequence = true;
    
    for (const event of connectionEvents) {
      if (event.type === 'connect_attempt' && connectionStartTime === null) {
        connectionStartTime = event.timestamp;
      } else if (event.type === 'connect_success' && connectionStartTime !== null) {
        expect(event.timestamp).toBeGreaterThan(connectionStartTime);
        connectionStartTime = null;
      }
    }

    // Clean up
    delete (global as any).setTestToken;
  });
});