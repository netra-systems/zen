/**
 * Integration Tests for WebSocket Ticket Authentication - Issue #1295
 * 
 * Tests the complete integration between AuthProvider, TicketAuthProvider, 
 * WebSocketService, and the unified auth service.
 */

import React from 'react';
import { render, act, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth } from '@/auth/context';
import { WebSocketProvider, useWebSocketContext } from '@/providers/WebSocketProvider';
import { webSocketService } from '@/services/webSocketService';
import { ticketAuthProvider } from '@/lib/ticket-auth-provider';
import { unifiedAuthService } from '@/lib/unified-auth-service';
import { websocketTicketService } from '@/services/websocketTicketService';

// Mock external dependencies
jest.mock('@/services/webSocketService');
jest.mock('@/services/websocketTicketService');
jest.mock('@/lib/unified-auth-service');
jest.mock('@/lib/logger', () => ({
  logger: {
    debug: jest.fn(),
    info: jest.fn(),
    warn: jest.fn(),
    error: jest.fn()
  }
}));

// Mock config
jest.mock('@/config', () => ({
  config: {
    apiUrl: 'https://api-staging.netrasystems.ai',
    wsUrl: 'wss://api-staging.netrasystems.ai/ws'
  }
}));

// Mock localStorage
const mockLocalStorage = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => { store[key] = value; },
    removeItem: (key: string) => { delete store[key]; },
    clear: () => { store = {}; }
  };
})();

Object.defineProperty(window, 'localStorage', { value: mockLocalStorage });

describe('WebSocket Ticket Authentication Integration', () => {
  const mockWebSocketService = webSocketService as jest.Mocked<typeof webSocketService>;
  const mockWebsocketTicketService = websocketTicketService as jest.Mocked<typeof websocketTicketService>;
  const mockUnifiedAuthService = unifiedAuthService as jest.Mocked<typeof unifiedAuthService>;

  // Test component to access auth and websocket contexts
  const TestComponent: React.FC = () => {
    const { token, user, initialized } = useAuth();
    const { status } = useWebSocketContext();
    
    return (
      <div>
        <div data-testid="auth-token">{token || 'no-token'}</div>
        <div data-testid="auth-user">{user?.email || 'no-user'}</div>
        <div data-testid="auth-initialized">{initialized ? 'true' : 'false'}</div>
        <div data-testid="ws-status">{status}</div>
      </div>
    );
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockLocalStorage.clear();
    
    // Setup default mocks
    mockUnifiedAuthService.getWebSocketAuthConfig.mockReturnValue({
      token: 'test-jwt-token',
      refreshToken: jest.fn().mockResolvedValue('refreshed-jwt-token'),
      getTicket: jest.fn().mockResolvedValue({
        success: true,
        ticket: {
          ticket: 'test-ticket-123',
          expires_at: Date.now() + 300000,
          created_at: Date.now(),
          websocket_url: 'wss://api-staging.netrasystems.ai/ws?ticket=test-ticket-123'
        }
      }),
      useTicketAuth: true
    });
    
    mockWebsocketTicketService.acquireTicket.mockResolvedValue({
      success: true,
      ticket: {
        ticket: 'test-ticket-123',
        expires_at: Date.now() + 300000,
        created_at: Date.now(),
        websocket_url: 'wss://api-staging.netrasystems.ai/ws?ticket=test-ticket-123'
      }
    });
    
    mockWebsocketTicketService.clearTicketCache.mockImplementation(() => {});
    
    mockWebSocketService.connect.mockImplementation(() => {});
    mockWebSocketService.getSecureUrl.mockImplementation((url) => url);
  });

  describe('Ticket Authentication Flow', () => {
    it('should integrate ticket auth with WebSocket connection when enabled', async () => {
      // Set up authenticated state
      mockLocalStorage.setItem('jwt_token', 'test-jwt-token');
      
      const { getByTestId } = render(
        <AuthProvider>
          <WebSocketProvider>
            <TestComponent />
          </WebSocketProvider>
        </AuthProvider>
      );

      // Wait for auth initialization
      await waitFor(() => {
        expect(getByTestId('auth-initialized').textContent).toBe('true');
      });

      // Verify WebSocket connection was called with ticket auth config
      expect(mockWebSocketService.connect).toHaveBeenCalledWith(
        'wss://api-staging.netrasystems.ai/ws',
        expect.objectContaining({
          token: 'test-jwt-token',
          useTicketAuth: true,
          getTicket: expect.any(Function),
          clearTicketCache: expect.any(Function)
        })
      );
    });

    it('should fall back to JWT when ticket auth fails', async () => {
      // Setup ticket auth failure
      mockUnifiedAuthService.getWebSocketAuthConfig.mockReturnValue({
        token: 'test-jwt-token',
        refreshToken: jest.fn().mockResolvedValue('refreshed-jwt-token'),
        getTicket: jest.fn().mockResolvedValue({
          success: false,
          error: 'Ticket service unavailable',
          recoverable: true
        }),
        useTicketAuth: true
      });
      
      mockLocalStorage.setItem('jwt_token', 'test-jwt-token');
      
      render(
        <AuthProvider>
          <WebSocketProvider>
            <TestComponent />
          </WebSocketProvider>
        </AuthProvider>
      );

      await waitFor(() => {
        expect(mockWebSocketService.connect).toHaveBeenCalledWith(
          'wss://api-staging.netrasystems.ai/ws',
          expect.objectContaining({
            token: 'test-jwt-token',
            useTicketAuth: true // Still tries ticket auth, but service will handle fallback
          })
        );
      });
    });

    it('should disable ticket auth when feature flag is off', async () => {
      // Disable ticket auth
      mockUnifiedAuthService.getWebSocketAuthConfig.mockReturnValue({
        token: 'test-jwt-token',
        refreshToken: jest.fn().mockResolvedValue('refreshed-jwt-token'),
        getTicket: jest.fn().mockResolvedValue({
          success: false,
          error: 'Ticket authentication is disabled',
          recoverable: false
        }),
        useTicketAuth: false
      });
      
      mockLocalStorage.setItem('jwt_token', 'test-jwt-token');
      
      render(
        <AuthProvider>
          <WebSocketProvider>
            <TestComponent />
          </WebSocketProvider>
        </AuthProvider>
      );

      await waitFor(() => {
        expect(mockWebSocketService.connect).toHaveBeenCalledWith(
          'wss://api-staging.netrasystems.ai/ws',
          expect.objectContaining({
            token: 'test-jwt-token',
            useTicketAuth: false
          })
        );
      });
    });
  });

  describe('Auth State Synchronization', () => {
    it('should update ticket provider when auth token changes', async () => {
      const { rerender } = render(
        <AuthProvider>
          <WebSocketProvider>
            <TestComponent />
          </WebSocketProvider>
        </AuthProvider>
      );

      // Simulate token update
      await act(async () => {
        mockLocalStorage.setItem('jwt_token', 'new-jwt-token');
        // Trigger a storage event to simulate token change
        window.dispatchEvent(new StorageEvent('storage', {
          key: 'jwt_token',
          newValue: 'new-jwt-token'
        }));
      });

      // The ticket provider should be updated through the auth context
      // This is verified through the integration rather than direct calls
      expect(mockUnifiedAuthService.getWebSocketAuthConfig).toHaveBeenCalled();
    });

    it('should clear ticket cache on logout', async () => {
      const { getByTestId } = render(
        <AuthProvider>
          <WebSocketProvider>
            <TestComponent />
          </WebSocketProvider>
        </AuthProvider>
      );

      // Simulate logout
      await act(async () => {
        mockLocalStorage.removeItem('jwt_token');
        // Trigger auth state change
        window.dispatchEvent(new StorageEvent('storage', {
          key: 'jwt_token',
          newValue: null
        }));
      });

      // Ticket cache should be cleared during logout flow
      expect(mockUnifiedAuthService.clearTicketCache).toHaveBeenCalled();
    });
  });

  describe('Error Handling', () => {
    it('should handle ticket acquisition errors gracefully', async () => {
      mockUnifiedAuthService.getWebSocketAuthConfig.mockReturnValue({
        token: 'test-jwt-token',
        refreshToken: jest.fn().mockResolvedValue('refreshed-jwt-token'),
        getTicket: jest.fn().mockRejectedValue(new Error('Network error')),
        useTicketAuth: true
      });
      
      mockLocalStorage.setItem('jwt_token', 'test-jwt-token');
      
      const { getByTestId } = render(
        <AuthProvider>
          <WebSocketProvider>
            <TestComponent />
          </WebSocketProvider>
        </AuthProvider>
      );

      await waitFor(() => {
        expect(getByTestId('auth-initialized').textContent).toBe('true');
      });

      // Should still attempt connection with error handling
      expect(mockWebSocketService.connect).toHaveBeenCalled();
    });

    it('should handle WebSocket connection errors with ticket auth', async () => {
      let onErrorCallback: ((error: any) => void) | undefined;
      
      mockWebSocketService.connect.mockImplementation((url, options) => {
        onErrorCallback = options?.onError;
      });
      
      mockLocalStorage.setItem('jwt_token', 'test-jwt-token');
      
      render(
        <AuthProvider>
          <WebSocketProvider>
            <TestComponent />
          </WebSocketProvider>
        </AuthProvider>
      );

      await waitFor(() => {
        expect(mockWebSocketService.connect).toHaveBeenCalled();
      });

      // Simulate WebSocket auth error
      if (onErrorCallback) {
        act(() => {
          onErrorCallback({
            type: 'auth',
            code: 1008,
            message: 'Ticket expired',
            recoverable: true
          });
        });
      }

      // Should clear ticket cache on auth error
      expect(mockUnifiedAuthService.clearTicketCache).toHaveBeenCalled();
    });
  });

  describe('Ticket Refresh Scenarios', () => {
    it('should handle ticket expiry and refresh', async () => {
      let getTicketCallback: (() => Promise<any>) | undefined;
      
      mockWebSocketService.connect.mockImplementation((url, options) => {
        getTicketCallback = options?.getTicket;
      });
      
      mockLocalStorage.setItem('jwt_token', 'test-jwt-token');
      
      render(
        <AuthProvider>
          <WebSocketProvider>
            <TestComponent />
          </WebSocketProvider>
        </AuthProvider>
      );

      await waitFor(() => {
        expect(mockWebSocketService.connect).toHaveBeenCalled();
      });

      // Simulate ticket acquisition through WebSocket service
      if (getTicketCallback) {
        const ticketResult = await getTicketCallback();
        expect(ticketResult.success).toBe(true);
        expect(ticketResult.ticket?.ticket).toBe('test-ticket-123');
      }
    });

    it('should handle ticket cache clearing during connection', async () => {
      let clearCacheCallback: (() => void) | undefined;
      
      mockWebSocketService.connect.mockImplementation((url, options) => {
        clearCacheCallback = options?.clearTicketCache;
      });
      
      mockLocalStorage.setItem('jwt_token', 'test-jwt-token');
      
      render(
        <AuthProvider>
          <WebSocketProvider>
            <TestComponent />
          </WebSocketProvider>
        </AuthProvider>
      );

      await waitFor(() => {
        expect(mockWebSocketService.connect).toHaveBeenCalled();
      });

      // Simulate cache clearing through WebSocket service
      if (clearCacheCallback) {
        clearCacheCallback();
        expect(mockUnifiedAuthService.clearTicketCache).toHaveBeenCalled();
      }
    });
  });

  describe('Development vs Production Behavior', () => {
    it('should handle development mode without authentication', async () => {
      // No JWT token in development
      mockUnifiedAuthService.getWebSocketAuthConfig.mockReturnValue({
        token: null,
        refreshToken: jest.fn().mockResolvedValue(null),
        getTicket: jest.fn().mockResolvedValue({
          success: false,
          error: 'No authentication token available',
          recoverable: false
        }),
        useTicketAuth: false
      });
      
      render(
        <AuthProvider>
          <WebSocketProvider>
            <TestComponent />
          </WebSocketProvider>
        </AuthProvider>
      );

      await waitFor(() => {
        expect(mockWebSocketService.connect).toHaveBeenCalledWith(
          'wss://api-staging.netrasystems.ai/ws',
          expect.objectContaining({
            token: undefined, // No token in development
            useTicketAuth: false
          })
        );
      });
    });

    it('should require authentication in production mode', async () => {
      // Simulate production behavior
      process.env.NODE_ENV = 'production';
      
      mockUnifiedAuthService.getWebSocketAuthConfig.mockReturnValue({
        token: 'prod-jwt-token',
        refreshToken: jest.fn().mockResolvedValue('refreshed-prod-token'),
        getTicket: jest.fn().mockResolvedValue({
          success: true,
          ticket: {
            ticket: 'prod-ticket-456',
            expires_at: Date.now() + 300000,
            created_at: Date.now(),
            websocket_url: 'wss://api.netrasystems.ai/ws?ticket=prod-ticket-456'
          }
        }),
        useTicketAuth: true
      });
      
      mockLocalStorage.setItem('jwt_token', 'prod-jwt-token');
      
      render(
        <AuthProvider>
          <WebSocketProvider>
            <TestComponent />
          </WebSocketProvider>
        </AuthProvider>
      );

      await waitFor(() => {
        expect(mockWebSocketService.connect).toHaveBeenCalledWith(
          'wss://api-staging.netrasystems.ai/ws',
          expect.objectContaining({
            token: 'prod-jwt-token',
            useTicketAuth: true
          })
        );
      });
      
      // Reset NODE_ENV
      delete process.env.NODE_ENV;
    });
  });

  describe('Performance and Memory Management', () => {
    it('should not create excessive connections during auth updates', async () => {
      mockLocalStorage.setItem('jwt_token', 'test-jwt-token');
      
      render(
        <AuthProvider>
          <WebSocketProvider>
            <TestComponent />
          </WebSocketProvider>
        </AuthProvider>
      );

      // Simulate rapid auth updates
      for (let i = 0; i < 5; i++) {
        await act(async () => {
          mockLocalStorage.setItem('jwt_token', `token-${i}`);
          window.dispatchEvent(new StorageEvent('storage', {
            key: 'jwt_token',
            newValue: `token-${i}`
          }));
        });
      }

      // Connection should be managed efficiently, not called excessively
      expect(mockWebSocketService.connect.mock.calls.length).toBeLessThan(10);
    });

    it('should clean up resources properly', async () => {
      const { unmount } = render(
        <AuthProvider>
          <WebSocketProvider>
            <TestComponent />
          </WebSocketProvider>
        </AuthProvider>
      );

      // Unmount components
      unmount();

      // Should not cause memory leaks or errors
      expect(() => {
        // Simulate some cleanup scenarios
        ticketAuthProvider.clearTicketCache();
      }).not.toThrow();
    });
  });
});