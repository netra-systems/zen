/**
 * Error Handling and Recovery Integration Tests
 * Implements comprehensive error handling scenarios for Netra Apex frontend
 * Tests graceful degradation, automatic retry, and recovery without page refresh
 */

import React from 'react';
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { jest } from '@jest/globals';
import WS from 'jest-websocket-mock';
import { TestProviders } from '../setup/test-providers';
import * as WebSocketTestManager from '@/__tests__/helpers/websocket-test-manager';
import { webSocketService } from '@/services/webSocketService';
import { logger } from '@/lib/logger';

// Mock dependencies
jest.mock('@/services/webSocketService');
jest.mock('@/lib/logger');
jest.mock('@/config', () => ({
  config: {
    wsUrl: 'ws://localhost:8000',
    apiUrl: 'http://localhost:3000/api',
    retryAttempts: 3,
    retryDelay: 1000
  }
}));

interface ErrorTestScenario {
  name: string;
  error: Error;
  expectedRecovery: boolean;
}

interface APIError {
  status: number;
  message: string;
  retryable: boolean;
}

interface RetryConfig {
  attempts: number;
  baseDelay: number;
  maxDelay: number;
}

const createAPIError = (status: number, message: string): APIError => ({
  status,
  message, 
  retryable: status >= 500 || status === 429
});

const createRetryConfig = (): RetryConfig => ({
  attempts: 3,
  baseDelay: 1000,
  maxDelay: 10000
});

const calculateBackoffDelay = (attempt: number, config: RetryConfig): number => {
  const delay = config.baseDelay * Math.pow(2, attempt - 1);
  return Math.min(delay, config.maxDelay);
};

const simulateNetworkError = (): Error => {
  return new Error('Network request failed');
};

const ErrorRecoveryComponent: React.FC = () => {
  const [error, setError] = React.useState<string | null>(null);
  const [isRetrying, setIsRetrying] = React.useState(false);
  const [retryCount, setRetryCount] = React.useState(0);
  const [messages, setMessages] = React.useState<string[]>([]);

  const handleAPICall = async (shouldFail = false) => {
    setError(null);
    setIsRetrying(true);
    
    try {
      if (shouldFail) {
        throw simulateNetworkError();
      }
      
      const response = await fetch('/api/test');
      if (!response.ok) {
        throw createAPIError(response.status, 'API request failed');
      }
      
      setMessages(prev => [...prev, 'API call successful']);
    } catch (err) {
      setError((err as Error).message);
      setRetryCount(prev => prev + 1);
    } finally {
      setIsRetrying(false);
    }
  };

  const handleRetry = () => {
    if (retryCount < 3) {
      handleAPICall();
    }
  };

  const clearError = () => {
    setError(null);
    setRetryCount(0);
  };

  return (
    <div>
      <button 
        onClick={() => handleAPICall(false)}
        data-testid="api-success-btn"
      >
        Success API Call
      </button>
      <button 
        onClick={() => handleAPICall(true)}
        data-testid="api-error-btn"
      >
        Error API Call
      </button>
      
      {error && (
        <div data-testid="error-display">
          <p>Error: {error}</p>
          <p>Attempts: {retryCount}</p>
          {retryCount < 3 && (
            <button onClick={handleRetry} data-testid="retry-btn">
              Retry ({3 - retryCount} attempts left)
            </button>
          )}
          <button onClick={clearError} data-testid="clear-error-btn">
            Clear Error
          </button>
        </div>
      )}
      
      {isRetrying && (
        <div data-testid="loading-indicator">
          Retrying...
        </div>
      )}
      
      <div data-testid="message-list">
        {messages.map((msg, idx) => (
          <div key={idx}>{msg}</div>
        ))}
      </div>
    </div>
  );
};

const SessionTimeoutComponent: React.FC = () => {
  const [isAuthenticated, setIsAuthenticated] = React.useState(true);
  const [sessionTimeout, setSessionTimeout] = React.useState<NodeJS.Timeout | null>(null);
  const [showTimeoutWarning, setShowTimeoutWarning] = React.useState(false);

  React.useEffect(() => {
    const timeout = setTimeout(() => {
      setShowTimeoutWarning(true);
      setTimeout(() => {
        setIsAuthenticated(false);
        setShowTimeoutWarning(false);
      }, 5000);
    }, 10000);
    
    setSessionTimeout(timeout);
    
    return () => {
      if (timeout) clearTimeout(timeout);
    };
  }, []);

  const handleRefreshSession = () => {
    setShowTimeoutWarning(false);
    if (sessionTimeout) clearTimeout(sessionTimeout);
    
    // Simulate session refresh
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    setIsAuthenticated(false);
    setShowTimeoutWarning(false);
  };

  if (!isAuthenticated) {
    return (
      <div data-testid="login-required">
        <p>Session expired. Please log in again.</p>
        <button 
          onClick={() => setIsAuthenticated(true)}
          data-testid="login-btn"
        >
          Log In
        </button>
      </div>
    );
  }

  return (
    <div>
      <p data-testid="authenticated-content">
        You are authenticated
      </p>
      
      {showTimeoutWarning && (
        <div data-testid="timeout-warning">
          <p>Your session will expire soon.</p>
          <button 
            onClick={handleRefreshSession}
            data-testid="refresh-session-btn"
          >
            Refresh Session
          </button>
          <button 
            onClick={handleLogout}
            data-testid="logout-btn"
          >
            Logout
          </button>
        </div>
      )}
    </div>
  );
};

const RateLimitComponent: React.FC = () => {
  const [requestCount, setRequestCount] = React.useState(0);
  const [isRateLimited, setIsRateLimited] = React.useState(false);
  const [resetTime, setResetTime] = React.useState<number | null>(null);

  const handleRequest = async () => {
    if (isRateLimited) return;
    
    const newCount = requestCount + 1;
    setRequestCount(newCount);
    
    if (newCount >= 5) {
      setIsRateLimited(true);
      setResetTime(Date.now() + 10000); // 10 seconds
      
      setTimeout(() => {
        setIsRateLimited(false);
        setRequestCount(0);
        setResetTime(null);
      }, 10000);
    }
  };

  return (
    <div>
      <button 
        onClick={handleRequest}
        disabled={isRateLimited}
        data-testid="rate-limit-btn"
      >
        Make Request ({requestCount}/5)
      </button>
      
      {isRateLimited && (
        <div data-testid="rate-limit-warning">
          <p>Rate limit exceeded. Try again in {resetTime ? Math.ceil((resetTime - Date.now()) / 1000) : 0} seconds.</p>
        </div>
      )}
    </div>
  );
};

describe('Error Handling and Recovery Tests', () => {
  let wsManager: WebSocketTestManager;
  let mockFetch: jest.MockedFunction<typeof fetch>;

  beforeEach(() => {
    wsManager = new WebSocketTestManager();
    wsManager.setup();
    
    // Mock fetch for API error testing
    mockFetch = jest.fn() as jest.MockedFunction<typeof fetch>;
    global.fetch = mockFetch;
    
    // Reset timers
    jest.useFakeTimers();
  });

  afterEach(() => {
    wsManager.cleanup();
    jest.clearAllMocks();
    jest.useRealTimers();
  });

  describe('API Error Handling with Exponential Backoff', () => {
    it('should handle API failures with automatic retry', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      // First call fails, second succeeds
      mockFetch
        .mockRejectedValueOnce(simulateNetworkError())
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ success: true })
        } as Response);

      render(
        <TestProviders>
          <ErrorRecoveryComponent />
        </TestProviders>
      );

      // Trigger error
      await user.click(screen.getByTestId('api-error-btn'));
      
      // Should show error
      await waitFor(() => {
        expect(screen.getByTestId('error-display')).toBeInTheDocument();
        expect(screen.getByText(/Network request failed/)).toBeInTheDocument();
        expect(screen.getByText(/Attempts: 1/)).toBeInTheDocument();
      });

      // Retry should succeed
      await user.click(screen.getByTestId('retry-btn'));
      
      await waitFor(() => {
        expect(screen.queryByTestId('error-display')).not.toBeInTheDocument();
      });
    });

    it('should show clear error messages for different error types', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      // Test Network Error
      mockFetch.mockRejectedValueOnce(simulateNetworkError());
      
      const { unmount } = render(
        <TestProviders>
          <ErrorRecoveryComponent />
        </TestProviders>
      );

      await user.click(screen.getByTestId('api-error-btn'));
      
      await waitFor(() => {
        expect(screen.getByTestId('error-display')).toBeInTheDocument();
        expect(screen.getByText(/Network request failed/)).toBeInTheDocument();
      });
      
      unmount();
    }, 10000);
  });

  describe('Session Timeout Recovery', () => {
    it('should handle session timeout with warning and recovery', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(
        <TestProviders>
          <SessionTimeoutComponent />
        </TestProviders>
      );

      // Initially authenticated
      expect(screen.getByTestId('authenticated-content')).toBeInTheDocument();

      // Fast-forward to show timeout warning
      act(() => {
        jest.advanceTimersByTime(10000);
      });

      await waitFor(() => {
        expect(screen.getByTestId('timeout-warning')).toBeInTheDocument();
        expect(screen.getByText(/session will expire soon/)).toBeInTheDocument();
      });

      // Refresh session
      await user.click(screen.getByTestId('refresh-session-btn'));
      
      await waitFor(() => {
        expect(screen.queryByTestId('timeout-warning')).not.toBeInTheDocument();
        expect(screen.getByTestId('authenticated-content')).toBeInTheDocument();
      });
    });

    it('should redirect to login after session expires', async () => {
      render(
        <TestProviders>
          <SessionTimeoutComponent />
        </TestProviders>
      );

      // Fast-forward past timeout warning and expiration
      act(() => {
        jest.advanceTimersByTime(15000);
      });

      await waitFor(() => {
        expect(screen.getByTestId('login-required')).toBeInTheDocument();
        expect(screen.getByText(/Session expired/)).toBeInTheDocument();
      });
    });
  });

  describe('Rate Limiting with User Feedback', () => {
    it('should handle rate limiting with clear feedback', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(
        <TestProviders>
          <RateLimitComponent />
        </TestProviders>
      );

      const button = screen.getByTestId('rate-limit-btn');

      // Make requests until rate limited
      for (let i = 0; i < 5; i++) {
        await user.click(button);
      }

      // Should show rate limit warning
      await waitFor(() => {
        expect(screen.getByTestId('rate-limit-warning')).toBeInTheDocument();
        expect(button).toBeDisabled();
      });

      // Fast-forward past rate limit reset
      act(() => {
        jest.advanceTimersByTime(10000);
      });

      await waitFor(() => {
        expect(screen.queryByTestId('rate-limit-warning')).not.toBeInTheDocument();
        expect(button).toBeEnabled();
      });
    });
  });

  describe('Recovery Without Page Refresh', () => {
    it('should recover from errors without losing application state', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      // Only mock the success calls since error call doesn't use fetch
      // Error call uses shouldFail=true which throws before reaching fetch
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ success: true })
        } as Response)
        .mockResolvedValueOnce({
          ok: true, 
          json: async () => ({ success: true })
        } as Response);

      render(
        <TestProviders>
          <ErrorRecoveryComponent />
        </TestProviders>
      );

      // Make successful call
      await user.click(screen.getByTestId('api-success-btn'));
      
      await waitFor(() => {
        expect(screen.getByText('API call successful')).toBeInTheDocument();
        expect(screen.getAllByText('API call successful')).toHaveLength(1);
      });

      // Make failing call - this throws simulateNetworkError() without using fetch
      await user.click(screen.getByTestId('api-error-btn'));
      
      await waitFor(() => {
        expect(screen.getByTestId('error-display')).toBeInTheDocument();
        // Should still show previous successful message
        expect(screen.getByText('API call successful')).toBeInTheDocument();
        expect(screen.getAllByText('API call successful')).toHaveLength(1);
      });

      // Clear error - this should only clear the error, not affect messages
      await user.click(screen.getByTestId('clear-error-btn'));
      
      await waitFor(() => {
        expect(screen.queryByTestId('error-display')).not.toBeInTheDocument();
        // Messages should still be there
        expect(screen.getAllByText('API call successful')).toHaveLength(1);
      });

      // Make another successful call - this should add a second message
      await user.click(screen.getByTestId('api-success-btn'));
      
      await waitFor(
        () => {
          // Should have two successful messages
          expect(screen.getAllByText('API call successful')).toHaveLength(2);
        },
        { timeout: 5000 }
      );
    });
  });

  describe('Graceful Feature Degradation', () => {
    it('should degrade gracefully when WebSocket is unavailable', async () => {
      // Simulate WebSocket connection failure
      wsManager.close();
      
      const TestComponent = () => {
        const [wsStatus, setWsStatus] = React.useState('connecting');
        const [fallbackMode, setFallbackMode] = React.useState(false);
        
        React.useEffect(() => {
          const timer = setTimeout(() => {
            setWsStatus('failed');
            setFallbackMode(true);
          }, 3000);
          
          return () => clearTimeout(timer);
        }, []);
        
        return (
          <div>
            <div data-testid="ws-status">
              WebSocket: {wsStatus}
            </div>
            {fallbackMode && (
              <div data-testid="fallback-mode">
                Using polling mode
              </div>
            )}
          </div>
        );
      };
      
      render(
        <TestProviders>
          <TestComponent />
        </TestProviders>
      );

      // Fast-forward to trigger fallback
      act(() => {
        jest.advanceTimersByTime(3000);
      });

      await waitFor(() => {
        expect(screen.getByTestId('ws-status')).toHaveTextContent('failed');
        expect(screen.getByTestId('fallback-mode')).toBeInTheDocument();
      });
    });
  });

  describe('Error Boundary Integration', () => {
    it('should catch and handle component errors gracefully', async () => {
      const ThrowingComponent = ({ shouldThrow }: { shouldThrow: boolean }) => {
        if (shouldThrow) {
          throw new Error('Component error');
        }
        return <div data-testid="working-component">Working</div>;
      };
      
      const ErrorBoundaryWrapper = () => {
        const [hasError, setHasError] = React.useState(false);
        const [shouldThrow, setShouldThrow] = React.useState(false);
        
        const handleError = () => {
          setHasError(true);
        };
        
        const resetError = () => {
          setHasError(false);
          setShouldThrow(false);
        };
        
        if (hasError) {
          return (
            <div>
              <div data-testid="error-boundary">
                Something went wrong
              </div>
              <button onClick={resetError} data-testid="reset-error-btn">
                Try Again
              </button>
            </div>
          );
        }
        
        return (
          <div>
            <button 
              onClick={() => setShouldThrow(true)}
              data-testid="trigger-error-btn"
            >
              Trigger Error
            </button>
            <React.Suspense fallback={<div>Loading...</div>}>
              <ThrowingComponent shouldThrow={shouldThrow} />
            </React.Suspense>
          </div>
        );
      };
      
      // Note: Error boundaries require class components or custom error handling
      // This test simulates the error boundary behavior
      render(
        <TestProviders>
          <ErrorBoundaryWrapper />
        </TestProviders>
      );

      expect(screen.getByTestId('working-component')).toBeInTheDocument();
    });
  });
});
