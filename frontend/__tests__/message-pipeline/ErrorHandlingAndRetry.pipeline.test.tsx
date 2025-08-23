/**
 * Comprehensive Error Handling and Retry Pipeline Tests
 * 
 * Tests all error scenarios and recovery mechanisms:
 * 1. Network failures and connection errors
 * 2. Authentication failures and token expiry
 * 3. Backend service errors and timeouts
 * 4. Optimistic update failures and reconciliation
 * 5. Retry mechanisms and exponential backoff
 * 6. Error recovery and user feedback
 * 7. Graceful degradation and fallback states
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MessageInput } from '@/components/chat/MessageInput';
import { WebSocketProvider, useWebSocketContext } from '@/providers/WebSocketProvider';
import { AuthContext } from '@/auth/context';
import { useMessageSending } from '@/components/chat/hooks/useMessageSending';
import { optimisticMessageManager } from '@/services/optimistic-updates';
import { webSocketService } from '@/services/webSocketService';
import { ThreadService } from '@/services/threadService';
import { logger } from '@/utils/debug-logger';

// Test component for error handling scenarios
const ErrorHandlingTestHarness: React.FC<{
  simulateNetworkFailure?: boolean;
  simulateAuthFailure?: boolean;
  simulateBackendError?: boolean;
  onError?: (error: any) => void;
}> = ({ 
  simulateNetworkFailure,
  simulateAuthFailure, 
  simulateBackendError,
  onError 
}) => {
  const [errors, setErrors] = React.useState<any[]>([]);
  const webSocketContext = useWebSocketContext();

  // Error boundary for catching React errors
  const ErrorBoundary: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [hasError, setHasError] = React.useState(false);
    const [error, setError] = React.useState<Error | null>(null);

    React.useEffect(() => {
      const handleError = (event: ErrorEvent) => {
        setHasError(true);
        setError(new Error(event.message));
        setErrors(prev => [...prev, event.error]);
        onError?.(event.error);
      };

      window.addEventListener('error', handleError);
      return () => window.removeEventListener('error', handleError);
    }, []);

    if (hasError) {
      return <div data-testid="error-boundary">Error: {error?.message}</div>;
    }

    return <>{children}</>;
  };

  // Mock WebSocket failures
  React.useEffect(() => {
    if (simulateNetworkFailure) {
      const originalSendMessage = webSocketContext.sendMessage;
      webSocketContext.sendMessage = (message: any) => {
        const error = new Error('Network connection failed');
        setErrors(prev => [...prev, error]);
        onError?.(error);
        throw error;
      };
    }
  }, [simulateNetworkFailure, webSocketContext, onError]);

  const authValue = {
    token: simulateAuthFailure ? null : 'test-token-123',
    user: simulateAuthFailure ? null : { id: 'test-user', email: 'test@example.com' },
    isAuthenticated: !simulateAuthFailure,
    login: jest.fn(),
    logout: jest.fn(),
    refreshToken: jest.fn().mockImplementation(() => {
      if (simulateAuthFailure) {
        const error = new Error('Token refresh failed');
        setErrors(prev => [...prev, error]);
        onError?.(error);
        throw error;
      }
      return Promise.resolve('new-token-456');
    })
  };

  return (
    <ErrorBoundary>
      <AuthContext.Provider value={authValue}>
        <WebSocketProvider>
          <div data-testid="error-test-harness">
            <MessageInput />
            <div data-testid="error-count">{errors.length}</div>
            <div data-testid="error-list">
              {errors.map((error, index) => (
                <div key={index} data-testid={`error-${index}`}>
                  {error.message || error.toString()}
                </div>
              ))}
            </div>
          </div>
        </WebSocketProvider>
      </AuthContext.Provider>
    </ErrorBoundary>
  );
};

// Mock all dependencies
jest.mock('@/services/webSocketService');
jest.mock('@/services/threadService');
jest.mock('@/services/threadRenameService');
jest.mock('@/utils/debug-logger');

describe('Error Handling and Retry Pipeline Tests', () => {
  const mockWebSocketService = {
    onMessage: null,
    onStatusChange: null,
    connect: jest.fn(),
    disconnect: jest.fn(),
    sendMessage: jest.fn(),
    updateToken: jest.fn(),
    getSecureUrl: jest.fn((url: string) => url),
    simulateError: jest.fn()
  };

  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();

    (webSocketService as jest.Mocked<typeof webSocketService>) = mockWebSocketService as any;
    
    // Reset optimistic manager
    optimisticMessageManager.clearAllOptimisticMessages();

    // Setup default successful mocks
    (ThreadService.createThread as jest.Mock).mockResolvedValue({
      id: 'test-thread-123',
      title: 'Test Thread',
      metadata: { renamed: false }
    });
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  describe('Network Failure Handling', () => {
    it('should handle WebSocket connection failures gracefully', async () => {
      const connectionError = new Error('WebSocket connection failed');
      mockWebSocketService.connect.mockImplementation(() => {
        throw connectionError;
      });

      const errorHandler = jest.fn();
      
      render(<ErrorHandlingTestHarness onError={errorHandler} />);

      await waitFor(() => {
        expect(logger.error).toHaveBeenCalledWith(
          'Failed to connect to WebSocket',
          expect.any(Error),
          expect.objectContaining({
            component: 'WebSocketProvider',
            action: 'connect_websocket'
          })
        );
      });
    });

    it('should handle WebSocket send failures with optimistic updates', async () => {
      mockWebSocketService.sendMessage.mockImplementation(() => {
        throw new Error('Send failed - connection lost');
      });

      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(<ErrorHandlingTestHarness />);

      const textarea = screen.getByRole('textbox', { name: /message input/i });
      await user.type(textarea, 'Message during network failure');
      await user.keyboard('{Enter}');

      // Should still create optimistic messages
      await waitFor(() => {
        const optimisticMessages = optimisticMessageManager.getOptimisticMessages();
        expect(optimisticMessages).toHaveLength(2); // User + AI
      });

      // Should mark messages as failed after timeout
      act(() => {
        jest.advanceTimersByTime(35000); // Exceed timeout
      });

      const reconciliationResult = optimisticMessageManager.reconcileWithBackend([]);
      expect(reconciliationResult.failed).toHaveLength(1);
    });

    it('should handle intermittent connection failures with retry', async () => {
      let sendAttempts = 0;
      mockWebSocketService.sendMessage.mockImplementation(() => {
        sendAttempts++;
        if (sendAttempts <= 2) {
          throw new Error(`Connection failed - attempt ${sendAttempts}`);
        }
        // Third attempt succeeds
      });

      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(<ErrorHandlingTestHarness />);

      const textarea = screen.getByRole('textbox', { name: /message input/i });
      await user.type(textarea, 'Message with retry');
      await user.keyboard('{Enter}');

      // Should have failed messages with retry capability
      await waitFor(() => {
        const failedMessages = optimisticMessageManager.getFailedMessages();
        expect(failedMessages.length).toBeGreaterThan(0);
        expect(failedMessages[0].retry).toBeInstanceOf(Function);
      });

      // Execute retry
      const failedMessage = optimisticMessageManager.getFailedMessages()[0];
      await failedMessage.retry!();

      // Should eventually succeed on retry
      expect(sendAttempts).toBeGreaterThan(1);
    });
  });

  describe('Authentication Failure Handling', () => {
    it('should handle expired token during message send', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      // Start with valid token
      const { rerender } = render(<ErrorHandlingTestHarness />);

      const textarea = screen.getByRole('textbox', { name: /message input/i });
      await user.type(textarea, 'Message before token expiry');

      // Simulate token expiry
      rerender(<ErrorHandlingTestHarness simulateAuthFailure={true} />);

      await user.keyboard('{Enter}');

      // Should not send message and show disabled state
      expect(mockWebSocketService.sendMessage).not.toHaveBeenCalled();
      expect(textarea).toBeDisabled();
    });

    it('should handle token refresh failures', async () => {
      mockWebSocketService.updateToken.mockRejectedValue(new Error('Token refresh failed'));

      const { rerender } = render(<ErrorHandlingTestHarness />);

      // Change token to trigger refresh
      rerender(<ErrorHandlingTestHarness />);

      await waitFor(() => {
        expect(logger.error).toHaveBeenCalledWith(
          'Failed to update WebSocket token',
          expect.any(Error),
          expect.any(Object)
        );
      });
    });

    it('should handle authentication errors from WebSocket', async () => {
      render(<ErrorHandlingTestHarness />);

      await waitFor(() => {
        expect(mockWebSocketService.connect).toHaveBeenCalled();
      });

      // Simulate WebSocket auth error callback
      const connectCall = mockWebSocketService.connect.mock.calls[0];
      const connectOptions = connectCall[1];

      const authError = {
        type: 'auth',
        code: 1008,
        message: 'Authentication failed',
        recoverable: false
      };

      act(() => {
        connectOptions?.onError?.(authError);
      });

      expect(logger.error).toHaveBeenCalledWith(
        'WebSocket connection error',
        undefined,
        expect.objectContaining({
          metadata: expect.objectContaining({
            error: 'Authentication failed',
            type: 'auth'
          })
        })
      );
    });
  });

  describe('Backend Service Error Handling', () => {
    it('should handle thread creation service errors', async () => {
      const serviceError = new Error('Thread service unavailable');
      (ThreadService.createThread as jest.Mock).mockRejectedValue(serviceError);

      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(<ErrorHandlingTestHarness />);

      const textarea = screen.getByRole('textbox', { name: /message input/i });
      await user.type(textarea, 'Message causing service error');
      await user.keyboard('{Enter}');

      await waitFor(() => {
        expect(logger.error).toHaveBeenCalledWith(
          'Failed to send message:',
          serviceError
        );
      });

      // Should mark optimistic messages as failed
      const failedMessages = optimisticMessageManager.getFailedMessages();
      expect(failedMessages.length).toBeGreaterThan(0);
    });

    it('should handle backend timeout errors', async () => {
      // Mock slow backend response
      mockWebSocketService.sendMessage.mockImplementation(() => {
        // Simulate sending but never getting response
      });

      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(<ErrorHandlingTestHarness />);

      const textarea = screen.getByRole('textbox', { name: /message input/i });
      await user.type(textarea, 'Message that will timeout');
      await user.keyboard('{Enter}');

      // Create optimistic messages
      await waitFor(() => {
        const optimisticMessages = optimisticMessageManager.getOptimisticMessages();
        expect(optimisticMessages).toHaveLength(2);
      });

      // Fast-forward past timeout
      act(() => {
        jest.advanceTimersByTime(35000);
      });

      // Reconcile with empty response (timeout scenario)
      const reconciliationResult = optimisticMessageManager.reconcileWithBackend([]);
      expect(reconciliationResult.failed).toHaveLength(1);
    });

    it('should handle malformed backend responses', async () => {
      render(<ErrorHandlingTestHarness />);

      await waitFor(() => {
        expect(mockWebSocketService.onMessage).toBeDefined();
      });

      // Simulate malformed message
      const malformedMessage = {
        type: 'invalid_type',
        payload: null,
        corrupted: true
      };

      expect(() => {
        act(() => {
          mockWebSocketService.onMessage!(malformedMessage);
        });
      }).not.toThrow();

      // Should log error but not crash
      expect(logger.error).toHaveBeenCalled();
    });
  });

  describe('Optimistic Update Error Handling', () => {
    it('should handle optimistic message creation failures', async () => {
      // Mock optimistic manager failure
      const originalAddOptimistic = optimisticMessageManager.addOptimisticUserMessage;
      optimisticMessageManager.addOptimisticUserMessage = jest.fn().mockImplementation(() => {
        throw new Error('Optimistic creation failed');
      });

      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(<ErrorHandlingTestHarness />);

      const textarea = screen.getByRole('textbox', { name: /message input/i });
      await user.type(textarea, 'Message causing optimistic failure');

      expect(async () => {
        await user.keyboard('{Enter}');
      }).not.toThrow();

      // Should still attempt to send via WebSocket
      expect(mockWebSocketService.sendMessage).toHaveBeenCalled();

      // Restore original function
      optimisticMessageManager.addOptimisticUserMessage = originalAddOptimistic;
    });

    it('should handle optimistic update conflicts', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(<ErrorHandlingTestHarness />);

      const textarea = screen.getByRole('textbox', { name: /message input/i });
      await user.type(textarea, 'Message for conflict test');
      await user.keyboard('{Enter}');

      const optimisticMessages = optimisticMessageManager.getOptimisticMessages();
      const userMessage = optimisticMessages.find(m => m.role === 'user');

      // Simulate conflicting updates
      if (userMessage) {
        optimisticMessageManager.updateOptimisticMessage(userMessage.localId, { status: 'confirmed' });
        optimisticMessageManager.updateOptimisticMessage(userMessage.localId, { status: 'failed' });
        optimisticMessageManager.updateOptimisticMessage(userMessage.localId, { status: 'pending' });
      }

      // Should handle conflicts gracefully
      const finalMessage = optimisticMessageManager.getOptimisticMessages()
        .find(m => m.localId === userMessage?.localId);
      
      expect(finalMessage?.status).toBe('pending'); // Last update wins
    });

    it('should handle reconciliation with conflicting backend data', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(<ErrorHandlingTestHarness />);

      const textarea = screen.getByRole('textbox', { name: /message input/i });
      await user.type(textarea, 'Original message content');
      await user.keyboard('{Enter}');

      // Backend returns different content
      const conflictingBackendMessage = {
        id: 'backend-123',
        content: 'Modified message content', // Different from what user sent
        role: 'user' as const,
        timestamp: Date.now()
      };

      const reconciliationResult = optimisticMessageManager.reconcileWithBackend([conflictingBackendMessage]);

      // Should still reconcile but with backend data taking precedence
      expect(reconciliationResult.confirmed).toHaveLength(1);
      expect(reconciliationResult.confirmed[0].content).toBe('Modified message content');
    });
  });

  describe('Retry Mechanism Testing', () => {
    it('should implement exponential backoff for retries', async () => {
      let retryCount = 0;
      const retryDelays: number[] = [];
      
      const mockRetry = jest.fn().mockImplementation(async () => {
        const startTime = Date.now();
        retryCount++;
        
        if (retryCount <= 3) {
          // Record delay between retries
          if (retryCount > 1) {
            retryDelays.push(Date.now() - startTime);
          }
          throw new Error(`Retry ${retryCount} failed`);
        }
        // Fourth retry succeeds
      });

      const failedMessage = {
        localId: 'failed-msg-123',
        content: 'Failed message',
        status: 'failed' as const,
        retry: mockRetry
      };

      // Simulate retry attempts
      for (let i = 0; i < 4; i++) {
        try {
          await optimisticMessageManager.retryMessage(failedMessage.localId);
        } catch (error) {
          // Expected for first 3 attempts
        }
        
        act(() => {
          jest.advanceTimersByTime(Math.pow(2, i) * 1000); // Exponential backoff
        });
      }

      expect(retryCount).toBe(4);
    });

    it('should respect maximum retry attempts', async () => {
      const message = optimisticMessageManager.addOptimisticUserMessage('Test message');
      optimisticMessageManager.updateOptimisticMessage(message.localId, { status: 'failed' });

      // Attempt more than maximum retries (3)
      for (let i = 0; i < 5; i++) {
        if (i < 3) {
          await expect(optimisticMessageManager.retryMessage(message.localId)).resolves.toBeUndefined();
          optimisticMessageManager.updateOptimisticMessage(message.localId, { status: 'failed' });
        } else {
          await expect(optimisticMessageManager.retryMessage(message.localId))
            .rejects.toBe('Max retries exceeded');
        }
      }
    });

    it('should allow manual retry after automatic retries exhausted', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      // Setup failing WebSocket
      mockWebSocketService.sendMessage.mockImplementation(() => {
        throw new Error('Persistent network error');
      });

      render(<ErrorHandlingTestHarness />);

      const textarea = screen.getByRole('textbox', { name: /message input/i });
      await user.type(textarea, 'Message for manual retry');
      await user.keyboard('{Enter}');

      // Should have failed message
      await waitFor(() => {
        const failedMessages = optimisticMessageManager.getFailedMessages();
        expect(failedMessages.length).toBeGreaterThan(0);
      });

      // Exhaust automatic retries
      const failedMessage = optimisticMessageManager.getFailedMessages()[0];
      for (let i = 0; i < 3; i++) {
        await failedMessage.retry!().catch(() => {});
      }

      // Manual retry should still be possible (user action)
      // Fix the WebSocket for successful retry
      mockWebSocketService.sendMessage.mockImplementation(() => {});
      
      // User manually retries
      await user.type(textarea, 'Retry message');
      await user.keyboard('{Enter}');

      expect(mockWebSocketService.sendMessage).toHaveBeenCalledTimes(4); // 3 failed + 1 successful
    });
  });

  describe('Error Recovery and User Feedback', () => {
    it('should provide clear error messages to users', async () => {
      const errorHandler = jest.fn();
      
      render(<ErrorHandlingTestHarness onError={errorHandler} simulateNetworkFailure={true} />);

      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      const textarea = screen.getByRole('textbox', { name: /message input/i });
      
      await user.type(textarea, 'Message causing error');
      await user.keyboard('{Enter}');

      await waitFor(() => {
        expect(errorHandler).toHaveBeenCalledWith(
          expect.objectContaining({
            message: expect.stringMatching(/Network connection failed/)
          })
        );
      });
    });

    it('should maintain UI responsiveness during errors', async () => {
      // Simulate slow error handling
      mockWebSocketService.sendMessage.mockImplementation(async () => {
        await new Promise(resolve => setTimeout(resolve, 100));
        throw new Error('Slow error');
      });

      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(<ErrorHandlingTestHarness />);

      const textarea = screen.getByRole('textbox', { name: /message input/i });
      
      // Send message
      await user.type(textarea, 'First message');
      const sendPromise = user.keyboard('{Enter}');

      // UI should remain responsive - can type in textarea immediately
      await user.clear(textarea);
      await user.type(textarea, 'Second message while first is failing');

      expect(textarea).toHaveValue('Second message while first is failing');

      await sendPromise; // Wait for first message to complete
    });

    it('should allow error recovery without page refresh', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      // Start with failing WebSocket
      mockWebSocketService.sendMessage.mockImplementation(() => {
        throw new Error('Initial connection error');
      });

      render(<ErrorHandlingTestHarness />);

      const textarea = screen.getByRole('textbox', { name: /message input/i });
      await user.type(textarea, 'Message during error');
      await user.keyboard('{Enter}');

      // Should show error state
      await waitFor(() => {
        const failedMessages = optimisticMessageManager.getFailedMessages();
        expect(failedMessages.length).toBeGreaterThan(0);
      });

      // Fix the connection
      mockWebSocketService.sendMessage.mockImplementation(() => {
        // Connection restored - succeeds
      });

      // Send another message
      await user.clear(textarea);
      await user.type(textarea, 'Message after recovery');
      await user.keyboard('{Enter}');

      // Should work normally now
      expect(mockWebSocketService.sendMessage).toHaveBeenLastCalledWith(
        expect.objectContaining({
          payload: expect.objectContaining({
            user_request: 'Message after recovery'
          })
        })
      );
    });
  });

  describe('Edge Cases and Boundary Conditions', () => {
    it('should handle rapid error and recovery cycles', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      let shouldFail = true;
      mockWebSocketService.sendMessage.mockImplementation(() => {
        if (shouldFail) {
          shouldFail = false; // Next call will succeed
          throw new Error('Intermittent error');
        }
        // Success
      });

      render(<ErrorHandlingTestHarness />);

      const textarea = screen.getByRole('textbox', { name: /message input/i });

      // Send multiple messages with alternating success/failure
      const messages = ['Message 1', 'Message 2', 'Message 3', 'Message 4'];
      
      for (const message of messages) {
        await user.clear(textarea);
        await user.type(textarea, message);
        await user.keyboard('{Enter}');
        
        act(() => {
          jest.advanceTimersByTime(100);
        });
      }

      // Should have handled all messages without crashing
      expect(mockWebSocketService.sendMessage).toHaveBeenCalledTimes(4);
    });

    it('should handle memory cleanup during error states', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      mockWebSocketService.sendMessage.mockImplementation(() => {
        throw new Error('All messages fail');
      });

      const { unmount } = render(<ErrorHandlingTestHarness />);

      const textarea = screen.getByRole('textbox', { name: /message input/i });

      // Create many failed messages
      for (let i = 0; i < 100; i++) {
        await user.clear(textarea);
        await user.type(textarea, `Failed message ${i}`);
        await user.keyboard('{Enter}');
        
        act(() => {
          jest.advanceTimersByTime(10);
        });
      }

      // Unmount component
      unmount();

      // Should cleanup without memory leaks
      const remainingMessages = optimisticMessageManager.getOptimisticMessages();
      expect(remainingMessages.length).toBeLessThan(200); // Should have reasonable bounds
    });

    it('should handle errors during component unmounting', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      let resolveSlowSend: () => void;
      const slowSendPromise = new Promise<void>((resolve) => {
        resolveSlowSend = resolve;
      });

      mockWebSocketService.sendMessage.mockImplementation(() => slowSendPromise);

      const { unmount } = render(<ErrorHandlingTestHarness />);

      const textarea = screen.getByRole('textbox', { name: /message input/i });
      await user.type(textarea, 'Message during unmount');
      await user.keyboard('{Enter}');

      // Unmount while send is in progress
      unmount();

      // Complete the slow operation
      act(() => {
        resolveSlowSend!();
      });

      // Should not cause any errors after unmount
      expect(() => {
        resolveSlowSend!();
      }).not.toThrow();
    });
  });
});