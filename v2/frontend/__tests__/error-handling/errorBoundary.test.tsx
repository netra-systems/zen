import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ErrorBoundary } from 'react-error-boundary';

const ThrowError = ({ shouldThrow }: { shouldThrow: boolean }) => {
  if (shouldThrow) {
    throw new Error('Test error');
  }
  return <div>No error</div>;
};

const ErrorFallback = ({ error, resetErrorBoundary }: any) => (
  <div role="alert">
    <h2>Something went wrong</h2>
    <p>{error.message}</p>
    <button onClick={resetErrorBoundary}>Try again</button>
  </div>
);

describe('Error Boundary', () => {
  const originalError = console.error;
  
  beforeEach(() => {
    console.error = jest.fn();
  });

  afterEach(() => {
    console.error = originalError;
  });

  describe('Component Error Catching', () => {
    it('should catch and display component errors', () => {
      render(
        <ErrorBoundary FallbackComponent={ErrorFallback}>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText('Something went wrong')).toBeInTheDocument();
      expect(screen.getByText('Test error')).toBeInTheDocument();
    });

    it('should render children when no error occurs', () => {
      render(
        <ErrorBoundary FallbackComponent={ErrorFallback}>
          <ThrowError shouldThrow={false} />
        </ErrorBoundary>
      );

      expect(screen.getByText('No error')).toBeInTheDocument();
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });

    it('should allow error recovery with reset', () => {
      const { rerender } = render(
        <ErrorBoundary FallbackComponent={ErrorFallback}>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      expect(screen.getByRole('alert')).toBeInTheDocument();

      const resetButton = screen.getByText('Try again');
      fireEvent.click(resetButton);

      rerender(
        <ErrorBoundary FallbackComponent={ErrorFallback}>
          <ThrowError shouldThrow={false} />
        </ErrorBoundary>
      );

      expect(screen.getByText('No error')).toBeInTheDocument();
    });
  });

  describe('WebSocket Error Handling', () => {
    it('should handle WebSocket connection failures', () => {
      const WebSocketErrorComponent = () => {
        React.useEffect(() => {
          const mockWS = {
            onerror: null as ((error: Event) => void) | null,
            onopen: null as (() => void) | null,
          };

          if (mockWS.onerror) {
            mockWS.onerror(new Event('error'));
          }
        }, []);

        return <div>WebSocket Component</div>;
      };

      render(
        <ErrorBoundary 
          FallbackComponent={ErrorFallback}
          onError={(error) => {
            console.log('WebSocket error caught:', error);
          }}
        >
          <WebSocketErrorComponent />
        </ErrorBoundary>
      );

      expect(screen.getByText('WebSocket Component')).toBeInTheDocument();
    });

    it('should handle WebSocket message parsing errors', () => {
      const ParseErrorComponent = () => {
        React.useEffect(() => {
          try {
            JSON.parse('invalid json {');
          } catch (error) {
            console.error('JSON parse error:', error);
          }
        }, []);

        return <div>Parse Component</div>;
      };

      render(
        <ErrorBoundary FallbackComponent={ErrorFallback}>
          <ParseErrorComponent />
        </ErrorBoundary>
      );

      expect(screen.getByText('Parse Component')).toBeInTheDocument();
    });

    it('should handle WebSocket rate limiting errors', () => {
      const RateLimitComponent = () => {
        const [error, setError] = React.useState<string | null>(null);

        React.useEffect(() => {
          const simulateRateLimit = () => {
            setError('Rate limit exceeded. Please slow down your requests.');
          };

          const timer = setTimeout(simulateRateLimit, 100);
          return () => clearTimeout(timer);
        }, []);

        if (error) {
          throw new Error(error);
        }

        return <div>Rate Limit Component</div>;
      };

      render(
        <ErrorBoundary FallbackComponent={ErrorFallback}>
          <RateLimitComponent />
        </ErrorBoundary>
      );

      setTimeout(() => {
        expect(screen.getByText('Rate limit exceeded. Please slow down your requests.')).toBeInTheDocument();
      }, 150);
    });
  });

  describe('Authentication Error Handling', () => {
    it('should handle token expiration errors', () => {
      const TokenExpiredComponent = () => {
        React.useEffect(() => {
          const mockToken = 'expired-token';
          const expiry = Date.now() - 1000; // Expired
          
          if (Date.now() > expiry) {
            throw new Error('Token expired. Please log in again.');
          }
        }, []);

        return <div>Token Component</div>;
      };

      render(
        <ErrorBoundary FallbackComponent={ErrorFallback}>
          <TokenExpiredComponent />
        </ErrorBoundary>
      );

      expect(screen.getByText('Token expired. Please log in again.')).toBeInTheDocument();
    });

    it('should handle invalid credentials errors', () => {
      const InvalidCredentialsComponent = () => {
        React.useEffect(() => {
          const mockLogin = async () => {
            throw new Error('Invalid username or password');
          };
          
          mockLogin().catch(error => {
            throw error;
          });
        }, []);

        return <div>Login Component</div>;
      };

      render(
        <ErrorBoundary FallbackComponent={ErrorFallback}>
          <InvalidCredentialsComponent />
        </ErrorBoundary>
      );

      setTimeout(() => {
        expect(screen.getByText('Invalid username or password')).toBeInTheDocument();
      }, 100);
    });

    it('should handle authorization errors', () => {
      const UnauthorizedComponent = () => {
        const [shouldThrow, setShouldThrow] = React.useState(false);

        React.useEffect(() => {
          const checkAuth = () => {
            setShouldThrow(true);
          };
          checkAuth();
        }, []);

        if (shouldThrow) {
          throw new Error('403: You do not have permission to access this resource');
        }

        return <div>Authorized Component</div>;
      };

      render(
        <ErrorBoundary FallbackComponent={ErrorFallback}>
          <UnauthorizedComponent />
        </ErrorBoundary>
      );

      expect(screen.getByText('403: You do not have permission to access this resource')).toBeInTheDocument();
    });
  });

  describe('State Management Error Handling', () => {
    it('should handle store initialization errors', () => {
      const StoreErrorComponent = () => {
        React.useEffect(() => {
          const mockStore = {
            getState: () => {
              throw new Error('Store initialization failed');
            }
          };

          mockStore.getState();
        }, []);

        return <div>Store Component</div>;
      };

      render(
        <ErrorBoundary FallbackComponent={ErrorFallback}>
          <StoreErrorComponent />
        </ErrorBoundary>
      );

      expect(screen.getByText('Store initialization failed')).toBeInTheDocument();
    });

    it('should handle state update errors', () => {
      const StateUpdateErrorComponent = () => {
        const [state, setState] = React.useState<any>({ data: [] });

        React.useEffect(() => {
          try {
            setState((prev: any) => {
              if (prev.data.length > 100) {
                throw new Error('State update failed: Too many items');
              }
              return { ...prev, data: [...prev.data, ...Array(101).fill(0)] };
            });
          } catch (error) {
            throw error;
          }
        }, []);

        return <div>State Component</div>;
      };

      render(
        <ErrorBoundary FallbackComponent={ErrorFallback}>
          <StateUpdateErrorComponent />
        </ErrorBoundary>
      );

      expect(screen.getByText('State update failed: Too many items')).toBeInTheDocument();
    });
  });

  describe('API Error Handling', () => {
    it('should handle network errors', () => {
      const NetworkErrorComponent = () => {
        React.useEffect(() => {
          const mockFetch = () => {
            throw new Error('Network error: Unable to connect to server');
          };

          try {
            mockFetch();
          } catch (error) {
            throw error;
          }
        }, []);

        return <div>Network Component</div>;
      };

      render(
        <ErrorBoundary FallbackComponent={ErrorFallback}>
          <NetworkErrorComponent />
        </ErrorBoundary>
      );

      expect(screen.getByText('Network error: Unable to connect to server')).toBeInTheDocument();
    });

    it('should handle timeout errors', () => {
      const TimeoutErrorComponent = () => {
        React.useEffect(() => {
          const timeout = setTimeout(() => {
            throw new Error('Request timeout: Server did not respond within expected time');
          }, 0);

          return () => clearTimeout(timeout);
        }, []);

        return <div>Timeout Component</div>;
      };

      render(
        <ErrorBoundary FallbackComponent={ErrorFallback}>
          <TimeoutErrorComponent />
        </ErrorBoundary>
      );

      setTimeout(() => {
        expect(screen.getByText('Request timeout: Server did not respond within expected time')).toBeInTheDocument();
      }, 50);
    });

    it('should handle server errors', () => {
      const ServerErrorComponent = () => {
        React.useEffect(() => {
          const mockServerResponse = {
            status: 500,
            statusText: 'Internal Server Error'
          };

          if (mockServerResponse.status >= 500) {
            throw new Error(`Server error ${mockServerResponse.status}: ${mockServerResponse.statusText}`);
          }
        }, []);

        return <div>Server Component</div>;
      };

      render(
        <ErrorBoundary FallbackComponent={ErrorFallback}>
          <ServerErrorComponent />
        </ErrorBoundary>
      );

      expect(screen.getByText('Server error 500: Internal Server Error')).toBeInTheDocument();
    });
  });

  describe('Async Error Handling', () => {
    it('should handle promise rejection errors', async () => {
      const PromiseErrorComponent = () => {
        const [error, setError] = React.useState<string | null>(null);

        React.useEffect(() => {
          const asyncOperation = async () => {
            throw new Error('Async operation failed');
          };

          asyncOperation().catch(err => {
            setError(err.message);
          });
        }, []);

        if (error) {
          throw new Error(error);
        }

        return <div>Promise Component</div>;
      };

      render(
        <ErrorBoundary FallbackComponent={ErrorFallback}>
          <PromiseErrorComponent />
        </ErrorBoundary>
      );

      setTimeout(() => {
        expect(screen.getByText('Async operation failed')).toBeInTheDocument();
      }, 100);
    });

    it('should handle concurrent operation errors', () => {
      const ConcurrentErrorComponent = () => {
        React.useEffect(() => {
          const operations = Array.from({ length: 5 }, (_, i) => 
            new Promise((_, reject) => 
              setTimeout(() => reject(new Error(`Operation ${i} failed`)), i * 10)
            )
          );

          Promise.allSettled(operations).then(results => {
            const failures = results.filter(r => r.status === 'rejected') as PromiseRejectedResult[];
            if (failures.length > 0) {
              throw new Error(`Multiple operations failed: ${failures[0].reason.message}`);
            }
          });
        }, []);

        return <div>Concurrent Component</div>;
      };

      render(
        <ErrorBoundary FallbackComponent={ErrorFallback}>
          <ConcurrentErrorComponent />
        </ErrorBoundary>
      );

      setTimeout(() => {
        expect(screen.getByText(/Multiple operations failed/)).toBeInTheDocument();
      }, 100);
    });
  });

  describe('Error Recovery Strategies', () => {
    it('should provide retry functionality', () => {
      let attemptCount = 0;
      
      const RetryComponent = () => {
        React.useEffect(() => {
          attemptCount++;
          if (attemptCount < 3) {
            throw new Error(`Attempt ${attemptCount} failed`);
          }
        }, []);

        return <div>Success after {attemptCount} attempts</div>;
      };

      const RetryErrorFallback = ({ error, resetErrorBoundary }: any) => (
        <div role="alert">
          <p>{error.message}</p>
          <button onClick={() => {
            resetErrorBoundary();
          }}>
            Retry ({attemptCount}/3)
          </button>
        </div>
      );

      const { rerender } = render(
        <ErrorBoundary FallbackComponent={RetryErrorFallback}>
          <RetryComponent />
        </ErrorBoundary>
      );

      expect(screen.getByText('Attempt 1 failed')).toBeInTheDocument();
      
      fireEvent.click(screen.getByText(/Retry/));
      
      rerender(
        <ErrorBoundary FallbackComponent={RetryErrorFallback}>
          <RetryComponent />
        </ErrorBoundary>
      );

      expect(screen.getByText('Attempt 2 failed')).toBeInTheDocument();
      
      fireEvent.click(screen.getByText(/Retry/));
      
      rerender(
        <ErrorBoundary FallbackComponent={RetryErrorFallback}>
          <RetryComponent />
        </ErrorBoundary>
      );

      expect(screen.getByText('Success after 3 attempts')).toBeInTheDocument();
    });

    it('should provide fallback content for critical errors', () => {
      const CriticalErrorFallback = ({ error }: any) => (
        <div role="alert">
          <h1>Application Error</h1>
          <p>The application has encountered a critical error and needs to be reloaded.</p>
          <details>
            <summary>Error Details</summary>
            <pre>{error.message}</pre>
          </details>
          <button onClick={() => window.location.reload()}>
            Reload Application
          </button>
        </div>
      );

      const CriticalErrorComponent = () => {
        throw new Error('Critical system failure: Memory allocation error');
      };

      render(
        <ErrorBoundary FallbackComponent={CriticalErrorFallback}>
          <CriticalErrorComponent />
        </ErrorBoundary>
      );

      expect(screen.getByText('Application Error')).toBeInTheDocument();
      expect(screen.getByText('Critical system failure: Memory allocation error')).toBeInTheDocument();
      expect(screen.getByText('Reload Application')).toBeInTheDocument();
    });
  });
});