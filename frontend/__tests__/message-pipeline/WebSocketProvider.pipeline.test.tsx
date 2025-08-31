/**
 * Comprehensive WebSocketProvider Pipeline Tests
 * 
 * Tests the complete WebSocket integration pipeline including:
 * 1. Connection establishment and lifecycle management
 * 2. Authentication and token management
 * 3. Message sending and receiving
 * 4. Reconciliation service integration
 * 5. Error handling and reconnection
 * 6. Context provider functionality
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
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

// Mock all dependencies
jest.mock('@/services/webSocketService');
jest.mock('@/services/reconciliation');
jest.mock('@/lib/unified-auth-service');
jest.mock('@/config');
jest.mock('@/lib/logger');

// Test component to consume WebSocket context
const TestConsumer: React.FC<{ onContextUpdate?: (context: any) => void }> = ({ 
  onContextUpdate 
}) => {
  const context = useWebSocketContext();
  
  React.useEffect(() => {
    onContextUpdate?.(context);
  }, [context, onContextUpdate]);

  return (
    <div data-testid="websocket-consumer">
      <div data-testid="status">{context.status}</div>
      <div data-testid="message-count">{context.messages.length}</div>
      <button 
        data-testid="send-message"
        onClick={() => context.sendMessage({ type: 'test', payload: { data: 'test' } })}
      >
        Send Message
      </button>
      <button
        data-testid="send-optimistic"
        onClick={() => context.sendOptimisticMessage('Optimistic message', 'user')}
      >
        Send Optimistic
      </button>
    </div>
  );
};

// Auth provider wrapper for testing
const AuthProviderWrapper: React.FC<{ 
  token?: string | null;
  children: React.ReactNode;
}> = ({ token = 'test-token-123', children }) => {
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

describe('WebSocketProvider Pipeline Tests', () => {
  setupAntiHang();
    jest.setTimeout(10000);
  const mockWebSocketService = {
    onStatusChange: null,
    onMessage: null,
    connect: jest.fn(),
    disconnect: jest.fn(),
    sendMessage: jest.fn(),
    updateToken: jest.fn().mockResolvedValue(undefined),
    getSecureUrl: jest.fn((url: string) => `${url}?jwt=test-token-123`)
  };

  const mockReconciliationService = {
    processConfirmation: jest.fn((msg) => msg),
    addOptimisticMessage: jest.fn((msg) => ({ ...msg, tempId: 'temp-123' })),
    getStats: jest.fn(() => ({ confirmed: 0, failed: 0, pending: 0 }))
  };

  const mockUnifiedAuthService = {
    getWebSocketAuthConfig: jest.fn(() => ({
      refreshToken: jest.fn().mockResolvedValue('refreshed-token-456')
    }))
  };

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Setup default mocks
    (webSocketService as jest.Mocked<typeof webSocketService>) = mockWebSocketService as any;
    (reconciliationService as jest.Mocked<typeof reconciliationService>) = mockReconciliationService as any;
    (unifiedAuthService as jest.Mocked<typeof unifiedAuthService>) = mockUnifiedAuthService as any;
    
    (appConfig as jest.Mocked<typeof appConfig>) = {
      wsUrl: 'ws://localhost:8000/ws',
      apiUrl: 'http://localhost:8000/api'
    } as any;

    // Reset timers
    jest.useFakeTimers();
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

  describe('Connection Establishment Pipeline', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should establish WebSocket connection on mount with token', async () => {
      const contextUpdates: any[] = [];
      
      render(
        <AuthProviderWrapper token="test-token-123">
          <WebSocketProvider>
            <TestConsumer onContextUpdate={(ctx) => contextUpdates.push(ctx)} />
          </WebSocketProvider>
        </AuthProviderWrapper>
      );

      await waitFor(() => {
        expect(mockWebSocketService.connect).toHaveBeenCalledWith(
          'ws://localhost:8000/ws?jwt=test-token-123',
          expect.objectContaining({
            token: 'test-token-123',
            refreshToken: expect.any(Function),
            onOpen: expect.any(Function),
            onError: expect.any(Function),
            onReconnect: expect.any(Function),
            heartbeatInterval: 30000,
            rateLimit: {
              messages: 60,
              window: 60000
            }
          })
        );
      });

      expect(mockWebSocketService.onStatusChange).toBeDefined();
      expect(mockWebSocketService.onMessage).toBeDefined();
    });

    it('should not connect without token', async () => {
      render(
        <AuthProviderWrapper token={null}>
          <WebSocketProvider>
            <TestConsumer />
          </WebSocketProvider>
        </AuthProviderWrapper>
      );

      await waitFor(() => {
        expect(mockWebSocketService.connect).not.toHaveBeenCalled();
      });
    });

    it('should use fallback WebSocket URL when wsUrl is not configured', async () => {
      (appConfig as any).wsUrl = undefined;
      
      render(
        <AuthProviderWrapper>
          <WebSocketProvider>
            <TestConsumer />
          </WebSocketProvider>
        </AuthProviderWrapper>
      );

      await waitFor(() => {
        expect(mockWebSocketService.getSecureUrl).toHaveBeenCalledWith(
          'ws://localhost:8000/api/ws'
        );
      });
    });

    it('should handle secure URL generation correctly', async () => {
      mockWebSocketService.getSecureUrl.mockReturnValue('wss://secure.example.com/ws?jwt=***');
      
      render(
        <AuthProviderWrapper>
          <WebSocketProvider>
            <TestConsumer />
          </WebSocketProvider>
        </AuthProviderWrapper>
      );

      await waitFor(() => {
        expect(mockWebSocketService.connect).toHaveBeenCalledWith(
          'wss://secure.example.com/ws?jwt=***',
          expect.any(Object)
        );
      });
    });
  });

  describe('Authentication and Token Management Pipeline', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should update WebSocket connection when token changes', async () => {
      const { rerender } = render(
        <AuthProviderWrapper token="initial-token">
          <WebSocketProvider>
            <TestConsumer />
          </WebSocketProvider>
        </AuthProviderWrapper>
      );

      await waitFor(() => {
        expect(mockWebSocketService.connect).toHaveBeenCalled();
      });

      // Change token
      rerender(
        <AuthProviderWrapper token="updated-token">
          <WebSocketProvider>
            <TestConsumer />
          </WebSocketProvider>
        </AuthProviderWrapper>
      );

      await waitFor(() => {
        expect(mockWebSocketService.updateToken).toHaveBeenCalledWith('updated-token');
      });
    });

    it('should handle token refresh correctly', async () => {
      render(
        <AuthProviderWrapper>
          <WebSocketProvider>
            <TestConsumer />
          </WebSocketProvider>
        </AuthProviderWrapper>
      );

      await waitFor(() => {
        expect(mockWebSocketService.connect).toHaveBeenCalled();
      });

      // Get the connect call arguments
      const connectCall = mockWebSocketService.connect.mock.calls[0];
      const connectOptions = connectCall[1];
      
      // Call the refreshToken function
      const refreshedToken = await connectOptions.refreshToken();
      
      expect(mockUnifiedAuthService.getWebSocketAuthConfig).toHaveBeenCalled();
      expect(refreshedToken).toBe('refreshed-token-456');
    });

    it('should handle token refresh failure gracefully', async () => {
      mockUnifiedAuthService.getWebSocketAuthConfig.mockImplementation(() => ({
        refreshToken: jest.fn().mockRejectedValue(new Error('Refresh failed'))
      }));

      render(
        <AuthProviderWrapper>
          <WebSocketProvider>
            <TestConsumer />
          </WebSocketProvider>
        </AuthProviderWrapper>
      );

      await waitFor(() => {
        expect(mockWebSocketService.connect).toHaveBeenCalled();
      });

      const connectCall = mockWebSocketService.connect.mock.calls[0];
      const connectOptions = connectCall[1];
      
      const refreshedToken = await connectOptions.refreshToken();
      
      expect(refreshedToken).toBeNull();
      expect(logger.error).toHaveBeenCalledWith(
        'Token refresh failed in WebSocketProvider',
        expect.any(Error),
        expect.any(Object)
      );
    });

    it('should handle token refresh returning null', async () => {
      mockUnifiedAuthService.getWebSocketAuthConfig.mockImplementation(() => ({
        refreshToken: jest.fn().mockResolvedValue(null)
      }));

      render(
        <AuthProviderWrapper>
          <WebSocketProvider>
            <TestConsumer />
          </WebSocketProvider>
        </AuthProviderWrapper>
      );

      await waitFor(() => {
        expect(mockWebSocketService.connect).toHaveBeenCalled();
      });

      const connectCall = mockWebSocketService.connect.mock.calls[0];
      const connectOptions = connectCall[1];
      
      const refreshedToken = await connectOptions.refreshToken();
      
      expect(refreshedToken).toBeNull();
    });
  });

  describe('Message Handling Pipeline', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should process incoming messages through reconciliation service', async () => {
      const contextUpdates: any[] = [];
      
      render(
        <AuthProviderWrapper>
          <WebSocketProvider>
            <TestConsumer onContextUpdate={(ctx) => contextUpdates.push(ctx)} />
          </WebSocketProvider>
        </AuthProviderWrapper>
      );

      await waitFor(() => {
        expect(mockWebSocketService.onMessage).toBeDefined();
      });

      const testMessage = {
        type: 'agent_response',
        payload: {
          message_id: 'msg-123',
          content: 'Test response',
          role: 'assistant'
        }
      };

      // Simulate incoming message
      act(() => {
        mockWebSocketService.onMessage!(testMessage);
      });

      expect(mockReconciliationService.processConfirmation).toHaveBeenCalledWith(testMessage);
      
      await waitFor(() => {
        const latestContext = contextUpdates[contextUpdates.length - 1];
        expect(latestContext.messages).toContainEqual(testMessage);
      });
    });

    it('should prevent duplicate messages', async () => {
      const contextUpdates: any[] = [];
      
      render(
        <AuthProviderWrapper>
          <WebSocketProvider>
            <TestConsumer onContextUpdate={(ctx) => contextUpdates.push(ctx)} />
          </WebSocketProvider>
        </AuthProviderWrapper>
      );

      await waitFor(() => {
        expect(mockWebSocketService.onMessage).toBeDefined();
      });

      const testMessage = {
        type: 'agent_response',
        payload: { message_id: 'duplicate-msg-123', content: 'Duplicate message' }
      };

      // Send same message twice
      act(() => {
        mockWebSocketService.onMessage!(testMessage);
        mockWebSocketService.onMessage!(testMessage);
      });

      await waitFor(() => {
        const latestContext = contextUpdates[contextUpdates.length - 1];
        const duplicateMessages = latestContext.messages.filter(
          (msg: any) => msg.payload?.message_id === 'duplicate-msg-123'
        );
        expect(duplicateMessages).toHaveLength(1);
      });
    });

    it('should limit message history to prevent memory bloat', async () => {
      const contextUpdates: any[] = [];
      
      render(
        <AuthProviderWrapper>
          <WebSocketProvider>
            <TestConsumer onContextUpdate={(ctx) => contextUpdates.push(ctx)} />
          </WebSocketProvider>
        </AuthProviderWrapper>
      );

      await waitFor(() => {
        expect(mockWebSocketService.onMessage).toBeDefined();
      });

      // Send 150 messages (more than the 100 limit)
      for (let i = 0; i < 150; i++) {
        const message = {
          type: 'test_message',
          payload: { message_id: `msg-${i}`, content: `Message ${i}` }
        };
        
        act(() => {
          mockWebSocketService.onMessage!(message);
        });
      }

      await waitFor(() => {
        const latestContext = contextUpdates[contextUpdates.length - 1];
        expect(latestContext.messages.length).toBeLessThanOrEqual(100);
        
        // Should keep the most recent messages
        const lastMessage = latestContext.messages[latestContext.messages.length - 1];
        expect(lastMessage.payload.message_id).toBe('msg-149');
      });
    });

    it('should handle messages without message_id', async () => {
      const contextUpdates: any[] = [];
      
      render(
        <AuthProviderWrapper>
          <WebSocketProvider>
            <TestConsumer onContextUpdate={(ctx) => contextUpdates.push(ctx)} />
          </WebSocketProvider>
        </AuthProviderWrapper>
      );

      await waitFor(() => {
        expect(mockWebSocketService.onMessage).toBeDefined();
      });

      const messageWithoutId = {
        type: 'status_update',
        payload: { status: 'processing' }
      };

      act(() => {
        mockWebSocketService.onMessage!(messageWithoutId);
      });

      await waitFor(() => {
        const latestContext = contextUpdates[contextUpdates.length - 1];
        expect(latestContext.messages).toContainEqual(messageWithoutId);
      });
    });
  });

  describe('Status Change Pipeline', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should update context status when WebSocket status changes', async () => {
      const contextUpdates: any[] = [];
      
      render(
        <AuthProviderWrapper>
          <WebSocketProvider>
            <TestConsumer onContextUpdate={(ctx) => contextUpdates.push(ctx)} />
          </WebSocketProvider>
        </AuthProviderWrapper>
      );

      await waitFor(() => {
        expect(mockWebSocketService.onStatusChange).toBeDefined();
      });

      // Simulate status change
      act(() => {
        mockWebSocketService.onStatusChange!('OPEN');
      });

      await waitFor(() => {
        const latestContext = contextUpdates[contextUpdates.length - 1];
        expect(latestContext.status).toBe('OPEN');
      });

      // Another status change
      act(() => {
        mockWebSocketService.onStatusChange!('CLOSED');
      });

      await waitFor(() => {
        const latestContext = contextUpdates[contextUpdates.length - 1];
        expect(latestContext.status).toBe('CLOSED');
      });
    });
  });

  describe('Error Handling Pipeline', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle connection errors appropriately', async () => {
      render(
        <AuthProviderWrapper>
          <WebSocketProvider>
            <TestConsumer />
          </WebSocketProvider>
        </AuthProviderWrapper>
      );

      await waitFor(() => {
        expect(mockWebSocketService.connect).toHaveBeenCalled();
      });

      const connectCall = mockWebSocketService.connect.mock.calls[0];
      const connectOptions = connectCall[1];
      
      // Test different error types
      const authError = {
        type: 'auth',
        code: 1008,
        message: 'Security violation: deprecated authentication method',
        recoverable: false
      };

      act(() => {
        connectOptions.onError(authError);
      });

      expect(logger.error).toHaveBeenCalledWith(
        'WebSocket connection error',
        undefined,
        expect.objectContaining({
          component: 'WebSocketProvider',
          action: 'connection_error'
        })
      );
    });

    it('should handle authentication errors correctly', async () => {
      render(
        <AuthProviderWrapper>
          <WebSocketProvider>
            <TestConsumer />
          </WebSocketProvider>
        </AuthProviderWrapper>
      );

      await waitFor(() => {
        expect(mockWebSocketService.connect).toHaveBeenCalled();
      });

      const connectCall = mockWebSocketService.connect.mock.calls[0];
      const connectOptions = connectCall[1];
      
      const authError = {
        type: 'auth',
        code: 1008,
        message: 'Invalid token',
        recoverable: true
      };

      act(() => {
        connectOptions.onError(authError);
      });

      expect(logger.warn).toHaveBeenCalledWith(
        'WebSocket authentication failed - token may be expired or invalid'
      );
    });

    it('should handle token update failures', async () => {
      mockWebSocketService.updateToken.mockRejectedValue(new Error('Token update failed'));
      
      const { rerender } = render(
        <AuthProviderWrapper token="initial-token">
          <WebSocketProvider>
            <TestConsumer />
          </WebSocketProvider>
        </AuthProviderWrapper>
      );

      await waitFor(() => {
        expect(mockWebSocketService.connect).toHaveBeenCalled();
      });

      // Change token to trigger update
      rerender(
        <AuthProviderWrapper token="updated-token">
          <WebSocketProvider>
            <TestConsumer />
          </WebSocketProvider>
        </AuthProviderWrapper>
      );

      await waitFor(() => {
        expect(logger.error).toHaveBeenCalledWith(
          'Failed to update WebSocket token',
          expect.any(Error),
          expect.objectContaining({
            component: 'WebSocketProvider',
            action: 'token_sync_failed'
          })
        );
      });
    });
  });

  describe('Context API Pipeline', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should provide sendMessage function that calls webSocketService', async () => {
      render(
        <AuthProviderWrapper>
          <WebSocketProvider>
            <TestConsumer />
          </WebSocketProvider>
        </AuthProviderWrapper>
      );

      const sendButton = screen.getByTestId('send-message');
      
      act(() => {
        sendButton.click();
      });

      expect(mockWebSocketService.sendMessage).toHaveBeenCalledWith({
        type: 'test',
        payload: { data: 'test' }
      });
    });

    it('should provide sendOptimisticMessage function', async () => {
      render(
        <AuthProviderWrapper>
          <WebSocketProvider>
            <TestConsumer />
          </WebSocketProvider>
        </AuthProviderWrapper>
      );

      const optimisticButton = screen.getByTestId('send-optimistic');
      
      act(() => {
        optimisticButton.click();
      });

      expect(mockReconciliationService.addOptimisticMessage).toHaveBeenCalledWith({
        id: expect.stringMatching(/^temp_/),
        content: 'Optimistic message',
        role: 'user',
        timestamp: expect.any(Number)
      });

      expect(mockWebSocketService.sendMessage).toHaveBeenCalledWith({
        type: 'user_message',
        payload: {
          content: 'Optimistic message',
          timestamp: expect.any(String),
          correlation_id: 'temp-123'
        }
      });
    });

    it('should provide reconciliation stats', async () => {
      const contextUpdates: any[] = [];
      
      render(
        <AuthProviderWrapper>
          <WebSocketProvider>
            <TestConsumer onContextUpdate={(ctx) => contextUpdates.push(ctx)} />
          </WebSocketProvider>
        </AuthProviderWrapper>
      );

      await waitFor(() => {
        const latestContext = contextUpdates[contextUpdates.length - 1];
        expect(latestContext.reconciliationStats).toEqual({
          confirmed: 0,
          failed: 0,
          pending: 0
        });
      });
    });

    it('should throw error when used outside provider', () => {
      const TestComponent = () => {
        useWebSocketContext();
        return null;
      };

      expect(() => {
        render(<TestComponent />);
      }).toThrow('useWebSocketContext must be used within a WebSocketProvider');
    });
  });

  describe('Cleanup and Lifecycle Pipeline', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should cleanup connections on unmount', async () => {
      const { unmount } = render(
        <AuthProviderWrapper>
          <WebSocketProvider>
            <TestConsumer />
          </WebSocketProvider>
        </AuthProviderWrapper>
      );

      await waitFor(() => {
        expect(mockWebSocketService.connect).toHaveBeenCalled();
      });

      unmount();

      await waitFor(() => {
        expect(mockWebSocketService.onStatusChange).toBeNull();
        expect(mockWebSocketService.onMessage).toBeNull();
        expect(mockWebSocketService.disconnect).toHaveBeenCalled();
      });
    });

    it('should handle rapid mount/unmount cycles', async () => {
      const { unmount: unmount1 } = render(
        <AuthProviderWrapper>
          <WebSocketProvider>
            <TestConsumer />
          </WebSocketProvider>
        </AuthProviderWrapper>
      );

      const { unmount: unmount2 } = render(
        <AuthProviderWrapper>
          <WebSocketProvider>
            <TestConsumer />
          </WebSocketProvider>
        </AuthProviderWrapper>
      );

      unmount1();
      unmount2();

      // Should not throw errors
      expect(mockWebSocketService.disconnect).toHaveBeenCalledTimes(2);
    });
  });

  describe('Reconnection Pipeline', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle reconnection events', async () => {
      render(
        <AuthProviderWrapper>
          <WebSocketProvider>
            <TestConsumer />
          </WebSocketProvider>
        </AuthProviderWrapper>
      );

      await waitFor(() => {
        expect(mockWebSocketService.connect).toHaveBeenCalled();
      });

      const connectCall = mockWebSocketService.connect.mock.calls[0];
      const connectOptions = connectCall[1];
      
      act(() => {
        connectOptions.onReconnect();
      });

      // Should not throw error and should log reconnection
      expect(() => {
        connectOptions.onReconnect();
      }).not.toThrow();
    });

    it('should handle connection opening events', async () => {
      render(
        <AuthProviderWrapper>
          <WebSocketProvider>
            <TestConsumer />
          </WebSocketProvider>
        </AuthProviderWrapper>
      );

      await waitFor(() => {
        expect(mockWebSocketService.connect).toHaveBeenCalled();
      });

      const connectCall = mockWebSocketService.connect.mock.calls[0];
      const connectOptions = connectCall[1];
      
      act(() => {
        connectOptions.onOpen();
      });

      // Should not throw error
      expect(() => {
        connectOptions.onOpen();
      }).not.toThrow();
    });
  });

  describe('Configuration and Options Pipeline', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should pass correct connection options to webSocketService', async () => {
      render(
        <AuthProviderWrapper>
          <WebSocketProvider>
            <TestConsumer />
          </WebSocketProvider>
        </AuthProviderWrapper>
      );

      await waitFor(() => {
        expect(mockWebSocketService.connect).toHaveBeenCalledWith(
          expect.any(String),
          expect.objectContaining({
            token: 'test-token-123',
            refreshToken: expect.any(Function),
            onOpen: expect.any(Function),
            onError: expect.any(Function),
            onReconnect: expect.any(Function),
            heartbeatInterval: 30000,
            rateLimit: {
              messages: 60,
              window: 60000
            }
          })
        );
      });
    });
  });
});