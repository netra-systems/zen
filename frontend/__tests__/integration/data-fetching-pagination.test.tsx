/**
 * Data Fetching Integration Tests - Pagination Module
 * Tests pagination and infinite scrolling patterns
 * 
 * Business Value Justification (BVJ):
 * - Segment: Mid and Enterprise (handling large datasets)  
 * - Goal: Enable efficient handling of large data volumes
 * - Value Impact: Improves performance for power users
 * - Revenue Impact: +$50K MRR from enhanced enterprise features
 */
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';
import React, { useState, useEffect } from 'react';

// ============================================================================
// PAGINATION TYPES
// ============================================================================

interface Thread {
  id: string;
  title: string;
  created_at: string;
  message_count?: number;
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

// ============================================================================
// PAGINATION HOOK
// ============================================================================

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

// ============================================================================
// TEST COMPONENTS
// ============================================================================

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

const InfiniteScrollComponent: React.FC = () => {
  const [data, setData] = useState<Thread[]>([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  
  const loadMore = async () => {
    if (loading) return;
    
    setLoading(true);
    const response = await fetch(
      `http://localhost:8000/api/threads?page=${page}&per_page=5`
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

// ============================================================================
// MSW SERVER SETUP
// ============================================================================

const mockApiUrl = 'http://localhost:8000';

const createPaginationMockData = () => {
  const threads: Thread[] = Array.from({ length: 25 }, (_, i) => ({
    id: `thread-${i + 1}`,
    title: `Thread ${i + 1}`,
    created_at: `2025-01-${String(i + 1).padStart(2, '0')}T10:00:00Z`,
    message_count: Math.floor(Math.random() * 50)
  }));
  return { threads };
};

const mockData = createPaginationMockData();

const createPaginationHandlers = () => [
  http.get(`${mockApiUrl}/api/threads`, ({ request }) => {
    const url = new URL(request.url);
    const page = parseInt(url.searchParams.get('page') || '1');
    const perPage = parseInt(url.searchParams.get('per_page') || '10');
    
    // Simulate delay for testing loading states
    return new Promise(resolve => {
      setTimeout(() => {
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
      }, 100);
    });
  })
];

const server = setupServer(...createPaginationHandlers());

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

  it('prevents duplicate loading requests', async () => {
    let requestCount = 0;
    
    server.use(
      http.get(`${mockApiUrl}/api/threads`, ({ request }) => {
        const url = new URL(request.url);
        const page = parseInt(url.searchParams.get('page') || '1');
        requestCount++;
        
        return HttpResponse.json({
          data: [{
            id: `thread-${page}`,
            title: `Thread ${page}`,
            created_at: new Date().toISOString()
          }],
          meta: { page, per_page: 1, total: 10, total_pages: 10 }
        });
      })
    );

    render(<InfiniteScrollComponent />);
    
    await waitFor(() => {
      expect(screen.getByTestId('load-more')).toBeInTheDocument();
    });
    
    // Rapid clicks should be debounced
    userEvent.click(screen.getByTestId('load-more'));
    userEvent.click(screen.getByTestId('load-more'));
    userEvent.click(screen.getByTestId('load-more'));
    
    await waitFor(() => {
      expect(requestCount).toBeLessThanOrEqual(2);
    });
  });
});