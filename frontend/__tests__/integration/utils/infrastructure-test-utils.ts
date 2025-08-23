/**
 * Infrastructure Test Utilities
 * Common utilities for infrastructure-related tests
 */

export interface InfrastructureTestContext {
  cleanup: () => void;
}

export function initInfrastructureTest(): InfrastructureTestContext {
  // Initialize infrastructure test environment
  return {
    cleanup: () => {
      jest.clearAllMocks();
      // Restore fetch if it was mocked
      if (global.fetch && 'mockRestore' in global.fetch) {
        (global.fetch as any).mockRestore();
      }
    },
  };
}

export function setupFetchMock(response?: any) {
  const mockFetch = jest.fn();
  
  if (response) {
    if (typeof response.json === 'function') {
      // Response object with json method - use as is
      mockFetch.mockResolvedValue(response);
    } else if (response.ok !== undefined) {
      // Response-like object - already has ok, status etc.
      mockFetch.mockResolvedValue({
        ...response,
        json: () => Promise.resolve(response.data || response),
      });
    } else {
      // Data object - wrap in response
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve(response),
      });
    }
  } else {
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({}),
    });
  }
  
  global.fetch = mockFetch;
  
  return {
    mockFetch,
    restore: () => {
      if ('mockRestore' in mockFetch) {
        mockFetch.mockRestore();
      }
    },
  };
}

export function createMockAnalyticsResponse(data: any = {}) {
  return {
    ok: true,
    status: 200,
    json: () => Promise.resolve({
      total_requests: data.requests || 0,
      avg_response_time: data.responseTime || 0,
      status: 'success',
      timestamp: Date.now(),
    }),
  };
}

export function createMockClickHouseResponse(rows: any[] = []) {
  return {
    ok: true,
    status: 200,
    json: () => Promise.resolve({
      data: rows,
      rows: rows.length,
      statistics: {
        elapsed: 0.001,
        rows_read: rows.length,
        bytes_read: rows.length * 100,
      },
    }),
  };
}

export function setupMockDatabase() {
  return {
    query: jest.fn().mockResolvedValue([]),
    close: jest.fn(),
    isConnected: jest.fn().mockReturnValue(true),
  };
}

export function createMockMetrics() {
  return {
    requests_total: 100,
    response_time_avg: 50,
    error_rate: 0.01,
    active_connections: 10,
  };
}

export function setupInfrastructureMonitoring() {
  return {
    startMonitoring: jest.fn(),
    stopMonitoring: jest.fn(),
    getMetrics: jest.fn().mockReturnValue(createMockMetrics()),
  };
}

export async function waitForAsyncOperation(delay: number = 100): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, delay));
}

export function createRetryableOperation(maxRetries: number = 3) {
  let attempts = 0;
  
  return async () => {
    attempts++;
    
    if (attempts < maxRetries) {
      throw new Error(`Attempt ${attempts} failed`);
    }
    
    return { attempts, success: true };
  };
}

export function createExponentialBackoff(baseDelay: number = 100) {
  return (attempt: number) => baseDelay * Math.pow(2, attempt);
}

export function createJitterFunction(maxJitter: number = 100) {
  return () => Math.random() * maxJitter;
}