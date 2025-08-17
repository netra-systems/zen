/**
 * Infrastructure Integration Test Utilities
 * Shared utilities for infrastructure layer testing
 * Enterprise segment - ensures platform reliability
 */

import WS from 'jest-websocket-mock';

export interface MockWebSocketConfig {
  url: string;
  autoConnect?: boolean;
}

export interface MockFetchConfig {
  ok: boolean;
  status?: number;
  data?: any;
  headers?: Record<string, string>;
}

export interface InfrastructureTestContext {
  mockWs: WS | null;
  cleanup: () => void;
}

/**
 * Setup WebSocket mock for infrastructure tests
 */
export const setupWebSocketMock = (config: MockWebSocketConfig): WS | null => {
  global.WebSocket = jest.fn(() => ({
    send: jest.fn(),
    close: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    readyState: 1,
    onmessage: null,
    onopen: null,
    onclose: null,
    onerror: null
  }));
  
  try {
    return new WS(config.url);
  } catch (error) {
    return null;
  }
};

/**
 * Setup fetch mock with configuration
 */
export const setupFetchMock = (config: MockFetchConfig): void => {
  const mockHeaders = new Headers();
  if (config.headers) {
    Object.entries(config.headers).forEach(([key, value]) => {
      mockHeaders.set(key, value);
    });
  }

  (global.fetch as jest.Mock).mockResolvedValueOnce({
    ok: config.ok,
    status: config.status || (config.ok ? 200 : 500),
    headers: mockHeaders,
    json: async () => config.data || {}
  });
};

/**
 * Clean WebSocket mock resources
 */
export const cleanWebSocketMock = (mockWs: WS | null): void => {
  try {
    if (mockWs) {
      WS.clean();
    }
  } catch (error) {
    // Clean gracefully
  }
};

/**
 * Initialize infrastructure test context
 */
export const initInfrastructureTest = (): InfrastructureTestContext => {
  const mockWs = setupWebSocketMock({ url: 'ws://localhost:8000/ws' });
  
  const cleanup = (): void => {
    cleanWebSocketMock(mockWs);
    jest.clearAllMocks();
  };

  return { mockWs, cleanup };
};

/**
 * Create mock transaction response
 */
export const createMockTransactionResponse = (success: boolean): MockFetchConfig => ({
  ok: success,
  data: { success, timestamp: Date.now() }
});

/**
 * Create mock cache response with headers
 */
export const createMockCacheResponse = (hit: boolean, data: any): MockFetchConfig => ({
  ok: true,
  data,
  headers: { 'X-Cache-Hit': hit.toString() }
});

/**
 * Create mock analytics response
 */
export const createMockAnalyticsResponse = (metrics: Record<string, any>): MockFetchConfig => ({
  ok: true,
  data: {
    total_requests: metrics.requests || 0,
    avg_response_time: metrics.responseTime || 0,
    ...metrics
  }
});

/**
 * Create mock task response
 */
export const createMockTaskResponse = (taskId: string): MockFetchConfig => ({
  ok: true,
  data: { task_id: taskId, status: 'queued' }
});

/**
 * Create mock error response
 */
export const createMockErrorResponse = (message: string, traceId?: string): MockFetchConfig => ({
  ok: false,
  status: 500,
  data: { 
    message, 
    trace_id: traceId || `trace-${Date.now()}`,
    timestamp: new Date().toISOString()
  }
});

/**
 * Wait for async operations in tests
 */
export const waitForAsyncOperation = (): Promise<void> => {
  return new Promise(resolve => requestAnimationFrame(() => resolve(undefined)));
};

/**
 * Simulate WebSocket message for testing
 */
export const simulateWebSocketMessage = (
  handler: (data: any) => void,
  message: any,
  delay: number = 100
): void => {
  const timeoutId = setTimeout(() => handler(message), delay);
  // Store timeout for potential cleanup
  (globalThis as any).__testTimeouts = (globalThis as any).__testTimeouts || [];
  (globalThis as any).__testTimeouts.push(timeoutId);
};

/**
 * Clean up test timeouts
 */
export const cleanTestTimeouts = (): void => {
  if ((globalThis as any).__testTimeouts) {
    (globalThis as any).__testTimeouts.forEach(clearTimeout);
    (globalThis as any).__testTimeouts = [];
  }
};