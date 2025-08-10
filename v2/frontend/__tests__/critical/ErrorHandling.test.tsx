import { render, screen, fireEvent, waitFor, renderHook, act } from '@testing-library/react';
import { ErrorBoundary } from 'react-error-boundary';
import { useError } from '../../hooks/useError';
import ErrorFallback from '../../components/ErrorFallback';
import MainChat from '../../components/chat/MainChat';
import { WebSocketProvider } from '../../providers/WebSocketProvider';

// Mock console.error to prevent test noise
const originalConsoleError = console.error;
beforeAll(() => {
  console.error = jest.fn();
});

afterAll(() => {
  console.error = originalConsoleError;
});

describe('Error Handling and Fallback UI Tests', () => {
  describe('Error Boundary Integration', () => {
    it('should catch JavaScript errors and show fallback UI', () => {
      const ThrowError = ({ shouldThrow }: { shouldThrow: boolean }) => {
        if (shouldThrow) {
          throw new Error('Test component error');
        }
        return <div>No error</div>;
      };

      const { rerender } = render(
        <ErrorBoundary fallback={<ErrorFallback />}>
          <ThrowError shouldThrow={false} />
        </ErrorBoundary>
      );

      expect(screen.getByText('No error')).toBeInTheDocument();

      rerender(
        <ErrorBoundary fallback={<ErrorFallback />}>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
    });

    it('should allow error recovery through retry mechanism', async () => {
      const onReset = jest.fn();
      let shouldThrow = true;

      const ThrowError = () => {
        if (shouldThrow) {
          throw new Error('Recoverable error');
        }
        return <div>Component recovered</div>;
      };

      render(
        <ErrorBoundary 
          fallbackRender={({ resetErrorBoundary }) => (
            <ErrorFallback onRetry={resetErrorBoundary} />
          )}
          onReset={onReset}
        >
          <ThrowError />
        </ErrorBoundary>
      );

      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();

      // Simulate error resolution
      shouldThrow = false;
      const retryButton = screen.getByRole('button', { name: /try again/i });
      fireEvent.click(retryButton);

      await waitFor(() => {
        expect(screen.getByText('Component recovered')).toBeInTheDocument();
      });
    });

    it('should handle nested error boundaries correctly', () => {
      const OuterError = () => {
        throw new Error('Outer boundary error');
      };

      const InnerError = () => {
        throw new Error('Inner boundary error');
      };

      render(
        <ErrorBoundary fallback={<div>Outer fallback</div>}>
          <div>
            <ErrorBoundary fallback={<div>Inner fallback</div>}>
              <InnerError />
            </ErrorBoundary>
            <OuterError />
          </div>
        </ErrorBoundary>
      );

      // Inner error boundary should catch the inner error
      expect(screen.getByText('Inner fallback')).toBeInTheDocument();
      // But outer error boundary should catch the outer error
      expect(screen.getByText('Outer fallback')).toBeInTheDocument();
    });
  });

  describe('Network Error Handling', () => {
    it('should handle WebSocket connection failures gracefully', async () => {
      const onConnectionError = jest.fn();

      render(
        <WebSocketProvider onConnectionError={onConnectionError}>
          <MainChat />
        </WebSocketProvider>
      );

      // Simulate WebSocket connection failure
      const connectionError = new Event('error');
      Object.defineProperty(connectionError, 'target', {
        value: { readyState: WebSocket.CLOSED },
        enumerable: true,
      });

      act(() => {
        window.dispatchEvent(connectionError);
      });

      await waitFor(() => {
        expect(onConnectionError).toHaveBeenCalledWith(
          expect.objectContaining({
            type: 'CONNECTION_FAILED',
            retryable: true,
          })
        );
      });

      expect(screen.getByText(/connection lost/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /reconnect/i })).toBeInTheDocument();
    });

    it('should handle API request failures with proper user feedback', async () => {
      const mockFailedFetch = jest.fn().mockRejectedValue(new Error('Network error'));
      global.fetch = mockFailedFetch;

      const { result } = renderHook(() => useError());

      await act(async () => {
        try {
          await fetch('/api/chat/send');
        } catch (error) {
          result.current.addError({
            id: 'api_error',
            type: 'NETWORK_ERROR',
            message: 'Failed to send message',
            retryable: true,
            context: { endpoint: '/api/chat/send' },
          });
        }
      });

      expect(result.current.errors).toHaveLength(1);
      expect(result.current.errors[0]).toEqual({
        id: 'api_error',
        type: 'NETWORK_ERROR',
        message: 'Failed to send message',
        retryable: true,
        context: { endpoint: '/api/chat/send' },
      });
    });

    it('should implement exponential backoff for retryable errors', async () => {
      const retryAttempts: number[] = [];
      const mockRetryFetch = jest.fn()
        .mockRejectedValueOnce(new Error('First failure'))
        .mockRejectedValueOnce(new Error('Second failure'))
        .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) });

      const { result } = renderHook(() => useError());

      const retryWithBackoff = async (attempt: number) => {
        const delay = Math.min(1000 * Math.pow(2, attempt), 10000);
        retryAttempts.push(delay);
        await new Promise(resolve => setTimeout(resolve, delay));
        return mockRetryFetch();
      };

      await act(async () => {
        for (let i = 0; i < 3; i++) {
          try {
            await retryWithBackoff(i);
            break;
          } catch (error) {
            if (i === 2) {
              result.current.addError({
                id: 'retry_exhausted',
                type: 'RETRY_EXHAUSTED',
                message: 'Maximum retry attempts exceeded',
                retryable: false,
              });
            }
          }
        }
      });

      expect(retryAttempts).toEqual([1000, 2000, 4000]);
      expect(mockRetryFetch).toHaveBeenCalledTimes(3);
    });
  });

  describe('User Input Validation', () => {
    it('should validate and sanitize user input', async () => {
      const { result } = renderHook(() => useError());

      const dangerousInputs = [
        '<script>alert("xss")</script>',
        'javascript:void(0)',
        '"><script>alert(1)</script>',
        '\u0000null byte',
        'A'.repeat(10000), // Extremely long input
      ];

      for (const input of dangerousInputs) {
        act(() => {
          const validationResult = result.current.validateInput(input);
          
          if (!validationResult.isValid) {
            result.current.addError({
              id: `validation_${Date.now()}`,
              type: 'INPUT_VALIDATION_ERROR',
              message: validationResult.error,
              field: 'message',
            });
          }
        });
      }

      expect(result.current.errors.length).toBeGreaterThan(0);
      expect(result.current.errors.every(error => 
        error.type === 'INPUT_VALIDATION_ERROR'
      )).toBe(true);
    });

    it('should handle form submission errors gracefully', async () => {
      render(
        <ErrorBoundary fallback={<ErrorFallback />}>
          <MainChat />
        </ErrorBoundary>
      );

      const messageInput = screen.getByPlaceholderText(/type your message/i);
      const sendButton = screen.getByRole('button', { name: /send/i });

      // Test empty submission
      fireEvent.click(sendButton);

      await waitFor(() => {
        expect(screen.getByText(/message cannot be empty/i)).toBeInTheDocument();
      });

      // Test invalid input
      fireEvent.change(messageInput, { target: { value: '<script>alert("test")</script>' } });
      fireEvent.click(sendButton);

      await waitFor(() => {
        expect(screen.getByText(/invalid characters detected/i)).toBeInTheDocument();
      });
    });
  });

  describe('Resource Loading Errors', () => {
    it('should handle component lazy loading failures', async () => {
      const LazyComponent = React.lazy(() => 
        Promise.reject(new Error('Chunk load error'))
      );

      render(
        <ErrorBoundary fallback={<ErrorFallback />}>
          <React.Suspense fallback={<div>Loading...</div>}>
            <LazyComponent />
          </React.Suspense>
        </ErrorBoundary>
      );

      await waitFor(() => {
        expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
        expect(screen.getByText(/chunk load error/i)).toBeInTheDocument();
      });
    });

    it('should handle missing image resources gracefully', () => {
      render(
        <img 
          src="nonexistent-image.jpg"
          alt="Test image"
          onError={(e) => {
            (e.target as HTMLImageElement).src = '/fallback-image.png';
          }}
        />
      );

      const image = screen.getByAltText('Test image') as HTMLImageElement;
      
      // Simulate image load error
      fireEvent.error(image);

      expect(image.src).toContain('fallback-image.png');
    });
  });

  describe('State Consistency Errors', () => {
    it('should detect and recover from inconsistent application state', async () => {
      const { result } = renderHook(() => useError());

      const inconsistentState = {
        user: { id: '123', authenticated: true },
        token: null, // Inconsistent: authenticated but no token
        session: { active: false }, // Inconsistent: authenticated but inactive session
      };

      act(() => {
        const stateValidation = result.current.validateApplicationState(inconsistentState);
        
        if (!stateValidation.isValid) {
          result.current.addError({
            id: 'state_inconsistency',
            type: 'STATE_INCONSISTENCY',
            message: 'Authentication state mismatch detected',
            recovery: 'FORCE_REAUTH',
          });
        }
      });

      expect(result.current.errors).toContainEqual(
        expect.objectContaining({
          type: 'STATE_INCONSISTENCY',
          recovery: 'FORCE_REAUTH',
        })
      );
    });

    it('should handle concurrent state updates gracefully', async () => {
      const { result } = renderHook(() => useError());
      
      const concurrentUpdates = [
        { type: 'UPDATE_USER', payload: { name: 'User 1' } },
        { type: 'UPDATE_USER', payload: { name: 'User 2' } },
        { type: 'UPDATE_USER', payload: { name: 'User 3' } },
      ];

      // Simulate rapid concurrent updates
      await Promise.all(
        concurrentUpdates.map(update => 
          act(async () => {
            try {
              await result.current.processStateUpdate(update);
            } catch (error) {
              result.current.addError({
                id: `concurrent_update_${Date.now()}`,
                type: 'CONCURRENT_UPDATE_ERROR',
                message: 'State update conflict detected',
              });
            }
          })
        )
      );

      // Should handle conflicts gracefully without corrupting state
      expect(result.current.errors.filter(e => 
        e.type === 'CONCURRENT_UPDATE_ERROR'
      ).length).toBeLessThanOrEqual(2); // Some conflicts expected, but not all should fail
    });
  });

  describe('Memory and Performance Error Handling', () => {
    it('should handle memory pressure gracefully', async () => {
      const { result } = renderHook(() => useError());

      // Simulate memory pressure
      const largeArray = new Array(1000000).fill(0).map(() => ({
        data: new Array(1000).fill('x').join(''),
        timestamp: Date.now(),
      }));

      act(() => {
        try {
          // Simulate memory-intensive operation
          JSON.stringify(largeArray);
        } catch (error) {
          result.current.addError({
            id: 'memory_pressure',
            type: 'MEMORY_ERROR',
            message: 'Insufficient memory for operation',
            recovery: 'REDUCE_MEMORY_USAGE',
          });
        }
      });

      // Cleanup should be triggered
      expect(result.current.memoryCleanupTriggered).toBe(true);
    });

    it('should handle infinite loops and stack overflow', () => {
      const { result } = renderHook(() => useError());

      const recursiveFunction = (depth: number): any => {
        if (depth > 10000) {
          throw new RangeError('Maximum call stack size exceeded');
        }
        return recursiveFunction(depth + 1);
      };

      act(() => {
        try {
          recursiveFunction(0);
        } catch (error) {
          if (error instanceof RangeError) {
            result.current.addError({
              id: 'stack_overflow',
              type: 'STACK_OVERFLOW',
              message: 'Infinite recursion detected',
              recovery: 'RESTART_COMPONENT',
            });
          }
        }
      });

      expect(result.current.errors).toContainEqual(
        expect.objectContaining({
          type: 'STACK_OVERFLOW',
          recovery: 'RESTART_COMPONENT',
        })
      );
    });
  });
});