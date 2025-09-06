/**
 * WebSocketProvider Test Suite
 * Tests for SSOT connection management and prevention of connection loops
 */

import React from 'react';
import { render, waitFor, act, screen } from '@testing-library/react';
import { WebSocketProvider, useWebSocketContext } from '../../providers/WebSocketProvider';
import { AuthContext } from '@/auth/context';
import { unifiedAuthService } from '@/lib/unified-auth-service';

// Mock the webSocketService module
jest.mock('../../services/webSocketService', () => ({
  webSocketService: {
    connect: jest.fn(),
    updateToken: jest.fn().mockResolvedValue(undefined),
    disconnect: jest.fn(),
    sendMessage: jest.fn(),
    getSecureUrl: jest.fn((url) => url),
    onStatusChange: null,
    onMessage: null,
    getState: jest.fn(() => 'disconnected'),
  }
}));

import { webSocketService } from '../../services/webSocketService';

// Get typed mocks after import
const mockConnect = webSocketService.connect as jest.MockedFunction<typeof webSocketService.connect>;
const mockUpdateToken = webSocketService.updateToken as jest.MockedFunction<typeof webSocketService.updateToken>;
const mockDisconnect = webSocketService.disconnect as jest.MockedFunction<typeof webSocketService.disconnect>;
const mockSendMessage = webSocketService.sendMessage as jest.MockedFunction<typeof webSocketService.sendMessage>;
const mockGetSecureUrl = webSocketService.getSecureUrl as jest.MockedFunction<typeof webSocketService.getSecureUrl>;

jest.mock('@/lib/unified-auth-service');
jest.mock('@/config', () => ({
  config: {
    apiUrl: 'http://localhost:8000',
    wsUrl: 'ws://localhost:8000/ws'
  }
}));
jest.mock('../../services/reconciliation', () => ({
  reconciliationService: {
    addOptimisticMessage: jest.fn((msg) => ({ ...msg, tempId: 'temp_123' })),
    processConfirmation: jest.fn((msg) => msg),
    getStats: jest.fn(() => ({}))
  }
}));
jest.mock('../../services/chatStatePersistence', () => ({
  chatStatePersistence: {
    getRestorableState: jest.fn(() => null),
    updateThread: jest.fn(),
    updateMessages: jest.fn(),
    destroy: jest.fn()
  }
}));
jest.mock('@/lib/logger', () => ({
  logger: {
    debug: jest.fn(),
    info: jest.fn(),
    warn: jest.fn(),
    error: jest.fn(),
  }
}));

// Mock child component to test context
const TestConsumer = () => {
  const context = useWebSocketContext();
  return (
    <div>
      <div data-testid="status">{context.status}</div>
      <div data-testid="message-count">{context.messages.length}</div>
    </div>
  );
};

describe('WebSocketProvider - SSOT Connection Management', () => {
  let mockAuthContext: any;

  beforeEach(() => {
    // Reset all mocks
    jest.clearAllMocks();
    mockConnect.mockClear();
    mockUpdateToken.mockClear();
    mockDisconnect.mockClear();
    mockSendMessage.mockClear();
    mockGetSecureUrl.mockClear();
    
    // Reset mock implementation
    mockUpdateToken.mockResolvedValue(undefined);
    mockGetSecureUrl.mockImplementation((url) => url);

    // Setup auth context mock
    mockAuthContext = {
      token: null,
      initialized: false,
      user: null,
    };

    // CRITICAL: Override the global auth mock to control useAuth() behavior
    (global as any).mockAuthState = {
      token: null,
      initialized: false,
      user: null,
      loading: false,
      error: null,
      isAuthenticated: false,
      authConfig: {},
      login: jest.fn(),
      logout: jest.fn()
    };

    // Setup unified auth service mock
    (unifiedAuthService.getWebSocketAuthConfig as jest.Mock) = jest.fn().mockReturnValue({
      refreshToken: jest.fn().mockResolvedValue('refreshed_token')
    });
  });

  describe('Connection Loop Prevention', () => {
    it('should NOT create multiple connections when auth initializes with token', async () => {
      // Start with no auth
      const { rerender } = render(
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <TestConsumer />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      // Verify no connection attempt without auth
      expect(mockConnect).not.toHaveBeenCalled();

      // Simulate auth initialization with token (this would previously trigger 2 effects)
      mockAuthContext = {
        token: 'test_token_123',
        initialized: true,
        user: { id: 'user1', email: 'test@test.com' }
      };

      // CRITICAL: Update global mock state to match
      (global as any).mockAuthState = {
        token: 'test_token_123',
        initialized: true,
        user: { id: 'user1', email: 'test@test.com' },
        loading: false,
        error: null,
        isAuthenticated: true,
        authConfig: {},
        login: jest.fn(),
        logout: jest.fn()
      };

      await act(async () => {
        rerender(
          <AuthContext.Provider value={mockAuthContext}>
            <WebSocketProvider>
              <TestConsumer />
            </WebSocketProvider>
          </AuthContext.Provider>
        );
      });

      // Wait for debounced effects to settle (WebSocketProvider uses 50ms debounce)
      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 100));
      });

      await waitFor(() => {
        // CRITICAL: Should only connect ONCE despite multiple state changes
        expect(mockConnect).toHaveBeenCalledTimes(1);
      });

      // Verify correct connection parameters
      expect(mockConnect).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          token: 'test_token_123'
        })
      );
    });

    it('should handle token refresh without creating new connection', async () => {
      // Start with authenticated state
      mockAuthContext = {
        token: 'initial_token',
        initialized: true,
        user: { id: 'user1', email: 'test@test.com' }
      };

      const { rerender } = render(
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <TestConsumer />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      // Wait for debounced effects to settle
      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 100));
      });

      await waitFor(() => {
        expect(mockConnect).toHaveBeenCalledTimes(1);
      });

      // Simulate token refresh (new token, same user)
      mockAuthContext = {
        token: 'refreshed_token',
        initialized: true,
        user: { id: 'user1', email: 'test@test.com' }
      };

      // Update global mock state
      (global as any).mockAuthState = {
        token: 'refreshed_token',
        initialized: true,
        user: { id: 'user1', email: 'test@test.com' },
        loading: false,
        error: null,
        isAuthenticated: true,
        authConfig: {},
        login: jest.fn(),
        logout: jest.fn()
      };

      await act(async () => {
        rerender(
          <AuthContext.Provider value={mockAuthContext}>
            <WebSocketProvider>
              <TestConsumer />
            </WebSocketProvider>
          </AuthContext.Provider>
        );
      });

      // Wait for debounced effects to settle
      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 100));
      });

      await waitFor(() => {
        // Should update token, NOT create new connection
        expect(mockUpdateToken).toHaveBeenCalledWith('refreshed_token');
        // Still only 1 connection total
        expect(mockConnect).toHaveBeenCalledTimes(1);
      });
    });

    it('should prevent rapid reconnection attempts', async () => {
      mockAuthContext = {
        token: 'test_token',
        initialized: true,
        user: { id: 'user1', email: 'test@test.com' }
      };

      // Update global mock state
      (global as any).mockAuthState = {
        token: 'test_token',
        initialized: true,
        user: { id: 'user1', email: 'test@test.com' },
        loading: false,
        error: null,
        isAuthenticated: true,
        authConfig: {},
        login: jest.fn(),
        logout: jest.fn()
      };

      const { rerender } = render(
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <TestConsumer />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      // Simulate rapid token changes (e.g., from multiple auth updates)
      for (let i = 0; i < 5; i++) {
        mockAuthContext = {
          ...mockAuthContext,
          token: `token_${i}`,
        };

        // Update global mock state
        (global as any).mockAuthState = {
          token: `token_${i}`,
          initialized: true,
          user: { id: 'user1', email: 'test@test.com' },
          loading: false,
          error: null,
          isAuthenticated: true,
          authConfig: {},
          login: jest.fn(),
          logout: jest.fn()
        };

        await act(async () => {
          rerender(
            <AuthContext.Provider value={mockAuthContext}>
              <WebSocketProvider>
                <TestConsumer />
              </WebSocketProvider>
            </AuthContext.Provider>
          );
        });
      }

      // Wait for all debounced effects to settle
      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 200));
      });

      // Despite 5 token changes, should still only have 1 connection
      await waitFor(() => {
        expect(mockConnect).toHaveBeenCalledTimes(1);
        // Token updates should be batched/debounced
        expect(mockUpdateToken.mock.calls.length).toBeLessThanOrEqual(5);
      });
    });

    it('should handle auth logout gracefully', async () => {
      // Start authenticated
      mockAuthContext = {
        token: 'test_token',
        initialized: true,
        user: { id: 'user1', email: 'test@test.com' }
      };

      // Update global mock state
      (global as any).mockAuthState = {
        token: 'test_token',
        initialized: true,
        user: { id: 'user1', email: 'test@test.com' },
        loading: false,
        error: null,
        isAuthenticated: true,
        authConfig: {},
        login: jest.fn(),
        logout: jest.fn()
      };

      const { rerender } = render(
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <TestConsumer />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      // Wait for debounced effects to settle
      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 100));
      });

      await waitFor(() => {
        expect(mockConnect).toHaveBeenCalledTimes(1);
      });

      // Simulate logout
      mockAuthContext = {
        token: null,
        initialized: true,
        user: null
      };

      // Update global mock state for logout
      (global as any).mockAuthState = {
        token: null,
        initialized: true,
        user: null,
        loading: false,
        error: null,
        isAuthenticated: false,
        authConfig: {},
        login: jest.fn(),
        logout: jest.fn()
      };

      await act(async () => {
        rerender(
          <AuthContext.Provider value={mockAuthContext}>
            <WebSocketProvider>
              <TestConsumer />
            </WebSocketProvider>
          </AuthContext.Provider>
        );
      });

      // Wait for debounced effects to settle
      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 100));
      });

      await waitFor(() => {
        // Should disconnect on logout
        expect(mockDisconnect).toHaveBeenCalled();
        // No new connections
        expect(mockConnect).toHaveBeenCalledTimes(1);
      });
    });
  });

  describe('Connection State Management', () => {
    it('should track connection state correctly through lifecycle', async () => {
      const stateLog: string[] = [];
      
      // Mock to track state changes
      mockConnect.mockImplementation((url, options) => {
        stateLog.push('connecting');
        // Simulate successful connection
        setTimeout(() => {
          if (options.onOpen) {
            stateLog.push('connected');
            options.onOpen();
          }
        }, 10);
      });

      mockAuthContext = {
        token: 'test_token',
        initialized: true,
        user: { id: 'user1', email: 'test@test.com' }
      };

      render(
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <TestConsumer />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      // Wait for debounced effects and simulate connection completion
      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 100));
      });

      await waitFor(() => {
        expect(stateLog).toEqual(['connecting', 'connected']);
      });
    });

    it('should not attempt connection while already connecting', async () => {
      // Mock slow connection
      mockConnect.mockImplementation(() => {
        return new Promise((resolve) => {
          setTimeout(resolve, 100);
        });
      });

      mockAuthContext = {
        token: 'test_token',
        initialized: true,
        user: { id: 'user1', email: 'test@test.com' }
      };

      const { rerender } = render(
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <TestConsumer />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      // Trigger multiple rapid re-renders while connecting
      for (let i = 0; i < 3; i++) {
        await act(async () => {
          rerender(
            <AuthContext.Provider value={mockAuthContext}>
              <WebSocketProvider>
                <TestConsumer />
              </WebSocketProvider>
            </AuthContext.Provider>
          );
        });
      }

      // Should still only have 1 connection attempt
      expect(mockConnect).toHaveBeenCalledTimes(1);
    });
  });

  describe('Message Handling', () => {
    it('should handle incoming messages correctly', async () => {
      mockAuthContext = {
        token: 'test_token',
        initialized: true,
        user: { id: 'user1', email: 'test@test.com' }
      };

      const { getByTestId } = render(
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <TestConsumer />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      // Wait for debounced effects to settle
      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 100));
      });

      await waitFor(() => {
        expect(mockConnect).toHaveBeenCalled();
      });

      // Get the onMessage handler that was registered
      const onMessageHandler = (webSocketService as any).onMessage;
      expect(onMessageHandler).toBeDefined();

      // Simulate incoming message
      act(() => {
        onMessageHandler({
          type: 'assistant_message',
          payload: {
            message_id: 'msg_1',
            content: 'Hello from assistant',
            timestamp: Date.now()
          }
        });
      });

      await waitFor(() => {
        // Verify message was added to context
        expect(getByTestId('message-count').textContent).toBe('1');
      });
    });

    it('should prevent duplicate messages', async () => {
      mockAuthContext = {
        token: 'test_token',
        initialized: true,
        user: { id: 'user1', email: 'test@test.com' }
      };

      const { getByTestId } = render(
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <TestConsumer />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      // Wait for debounced effects to settle
      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 100));
      });

      await waitFor(() => {
        expect(mockConnect).toHaveBeenCalled();
      });

      const onMessageHandler = (webSocketService as any).onMessage;

      // Send same message twice
      const duplicateMessage = {
        type: 'assistant_message',
        payload: {
          message_id: 'msg_duplicate',
          content: 'Duplicate message',
          timestamp: Date.now()
        }
      };

      act(() => {
        onMessageHandler(duplicateMessage);
        onMessageHandler(duplicateMessage); // Duplicate
      });

      await waitFor(() => {
        // Should only have 1 message, not 2
        expect(getByTestId('message-count').textContent).toBe('1');
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle connection errors gracefully', async () => {
      mockConnect.mockImplementation((url, options) => {
        // Simulate connection error
        setTimeout(() => {
          if (options.onError) {
            options.onError({
              code: 1006,
              message: 'Connection failed',
              type: 'connection',
              recoverable: true,
              timestamp: Date.now()
            });
          }
        }, 10);
      });

      mockAuthContext = {
        token: 'test_token',
        initialized: true,
        user: { id: 'user1', email: 'test@test.com' }
      };

      render(
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <TestConsumer />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      // Wait for debounced effects to settle
      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 100));
      });

      await waitFor(() => {
        expect(mockConnect).toHaveBeenCalledTimes(1);
      });

      // Should not crash and should handle error
    });

    it('should handle auth errors with proper backoff', async () => {
      let attemptCount = 0;
      mockConnect.mockImplementation((url, options) => {
        attemptCount++;
        // Simulate auth error
        setTimeout(() => {
          if (options.onClose) {
            options.onClose();
          }
          if (options.onError) {
            options.onError({
              code: 1008,
              message: 'Authentication failed',
              type: 'auth',
              recoverable: false,
              timestamp: Date.now()
            });
          }
        }, 10);
      });

      mockAuthContext = {
        token: 'invalid_token',
        initialized: true,
        user: { id: 'user1', email: 'test@test.com' }
      };

      render(
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <TestConsumer />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      // Wait a bit for potential retries
      await new Promise(resolve => setTimeout(resolve, 200));

      // Should not spam connection attempts on auth failure
      expect(attemptCount).toBeLessThanOrEqual(2);
    });
  });

  describe('Cleanup', () => {
    it('should cleanup on unmount', async () => {
      mockAuthContext = {
        token: 'test_token',
        initialized: true,
        user: { id: 'user1', email: 'test@test.com' }
      };

      const { unmount } = render(
        <AuthContext.Provider value={mockAuthContext}>
          <WebSocketProvider>
            <TestConsumer />
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      // Wait for debounced effects to settle
      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 100));
      });

      await waitFor(() => {
        expect(mockConnect).toHaveBeenCalled();
      });

      // Unmount the component
      unmount();

      // Should disconnect and cleanup
      expect(mockDisconnect).toHaveBeenCalled();
      expect((webSocketService as any).onStatusChange).toBeNull();
      expect((webSocketService as any).onMessage).toBeNull();
    });
  });
});

describe('WebSocketProvider - Integration Tests', () => {
  it('should handle complete auth flow without connection loops', async () => {
    const connectionLog: string[] = [];
    
    // Setup mocks to track calls
    mockConnect.mockImplementation((url, options) => {
      connectionLog.push(`connect:${url}`);
    });
    mockUpdateToken.mockImplementation((token) => {
      connectionLog.push(`updateToken:${token}`);
      return Promise.resolve();
    });
    mockDisconnect.mockImplementation(() => {
      connectionLog.push('disconnect');
    });

    // Simulate complete auth flow
    const authStates = [
      { token: null, initialized: false, user: null }, // Initial
      { token: null, initialized: true, user: null }, // Initialized, no user
      { token: 'token_1', initialized: true, user: { id: '1' } }, // Login
      { token: 'token_2', initialized: true, user: { id: '1' } }, // Token refresh
      { token: null, initialized: true, user: null }, // Logout
    ];

    const { rerender } = render(
      <AuthContext.Provider value={authStates[0]}>
        <WebSocketProvider>
          <TestConsumer />
        </WebSocketProvider>
      </AuthContext.Provider>
    );

    // Step through auth states
    for (let i = 1; i < authStates.length; i++) {
      await act(async () => {
        rerender(
          <AuthContext.Provider value={authStates[i]}>
            <WebSocketProvider>
              <TestConsumer />
            </WebSocketProvider>
          </AuthContext.Provider>
        );
      });
      
      // Wait for debounced effects to settle (WebSocketProvider uses 50ms debounce)
      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 100));
      });
    }

    // Verify correct connection sequence
    expect(connectionLog).toEqual([
      expect.stringContaining('connect:'), // Initial connection on login
      'updateToken:token_2', // Token update, not reconnect
      'disconnect', // Disconnect on logout
    ]);

    // Verify no connection loops
    const connectCalls = connectionLog.filter(log => log.startsWith('connect:'));
    expect(connectCalls.length).toBe(1); // Only one connection despite multiple auth changes
  });
});