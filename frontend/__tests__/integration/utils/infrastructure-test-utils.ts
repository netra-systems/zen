/**
 * Infrastructure Test Utilities
 * Common utilities for infrastructure-related tests
 */

export function initInfrastructureTest() {
  // Initialize infrastructure test environment
  return {
    cleanup: () => {
      // Cleanup logic
    },
  };
}

export function setupFetchMock() {
  const mockFetch = jest.fn();
  global.fetch = mockFetch;
  
  return {
    mockFetch,
    restore: () => {
      // Restore original fetch if needed
    },
  };
}

export function createMockAnalyticsResponse(data: any = {}) {
  return {
    ok: true,
    status: 200,
    json: () => Promise.resolve({
      data,
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