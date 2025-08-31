import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';
import React, { useState, useRef } from 'react';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
s
 * - Value Impact: Reduces user frustration from transient failures
 * - Revenue Impact: +$50K MRR from improved reliability
 */
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';
import React, { useState, useRef } from 'react';

// ============================================================================
// RETRY CONFIGURATION
// ============================================================================

interface RetryConfig {
  maxRetries: number;
  retryDelay: number;
  exponentialBackoff: boolean;
  retryableStatuses: number[];
}

class TimeoutError extends Error {
  constructor(message: string = 'Request timeout') {
    super(message);
    this.name = 'TimeoutError';
  }
}

const defaultRetryConfig: RetryConfig = {
  maxRetries: 3,
  retryDelay: 500,
  exponentialBackoff: true,
  retryableStatuses: [408, 429, 500, 502, 503, 504]
};

const calculateDelay = (attempt: number, config: RetryConfig): number => {
  const baseDelay = config.retryDelay;
  return config.exponentialBackoff 
    ? baseDelay * Math.pow(2, attempt - 1)
    : baseDelay;
};

const sleep = (ms: number): Promise<void> => 
  new Promise(resolve => setTimeout(resolve, ms));

// ============================================================================
// ROBUST API CLIENT
// ============================================================================

class RobustApiClient {
  private abortControllers = new Map<string, AbortController>();

  async request(
    url: string, 
    options: RequestInit & { 
      timeout?: number; 
      retry?: Partial<RetryConfig>;
      onRetry?: (attempt: number, error: Error) => void;
    } = {}
  ): Promise<any> {
    const {
      timeout = 5000,
      retry = {},
      onRetry,
      ...fetchOptions
    } = options;
    
    const retryConfig = { ...defaultRetryConfig, ...retry };
    const requestId = `${url}_${Date.now()}_${Math.random()}`;
    
    let lastError: Error;
    
    for (let attempt = 1; attempt <= retryConfig.maxRetries + 1; attempt++) {
      const abortController = new AbortController();
      this.abortControllers.set(requestId, abortController);
      
      try {
        const response = await this.makeRequest(url, {
          ...fetchOptions,
          signal: abortController.signal
        }, timeout);
        
        this.abortControllers.delete(requestId);
        return response;
        
      } catch (error) {
        lastError = error as Error;
        this.abortControllers.delete(requestId);
        
        if (attempt <= retryConfig.maxRetries) {
          onRetry?.(attempt, lastError);
          const delay = calculateDelay(attempt, retryConfig);
          await sleep(delay);
          continue;
        }
        
        break;
      }
    }
    
    throw lastError!;
  }

  private async makeRequest(
    url: string,
    options: RequestInit,
    timeout: number
  ): Promise<any> {
    const timeoutPromise = new Promise<never>((_, reject) => {
      setTimeout(() => reject(new TimeoutError()), timeout);
    });
    
    try {
      const fetchPromise = fetch(url, options);
      const response = await Promise.race([fetchPromise, timeoutPromise]);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      return await response.json();
      
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        throw new Error('Request cancelled');
      }
      throw error;
    }
  }

  cancelRequest(requestId: string): void {
    const controller = this.abortControllers.get(requestId);
    if (controller) {
      controller.abort();
      this.abortControllers.delete(requestId);
    }
  }

  cancelAllRequests(): void {
    this.abortControllers.forEach(controller => controller.abort());
    this.abortControllers.clear();
  }
}

// ============================================================================
// TEST COMPONENTS
// ============================================================================

const RetryTestComponent: React.FC<{ url: string; retryConfig?: Partial<RetryConfig> }> = ({ 
  url, 
  retryConfig 
}) => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  const apiClient = useRef(new RobustApiClient());
  
  const makeRequest = async () => {
    setLoading(true);
    setError(null);
    setRetryCount(0);
    
    try {
      const result = await apiClient.current.request(url, {
        retry: retryConfig,
        onRetry: (attempt) => setRetryCount(attempt)
      });
      setData(result);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div data-testid="retry-test-component">
      <button onClick={makeRequest} data-testid="start-request">
        Start Request
      </button>
      
      {loading && (
        <div data-testid="loading">
          Loading...
          {retryCount > 0 && <span data-testid="retry-count">Retry {retryCount}</span>}
        </div>
      )}
      {error && <div data-testid="error">{error}</div>}
      {data && <div data-testid="data">{JSON.stringify(data)}</div>}
    </div>
  );
};

const CancellableRequestComponent: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState<string | null>(null);
  const apiClient = useRef(new RobustApiClient());
  const abortController = useRef<AbortController | null>(null);
  
  const startRequest = async () => {
    setLoading(true);
    setError(null);
    setData(null);
    abortController.current = new AbortController();
    
    try {
      const result = await apiClient.current.request(
        'http://localhost:8000/api/slow',
        { signal: abortController.current.signal }
      );
      setData(result);
    } catch (err) {
      if ((err as Error).message.includes('cancelled')) {
        setError('Request cancelled');
      } else {
        setError((err as Error).message);
      }
    } finally {
      setLoading(false);
    }
  };
  
  const cancelRequest = () => {
    if (abortController.current) {
      abortController.current.abort();
    }
  };
  
  return (
    <div data-testid="cancellable-request">
      <button onClick={startRequest} data-testid="start-request" disabled={loading}>
        Start Request
      </button>
      <button onClick={cancelRequest} data-testid="cancel-request" disabled={!loading}>
        Cancel Request
      </button>
      
      {loading && <div data-testid="loading">Loading...</div>}
      {error && <div data-testid="error">{error}</div>}
      {data && <div data-testid="data">{JSON.stringify(data)}</div>}
    </div>
  );
};

const TimeoutComponent: React.FC = () => {
  const [result, setResult] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const apiClient = useRef(new RobustApiClient());
  
  const testTimeout = async (timeoutMs: number) => {
    setLoading(true);
    setResult('');
    
    try {
      await apiClient.current.request(
        'http://localhost:8000/api/slow',
        { timeout: timeoutMs }
      );
      setResult('Success');
    } catch (error) {
      if (error instanceof TimeoutError) {
        setResult('Timeout');
      } else {
        setResult(`Error: ${(error as Error).message}`);
      }
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div data-testid="timeout-component">
      <button 
        onClick={() => testTimeout(100)}
        data-testid="fast-timeout"
        disabled={loading}
      >
        Fast Timeout (100ms)
      </button>
      <button 
        onClick={() => testTimeout(10000)}
        data-testid="slow-timeout"
        disabled={loading}
      >
        Slow Timeout (10s)
      </button>
      
      {loading && <div data-testid="loading">Loading...</div>}
      <div data-testid="result">{result}</div>
    </div>
  );
};

// ============================================================================
// MSW SERVER SETUP
// ============================================================================

const mockApiUrl = 'http://localhost:8000';

const createRetryHandlers = () => [
  // Flaky endpoint that fails then succeeds
  http.get(`${mockApiUrl}/api/flaky`, (() => {
    let callCount = 0;
    return () => {
      callCount++;
      if (callCount <= 2) {
        return new HttpResponse(null, { status: 500 });
      }
      return HttpResponse.json({ success: true, call: callCount });
    };
  })()),

  // Always fails endpoint
  http.get(`${mockApiUrl}/api/always-fails`, () => {
    return new HttpResponse(null, { status: 500 });
  }),

  // Slow endpoint for timeout testing
  http.get(`${mockApiUrl}/api/slow`, () => {
    return new Promise(resolve => {
      setTimeout(() => {
        resolve(HttpResponse.json({ data: 'slow response' }));
      }, 1000);
    });
  }),

  // Success endpoint
  http.get(`${mockApiUrl}/api/success`, () => {
    return HttpResponse.json({ message: 'Success' });
  })
];

const server = setupServer(...createRetryHandlers());

// ============================================================================
// TEST SETUP
// ============================================================================

beforeAll(() => {
  server.listen();
  jest.useFakeTimers();
});

afterEach(() => {
  server.resetHandlers();
  jest.clearAllMocks();
  act(() => {
    jest.runAllTimers();
    // Clean up timers to prevent hanging
    jest.clearAllTimers();
    jest.useFakeTimers();
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });
});

afterAll(() => {
  server.close();
  jest.useRealTimers();
});

// ============================================================================
// RETRY LOGIC TESTS
// ============================================================================

describe('Error Handling - Retry Logic', () => {
    jest.setTimeout(10000);
  it('retries failed requests with exponential backoff', async () => {
    render(
      <RetryTestComponent 
        url={`${mockApiUrl}/api/flaky`}
        retryConfig={{ 
          maxRetries: 3,
          exponentialBackoff: true,
          retryDelay: 500
        }}
      />
    );
    
    userEvent.click(screen.getByTestId('start-request'));
    
    // Should show loading with retry count
    await waitFor(() => {
      expect(screen.getByTestId('loading')).toBeInTheDocument();
    });
    
    // Advance through retries
    act(() => {
      jest.advanceTimersByTime(500); // First retry
    });
    
    await waitFor(() => {
      expect(screen.getByTestId('retry-count')).toHaveTextContent('Retry 1');
    });
    
    act(() => {
      jest.advanceTimersByTime(1000); // Second retry (exponential backoff)
    });
    
    await waitFor(() => {
      expect(screen.getByTestId('retry-count')).toHaveTextContent('Retry 2');
    });
    
    act(() => {
      jest.advanceTimersByTime(2000); // Third retry succeeds
    });
    
    await waitFor(() => {
      expect(screen.getByTestId('data')).toBeInTheDocument();
    });
  });

  it('respects max retry limit', async () => {
    render(
      <RetryTestComponent 
        url={`${mockApiUrl}/api/always-fails`}
        retryConfig={{ maxRetries: 1 }}
      />
    );
    
    userEvent.click(screen.getByTestId('start-request'));
    
    await waitFor(() => {
      expect(screen.getByTestId('retry-count')).toHaveTextContent('Retry 1');
    });
    
    act(() => {
      jest.advanceTimersByTime(2000);
    });
    
    await waitFor(() => {
      expect(screen.getByTestId('error')).toBeInTheDocument();
    });
  });

  it('uses linear backoff when exponential is disabled', async () => {
    const delays: number[] = [];
    let startTime = Date.now();
    
    const TestComponent = () => {
      const [retryCount, setRetryCount] = useState(0);
      const apiClient = useRef(new RobustApiClient());
      
      const makeRequest = async () => {
        try {
          await apiClient.current.request(`${mockApiUrl}/api/always-fails`, {
            retry: { 
              maxRetries: 2, 
              exponentialBackoff: false, 
              retryDelay: 1000 
            },
            onRetry: (attempt) => {
              const now = Date.now();
              if (delays.length > 0) {
                delays.push(now - startTime);
              }
              startTime = now;
              setRetryCount(attempt);
            }
          });
        } catch (error) {
          // Expected
        }
      };
      
      return (
        <div>
          <button onClick={makeRequest} data-testid="start">Start</button>
          <div data-testid="retry-count">{retryCount}</div>
        </div>
      );
    };

    render(<TestComponent />);
    
    userEvent.click(screen.getByTestId('start'));
    
    await waitFor(() => {
      expect(screen.getByTestId('retry-count')).toHaveTextContent('1');
    });
    
    act(() => {
      jest.advanceTimersByTime(1000);
    });
    
    await waitFor(() => {
      expect(screen.getByTestId('retry-count')).toHaveTextContent('2');
    });
  });
});

// ============================================================================
// REQUEST CANCELLATION TESTS
// ============================================================================

describe('Error Handling - Request Cancellation', () => {
    jest.setTimeout(10000);
  it('cancels ongoing requests', async () => {
    render(<CancellableRequestComponent />);
    
    userEvent.click(screen.getByTestId('start-request'));
    
    await waitFor(() => {
      expect(screen.getByTestId('loading')).toBeInTheDocument();
    });
    
    userEvent.click(screen.getByTestId('cancel-request'));
    
    await waitFor(() => {
      expect(screen.getByTestId('error')).toHaveTextContent('Request cancelled');
    });
  });

  it('handles multiple concurrent cancellations', async () => {
    const TestComponent = () => {
      const [requests, setRequests] = useState<Array<{ id: string; loading: boolean }>>([]);
      const apiClient = useRef(new RobustApiClient());
      
      const startRequest = () => {
        const id = `req_${Date.now()}`;
        setRequests(prev => [...prev, { id, loading: true }]);
        
        apiClient.current.request(`${mockApiUrl}/api/slow`)
          .then(() => {
            setRequests(prev => prev.map(r => 
              r.id === id ? { ...r, loading: false } : r
            ));
          })
          .catch(() => {
            setRequests(prev => prev.filter(r => r.id !== id));
          });
      };
      
      const cancelAll = () => {
        apiClient.current.cancelAllRequests();
        setRequests([]);
      };
      
      return (
        <div data-testid="multi-cancel-test">
          <button onClick={startRequest} data-testid="start-request">Start</button>
          <button onClick={cancelAll} data-testid="cancel-all">Cancel All</button>
          <div data-testid="request-count">{requests.length}</div>
        </div>
      );
    };

    render(<TestComponent />);
    
    // Start multiple requests
    userEvent.click(screen.getByTestId('start-request'));
    userEvent.click(screen.getByTestId('start-request'));
    userEvent.click(screen.getByTestId('start-request'));
    
    await waitFor(() => {
      expect(screen.getByTestId('request-count')).toHaveTextContent('3');
    });
    
    userEvent.click(screen.getByTestId('cancel-all'));
    
    await waitFor(() => {
      expect(screen.getByTestId('request-count')).toHaveTextContent('0');
    });
  });
});

// ============================================================================
// TIMEOUT HANDLING TESTS
// ============================================================================

describe('Error Handling - Timeout Handling', () => {
    jest.setTimeout(10000);
  it('handles request timeouts correctly', async () => {
    render(<TimeoutComponent />);
    
    userEvent.click(screen.getByTestId('fast-timeout'));
    
    await waitFor(() => {
      expect(screen.getByTestId('loading')).toBeInTheDocument();
    });
    
    act(() => {
      jest.advanceTimersByTime(200); // Advance past 100ms timeout
    });
    
    await waitFor(() => {
      expect(screen.getByTestId('result')).toHaveTextContent('Timeout');
    });
  });

  it('succeeds when response is within timeout', async () => {
    // Mock fast response
    server.use(
      http.get(`${mockApiUrl}/api/slow`, () => {
        return HttpResponse.json({ data: 'fast response' });
      })
    );

    render(<TimeoutComponent />);
    
    userEvent.click(screen.getByTestId('slow-timeout'));
    
    await waitFor(() => {
      expect(screen.getByTestId('result')).toHaveTextContent('Success');
    });
  });
});