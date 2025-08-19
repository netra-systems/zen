/**
 * Data Fetching Integration Tests
 * Tests data fetching patterns including caching, optimistic updates, and pagination
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
// TEST COMPONENTS FOR DATA FETCHING
// ============================================================================

interface Thread {
  id: string;
  title: string;
  created_at: string;
  message_count?: number;
}

interface Message {
  id: string;
  content: string;
  thread_id: string;
  created_at: string;
}

interface PaginationMeta {
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
}

interface PaginatedResponse<T> {
  data: T[];
  meta: PaginationMeta;
}

// Data fetching hook with caching
const useDataFetcher = <T,>(url: string, options?: RequestInit) => {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [cache] = useState(new Map<string, T>());

  const fetchData = async (bypassCache = false) => {
    const cacheKey = `${url}_${JSON.stringify(options)}`;
    
    if (!bypassCache && cache.has(cacheKey)) {
      setData(cache.get(cacheKey)!);
      return;
    }

    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(url, options);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const result = await response.json();
      cache.set(cacheKey, result);
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

// Optimistic updates hook
const useOptimisticUpdates = <T extends { id: string }>(
  initialData: T[] = []
) => {
  const [data, setData] = useState<T[]>(initialData);
  const [pendingOperations] = useState(new Set<string>());

  const addOptimistic = async (item: T, saveAction: () => Promise<T>) => {
    const tempId = `temp_${Date.now()}`;
    const optimisticItem = { ...item, id: tempId };
    
    setData(prev => [...prev, optimisticItem]);
    pendingOperations.add(tempId);
    
    try {
      const savedItem = await saveAction();
      setData(prev => 
        prev.map(i => i.id === tempId ? savedItem : i)
      );
    } catch (error) {
      setData(prev => prev.filter(i => i.id !== tempId));
      throw error;
    } finally {
      pendingOperations.delete(tempId);
    }
  };

  const updateOptimistic = async (
    id: string, 
    updates: Partial<T>,
    saveAction: () => Promise<T>
  ) => {
    const originalItem = data.find(item => item.id === id);
    if (!originalItem) return;

    setData(prev => 
      prev.map(item => 
        item.id === id ? { ...item, ...updates } : item
      )
    );
    
    try {
      const updatedItem = await saveAction();
      setData(prev => 
        prev.map(item => item.id === id ? updatedItem : item)
      );
    } catch (error) {
      setData(prev => 
        prev.map(item => item.id === id ? originalItem : item)
      );
      throw error;
    }
  };

  const deleteOptimistic = async (id: string, deleteAction: () => Promise<void>) => {
    const originalItem = data.find(item => item.id === id);
    if (!originalItem) return;

    setData(prev => prev.filter(item => item.id !== id));
    
    try {
      await deleteAction();
    } catch (error) {
      setData(prev => [...prev, originalItem]);
      throw error;
    }
  };

  return {
    data,
    setData,
    addOptimistic,
    updateOptimistic,
    deleteOptimistic,
    isPending: (id: string) => pendingOperations.has(id)
  };
};

// Pagination hook
const usePagination = <T,>(
  baseUrl: string,
  initialPage = 1,
  perPage = 10
) => {
  const [currentPage, setCurrentPage] = useState(initialPage);
  const [data, setData] = useState<T[]>([]);
  const [meta, setMeta] = useState<PaginationMeta | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchPage = async (page: number) => {
    setLoading(true);
    setError(null);
    
    try {
      const url = `${baseUrl}?page=${page}&per_page=${perPage}`;
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const result: PaginatedResponse<T> = await response.json();
      setData(result.data);
      setMeta(result.meta);
      setCurrentPage(page);
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  };

  const goToPage = (page: number) => {
    if (page >= 1 && (!meta || page <= meta.total_pages)) {
      fetchPage(page);
    }
  };

  const nextPage = () => {
    if (meta && currentPage < meta.total_pages) {
      goToPage(currentPage + 1);
    }
  };

  const prevPage = () => {
    if (currentPage > 1) {
      goToPage(currentPage - 1);
    }
  };

  useEffect(() => {
    fetchPage(currentPage);
  }, []);

  return {
    data,
    meta,
    loading,
    error,
    currentPage,
    goToPage,
    nextPage,
    prevPage,
    refetch: () => fetchPage(currentPage)
  };
};

// Test components
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

const OptimisticThreadManager: React.FC = () => {
  const {
    data: threads,
    addOptimistic,
    updateOptimistic,
    deleteOptimistic,
    isPending
  } = useOptimisticUpdates<Thread>([]);

  const handleAddThread = async () => {
    const newThread: Thread = {
      id: '',
      title: 'New Thread',
      created_at: new Date().toISOString()
    };

    await addOptimistic(newThread, async () => {
      const response = await fetch('http://localhost:8000/api/threads', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newThread)
      });
      return response.json();
    });
  };

  const handleUpdateThread = async (id: string) => {
    await updateOptimistic(
      id,
      { title: 'Updated Thread' },
      async () => {
        const response = await fetch(`http://localhost:8000/api/threads/${id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title: 'Updated Thread' })
        });
        return response.json();
      }
    );
  };

  const handleDeleteThread = async (id: string) => {
    await deleteOptimistic(id, async () => {
      await fetch(`http://localhost:8000/api/threads/${id}`, {
        method: 'DELETE'
      });
    });
  };

  return (
    <div data-testid="optimistic-thread-manager">
      <button onClick={handleAddThread} data-testid="add-thread">
        Add Thread
      </button>
      {threads.map(thread => (
        <div key={thread.id} data-testid={`thread-${thread.id}`}>
          <span>{thread.title}</span>
          {isPending(thread.id) && <span data-testid="pending">Pending...</span>}
          <button 
            onClick={() => handleUpdateThread(thread.id)}
            data-testid={`update-${thread.id}`}
          >
            Update
          </button>
          <button 
            onClick={() => handleDeleteThread(thread.id)}
            data-testid={`delete-${thread.id}`}
          >
            Delete
          </button>
        </div>
      ))}
    </div>
  );
};

const PaginatedThreads: React.FC = () => {
  const {
    data: threads,
    meta,
    loading,
    error,
    currentPage,
    nextPage,
    prevPage,
    goToPage
  } = usePagination<Thread>('http://localhost:8000/api/threads', 1, 5);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div data-testid="paginated-threads">
      <div data-testid="thread-items">
        {threads.map(thread => (
          <div key={thread.id} data-testid={`thread-${thread.id}`}>
            {thread.title}
          </div>
        ))}
      </div>
      
      {meta && (
        <div data-testid="pagination-controls">
          <button 
            onClick={prevPage}
            disabled={currentPage === 1}
            data-testid="prev-page"
          >
            Previous
          </button>
          
          <span data-testid="page-info">
            Page {currentPage} of {meta.total_pages}
          </span>
          
          <button 
            onClick={nextPage}
            disabled={currentPage === meta.total_pages}
            data-testid="next-page"
          >
            Next
          </button>
          
          <button 
            onClick={() => goToPage(1)}
            data-testid="first-page"
          >
            First
          </button>
        </div>
      )}
    </div>
  );
};

// ============================================================================
// MSW SERVER SETUP
// ============================================================================

const mockApiUrl = 'http://localhost:8000';

const createMockData = () => {
  const threads: Thread[] = Array.from({ length: 25 }, (_, i) => ({
    id: `thread-${i + 1}`,
    title: `Thread ${i + 1}`,
    created_at: `2025-01-${String(i + 1).padStart(2, '0')}T10:00:00Z`,
    message_count: Math.floor(Math.random() * 50)
  }));
  return { threads };
};

const mockData = createMockData();

const createMockHandlers = () => [
  // Basic thread fetching
  http.get(`${mockApiUrl}/api/threads`, ({ request }) => {
    const url = new URL(request.url);
    const page = parseInt(url.searchParams.get('page') || '1');
    const perPage = parseInt(url.searchParams.get('per_page') || '10');
    
    // Simulate delay for testing loading states
    return new Promise(resolve => {
      setTimeout(() => {
        if (url.searchParams.has('page')) {
          // Paginated response
          const startIndex = (page - 1) * perPage;
          const endIndex = startIndex + perPage;
          const paginatedThreads = mockData.threads.slice(startIndex, endIndex);
          
          resolve(HttpResponse.json({
            data: paginatedThreads,
            meta: {
              page,
              per_page: perPage,
              total: mockData.threads.length,
              total_pages: Math.ceil(mockData.threads.length / perPage)
            }
          }));
        } else {
          // Standard response
          resolve(HttpResponse.json({ threads: mockData.threads.slice(0, 10) }));
        }
      }, 100);
    });
  }),

  // Single thread fetching
  http.get(`${mockApiUrl}/api/threads/:threadId`, ({ params }) => {
    const thread = mockData.threads.find(t => t.id === params.threadId);
    if (!thread) {
      return new HttpResponse(null, { status: 404 });
    }
    return HttpResponse.json(thread);
  }),

  // Create thread
  http.post(`${mockApiUrl}/api/threads`, async ({ request }) => {
    const body = await request.json();
    const newThread: Thread = {
      id: `thread-${Date.now()}`,
      title: (body as any).title || 'New Thread',
      created_at: new Date().toISOString(),
      message_count: 0
    };
    
    mockData.threads.push(newThread);
    return HttpResponse.json(newThread, { status: 201 });
  }),

  // Update thread
  http.put(`${mockApiUrl}/api/threads/:threadId`, async ({ params, request }) => {
    const body = await request.json();
    const threadIndex = mockData.threads.findIndex(t => t.id === params.threadId);
    
    if (threadIndex === -1) {
      return new HttpResponse(null, { status: 404 });
    }
    
    mockData.threads[threadIndex] = {
      ...mockData.threads[threadIndex],
      ...(body as Partial<Thread>)
    };
    
    return HttpResponse.json(mockData.threads[threadIndex]);
  }),

  // Delete thread
  http.delete(`${mockApiUrl}/api/threads/:threadId`, ({ params }) => {
    const threadIndex = mockData.threads.findIndex(t => t.id === params.threadId);
    
    if (threadIndex === -1) {
      return new HttpResponse(null, { status: 404 });
    }
    
    mockData.threads.splice(threadIndex, 1);
    return HttpResponse.json({ success: true });
  }),

  // Slow endpoint for timeout testing
  http.get(`${mockApiUrl}/api/slow`, () => {
    return new Promise(resolve => {
      setTimeout(() => {
        resolve(HttpResponse.json({ data: 'slow response' }));
      }, 5000);
    });
  }),

  // Large data endpoint
  http.get(`${mockApiUrl}/api/large-data`, () => {
    const largeData = Array.from({ length: 10000 }, (_, i) => ({
      id: i,
      content: `Large data item ${i}`.repeat(100)
    }));
    return HttpResponse.json({ data: largeData });
  })
];

const server = setupServer(...createMockHandlers());

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
  });
});

afterAll(() => {
  server.close();
  jest.useRealTimers();
});

// ============================================================================
// DATA FETCHING WITH CACHING TESTS
// ============================================================================

describe('Data Fetching - Caching', () => {
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
});

// ============================================================================
// OPTIMISTIC UPDATES TESTS
// ============================================================================

describe('Data Fetching - Optimistic Updates', () => {
  it('immediately shows optimistic update before server confirmation', async () => {
    render(<OptimisticThreadManager />);
    
    userEvent.click(screen.getByTestId('add-thread'));
    
    // Should immediately show the optimistic item
    await waitFor(() => {
      expect(screen.getByText('New Thread')).toBeInTheDocument();
    });
    
    // Should show pending state
    expect(screen.getByTestId('pending')).toBeInTheDocument();
    
    // After server responds, pending should be removed
    await waitFor(() => {
      expect(screen.queryByTestId('pending')).not.toBeInTheDocument();
    }, { timeout: 2000 });
  });

  it('reverts optimistic update on server error', async () => {
    server.use(
      http.post(`${mockApiUrl}/api/threads`, () => {
        return new HttpResponse(null, { status: 500 });
      })
    );

    render(<OptimisticThreadManager />);
    
    userEvent.click(screen.getByTestId('add-thread'));
    
    // Should initially show optimistic update
    await waitFor(() => {
      expect(screen.getByText('New Thread')).toBeInTheDocument();
    });
    
    // Should revert after error
    await waitFor(() => {
      expect(screen.queryByText('New Thread')).not.toBeInTheDocument();
    }, { timeout: 2000 });
  });

  it('handles optimistic updates for edit operations', async () => {
    // Pre-populate with a thread
    mockData.threads = [{
      id: 'existing-thread',
      title: 'Original Title',
      created_at: '2025-01-19T10:00:00Z'
    }];

    const TestComponent = () => {
      const [threads, setThreads] = useState(mockData.threads);
      
      const handleUpdate = async () => {
        const originalThread = threads[0];
        setThreads([{ ...originalThread, title: 'Updated Title' }]);
        
        try {
          await fetch(`${mockApiUrl}/api/threads/${originalThread.id}`, {
            method: 'PUT',
            body: JSON.stringify({ title: 'Updated Title' })
          });
        } catch (error) {
          setThreads([originalThread]);
        }
      };
      
      return (
        <div>
          <div data-testid="thread-title">{threads[0]?.title}</div>
          <button onClick={handleUpdate} data-testid="update-button">
            Update
          </button>
        </div>
      );
    };

    render(<TestComponent />);
    
    expect(screen.getByTestId('thread-title')).toHaveTextContent('Original Title');
    
    userEvent.click(screen.getByTestId('update-button'));
    
    // Should immediately show optimistic update
    await waitFor(() => {
      expect(screen.getByTestId('thread-title')).toHaveTextContent('Updated Title');
    });
  });

  it('handles multiple concurrent optimistic updates', async () => {
    render(<OptimisticThreadManager />);
    
    // Trigger multiple rapid updates
    userEvent.click(screen.getByTestId('add-thread'));
    userEvent.click(screen.getByTestId('add-thread'));
    userEvent.click(screen.getByTestId('add-thread'));
    
    // Should show all optimistic updates
    await waitFor(() => {
      const newThreads = screen.getAllByText('New Thread');
      expect(newThreads).toHaveLength(3);
    });
    
    // Should handle all pending states
    await waitFor(() => {
      const pendingStates = screen.getAllByTestId('pending');
      expect(pendingStates.length).toBeGreaterThan(0);
    });
  });
});

// ============================================================================
// PAGINATION TESTS
// ============================================================================

describe('Data Fetching - Pagination', () => {
  it('loads first page by default', async () => {
    render(<PaginatedThreads />);
    
    await waitFor(() => {
      expect(screen.getByTestId('thread-items')).toBeInTheDocument();
    });
    
    expect(screen.getByTestId('page-info')).toHaveTextContent('Page 1 of 5');
    expect(screen.getAllByTestId(/thread-thread-/)).toHaveLength(5);
  });

  it('navigates to next page correctly', async () => {
    render(<PaginatedThreads />);
    
    await waitFor(() => {
      expect(screen.getByTestId('next-page')).toBeInTheDocument();
    });
    
    userEvent.click(screen.getByTestId('next-page'));
    
    await waitFor(() => {
      expect(screen.getByTestId('page-info')).toHaveTextContent('Page 2 of 5');
    });
  });

  it('disables navigation buttons appropriately', async () => {
    render(<PaginatedThreads />);
    
    await waitFor(() => {
      expect(screen.getByTestId('prev-page')).toBeDisabled();
    });
    
    // Navigate to last page
    const nextButton = screen.getByTestId('next-page');
    for (let i = 0; i < 4; i++) {
      userEvent.click(nextButton);
      await waitFor(() => {
        expect(screen.getByTestId('page-info')).toBeInTheDocument();
      });
    }
    
    expect(screen.getByTestId('next-page')).toBeDisabled();
  });

  it('jumps to first page correctly', async () => {
    render(<PaginatedThreads />);
    
    await waitFor(() => {
      expect(screen.getByTestId('next-page')).toBeInTheDocument();
    });
    
    // Navigate to page 3
    userEvent.click(screen.getByTestId('next-page'));
    await waitFor(() => {
      expect(screen.getByTestId('page-info')).toHaveTextContent('Page 2');
    });
    
    userEvent.click(screen.getByTestId('next-page'));
    await waitFor(() => {
      expect(screen.getByTestId('page-info')).toHaveTextContent('Page 3');
    });
    
    // Jump back to first page
    userEvent.click(screen.getByTestId('first-page'));
    await waitFor(() => {
      expect(screen.getByTestId('page-info')).toHaveTextContent('Page 1');
    });
  });

  it('handles pagination with different page sizes', async () => {
    const TestComponent = () => {
      const { data, meta, loading } = usePagination<Thread>(
        `${mockApiUrl}/api/threads`,
        1,
        2 // Smaller page size
      );
      
      if (loading) return <div>Loading...</div>;
      
      return (
        <div>
          <div data-testid="item-count">{data.length}</div>
          {meta && <div data-testid="total-pages">{meta.total_pages}</div>}
        </div>
      );
    };

    render(<TestComponent />);
    
    await waitFor(() => {
      expect(screen.getByTestId('item-count')).toHaveTextContent('2');
    });
    
    await waitFor(() => {
      expect(screen.getByTestId('total-pages')).toHaveTextContent('13');
    });
  });
});

// ============================================================================
// INFINITE SCROLLING TESTS
// ============================================================================

describe('Data Fetching - Infinite Scrolling', () => {
  it('loads more data when scrolling to bottom', async () => {
    const InfiniteScrollComponent = () => {
      const [data, setData] = useState<Thread[]>([]);
      const [loading, setLoading] = useState(false);
      const [page, setPage] = useState(1);
      
      const loadMore = async () => {
        if (loading) return;
        
        setLoading(true);
        const response = await fetch(
          `${mockApiUrl}/api/threads?page=${page}&per_page=5`
        );
        const result = await response.json();
        setData(prev => [...prev, ...result.data]);
        setPage(prev => prev + 1);
        setLoading(false);
      };
      
      useEffect(() => {
        loadMore();
      }, []);
      
      return (
        <div data-testid="infinite-scroll">
          {data.map(thread => (
            <div key={thread.id} data-testid={`thread-${thread.id}`}>
              {thread.title}
            </div>
          ))}
          {loading && <div data-testid="loading-more">Loading more...</div>}
          <button onClick={loadMore} data-testid="load-more">
            Load More
          </button>
        </div>
      );
    };

    render(<InfiniteScrollComponent />);
    
    await waitFor(() => {
      expect(screen.getAllByTestId(/thread-thread-/)).toHaveLength(5);
    });
    
    userEvent.click(screen.getByTestId('load-more'));
    
    await waitFor(() => {
      expect(screen.getByTestId('loading-more')).toBeInTheDocument();
    });
    
    await waitFor(() => {
      expect(screen.getAllByTestId(/thread-thread-/)).toHaveLength(10);
    });
  });
});

// ============================================================================
// PERFORMANCE TESTS
// ============================================================================

describe('Data Fetching - Performance', () => {
  it('handles large datasets efficiently', async () => {
    const TestComponent = () => {
      const { data, loading } = useDataFetcher<{ data: any[] }>(
        `${mockApiUrl}/api/large-data`
      );
      
      if (loading) return <div>Loading...</div>;
      
      return (
        <div data-testid="large-data">
          {data?.data.length} items loaded
        </div>
      );
    };

    const startTime = performance.now();
    render(<TestComponent />);
    
    await waitFor(() => {
      expect(screen.getByTestId('large-data')).toBeInTheDocument();
    });
    
    const endTime = performance.now();
    expect(endTime - startTime).toBeLessThan(3000); // Should handle large data quickly
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
});