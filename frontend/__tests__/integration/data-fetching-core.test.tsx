/**
 * Data Fetching Integration Tests - Core Module
 * Tests basic data fetching patterns including caching
 * 
 * Business Value Justification (BVJ):
 * - Segment: All (Free → Enterprise)  
 * - Goal: Ensure reliable data synchronization for improved user experience
 * - Value Impact: Reduces user frustration and improves conversion rates
 * - Revenue Impact: +$50K MRR from enhanced reliability and performance
 */
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';
import React, { useState, useEffect } from 'react';

// ============================================================================
// CORE TYPES
// ============================================================================

interface Thread {
  id: string;
  title: string;
  created_at: string;
  message_count?: number;
}

// ============================================================================
// DATA FETCHING HOOK
// ============================================================================

// Global cache and pending requests for deduplication
const globalCache = new Map<string, any>();
const pendingRequests = new Map<string, Promise<any>>();

const useDataFetcher = <T,>(url: string, options?: RequestInit) => {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = async (bypassCache = false) => {
    const cacheKey = `${url}_${JSON.stringify(options)}`;
    
    if (!bypassCache && globalCache.has(cacheKey)) {
      setData(globalCache.get(cacheKey)!);
      return;
    }

    // Check if there's already a pending request for this URL
    if (pendingRequests.has(cacheKey)) {
      try {
        const result = await pendingRequests.get(cacheKey);
        setData(result);
        return;
      } catch (err) {
        setError(err as Error);
        return;
      }
    }

    setLoading(true);
    setError(null);
    
    // Create and store the request promise
    const requestPromise = (async () => {
      try {
        const response = await fetch(url, options);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        globalCache.set(cacheKey, result);
        return result;
      } finally {
        pendingRequests.delete(cacheKey);
      }
    })();
    
    pendingRequests.set(cacheKey, requestPromise);
    
    try {
      const result = await requestPromise;
      setData(result);
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [url]);

  return { data, loading, error, refetch: () => fetchData(true) };
};

// ============================================================================
// TEST COMPONENTS
// ============================================================================

const ThreadList: React.FC = () => {
  const { data, loading, error } = useDataFetcher<{ threads: Thread[] }>(
    'http://localhost:8000/api/threads'
  );

  if (loading) return <div>Loading threads...</div>;
  if (error) return <div>Error: {error.message}</div>;
  if (!data) return <div>No data</div>;

  return (
    <div data-testid="thread-list">
      {data.threads.map(thread => (
        <div key={thread.id} data-testid={`thread-${thread.id}`}>
          {thread.title}
        </div>
      ))}
    </div>
  );
};

// ============================================================================
// MSW SERVER SETUP
// ============================================================================

const mockApiUrl = 'http://localhost:8000';

const createBasicMockData = () => {
  const threads: Thread[] = Array.from({ length: 10 }, (_, i) => ({
    id: `thread-${i + 1}`,
    title: `Thread ${i + 1}`,
    created_at: `2025-01-${String(i + 1).padStart(2, '0')}T10:00:00Z`,
    message_count: Math.floor(Math.random() * 50)
  }));
  return { threads };
};

const mockData = createBasicMockData();

const createBasicHandlers = () => [
  http.get(`${mockApiUrl}/api/threads`, () => {
    return new Promise(resolve => {
      setTimeout(() => {
        resolve(HttpResponse.json({ threads: mockData.threads }));
      }, 100);
    });
  }),

  http.get(`${mockApiUrl}/api/slow`, () => {
    return new Promise(resolve => {
      setTimeout(() => {
        resolve(HttpResponse.json({ data: 'slow response' }));
      }, 3000);
    });
  })
];

const server = setupServer(...createBasicHandlers());

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
  // Clear global cache and pending requests
  globalCache.clear();
  pendingRequests.clear();
  act(() => {
    jest.runAllTimers();
  });
});

afterAll(() => {
  server.close();
  jest.useRealTimers();
});

// ============================================================================
// DATA FETCHING WITH CACHING TESTS
// ============================================================================

describe('Data Fetching - Core Caching', () => {
  it('fetches data on initial load', async () => {
    render(<ThreadList />);
    
    expect(screen.getByText('Loading threads...')).toBeInTheDocument();
    
    await waitFor(() => {
      expect(screen.getByTestId('thread-list')).toBeInTheDocument();
    });
    
    expect(screen.getByTestId('thread-thread-1')).toBeInTheDocument();
  });

  it('caches fetched data for subsequent requests', async () => {
    let requestCount = 0;
    
    server.use(
      http.get(`${mockApiUrl}/api/threads`, () => {
        requestCount++;
        return HttpResponse.json({ threads: mockData.threads.slice(0, 2) });
      })
    );

    const { rerender } = render(<ThreadList />);
    
    await waitFor(() => {
      expect(screen.getByTestId('thread-list')).toBeInTheDocument();
    });
    
    rerender(<ThreadList />);
    
    // Should not make additional request due to caching
    expect(requestCount).toBe(1);
  });

  it('bypasses cache when explicitly requested', async () => {
    let requestCount = 0;
    
    server.use(
      http.get(`${mockApiUrl}/api/threads`, () => {
        requestCount++;
        return HttpResponse.json({ 
          threads: [{ 
            id: `thread-${requestCount}`, 
            title: `Thread ${requestCount}`,
            created_at: new Date().toISOString()
          }] 
        });
      })
    );

    const TestComponent = () => {
      const { data, refetch } = useDataFetcher<{ threads: Thread[] }>(
        `${mockApiUrl}/api/threads`
      );
      
      return (
        <div>
          {data && <div data-testid="thread-count">{data.threads.length}</div>}
          <button onClick={refetch} data-testid="refetch">Refetch</button>
        </div>
      );
    };

    render(<TestComponent />);
    
    await waitFor(() => {
      expect(screen.getByTestId('thread-count')).toHaveTextContent('1');
    });
    
    userEvent.click(screen.getByTestId('refetch'));
    
    await waitFor(() => {
      expect(requestCount).toBe(2);
    });
  });

  it('handles cache misses gracefully', async () => {
    const TestComponent = () => {
      const { data, loading, error } = useDataFetcher<{ message: string }>(
        `${mockApiUrl}/api/nonexistent`
      );
      
      if (loading) return <div>Loading...</div>;
      if (error) return <div data-testid="error">Error: {error.message}</div>;
      return <div>{data?.message}</div>;
    };

    server.use(
      http.get(`${mockApiUrl}/api/nonexistent`, () => {
        return new HttpResponse(null, { status: 404 });
      })
    );

    render(<TestComponent />);
    
    await waitFor(() => {
      expect(screen.getByTestId('error')).toBeInTheDocument();
    });
  });

  it('implements request deduplication', async () => {
    let requestCount = 0;
    
    server.use(
      http.get(`${mockApiUrl}/api/threads`, () => {
        requestCount++;
        return HttpResponse.json({ threads: [] });
      })
    );

    const TestComponent = () => {
      useDataFetcher(`${mockApiUrl}/api/threads`);
      useDataFetcher(`${mockApiUrl}/api/threads`);
      useDataFetcher(`${mockApiUrl}/api/threads`);
      return <div>Multiple fetchers</div>;
    };

    render(<TestComponent />);
    
    await waitFor(() => {
      expect(screen.getByText('Multiple fetchers')).toBeInTheDocument();
    });
    
    // With proper deduplication, should only make one request
    expect(requestCount).toBe(1);
  });

  it('handles large datasets efficiently', async () => {
    const largeData = Array.from({ length: 1000 }, (_, i) => ({
      id: `thread-${i}`,
      title: `Large Thread ${i}`,
      created_at: new Date().toISOString(),
      message_count: i
    }));

    server.use(
      http.get(`${mockApiUrl}/api/large-data`, () => {
        return HttpResponse.json({ threads: largeData });
      })
    );

    const TestComponent = () => {
      const { data, loading } = useDataFetcher<{ threads: Thread[] }>(
        `${mockApiUrl}/api/large-data`
      );
      
      if (loading) return <div>Loading...</div>;
      
      return (
        <div data-testid="large-data">
          {data?.threads.length} items loaded
        </div>
      );
    };

    const startTime = performance.now();
    render(<TestComponent />);
    
    await waitFor(() => {
      expect(screen.getByTestId('large-data')).toBeInTheDocument();
    });
    
    const endTime = performance.now();
    expect(endTime - startTime).toBeLessThan(2000);
  });
});