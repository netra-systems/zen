/**
 * Centralized Jest timeout configuration
 * SSOT for all test timeout values across the frontend test suite
 */

export const TEST_TIMEOUTS = {
  // Default timeout for most tests
  DEFAULT: 10000,
  
  // Short timeout for fast unit tests
  UNIT: 5000,
  
  // Standard timeout for integration tests
  INTEGRATION: 15000,
  
  // Long timeout for E2E tests
  E2E: 30000,
  
  // Extra long timeout for performance tests
  PERFORMANCE: 60000,
  
  // Timeout for WebSocket connection tests
  WEBSOCKET: 10000,
  
  // Timeout for async operations
  ASYNC_OPERATION: 8000,
  
  // Timeout for API calls
  API_CALL: 10000,
  
  // Timeout for visual/rendering tests
  VISUAL: 10000,
  
  // Timeout for cross-browser tests
  CROSS_BROWSER: 10000,
  
  // Timeout for load tests
  LOAD_TEST: 45000,
} as const;

/**
 * Helper function to set Jest timeout for a test suite
 * Call this in beforeAll() or at the top of describe() blocks
 */
export function setTestTimeout(timeout: number = TEST_TIMEOUTS.DEFAULT): void {
  jest.setTimeout(timeout);
}

/**
 * Helper to set timeout for specific test categories
 */
export function setTimeoutForCategory(category: keyof typeof TEST_TIMEOUTS): void {
  jest.setTimeout(TEST_TIMEOUTS[category]);
}

/**
 * Decorator for setting timeout on individual test functions
 * Usage: @withTimeout(TEST_TIMEOUTS.E2E)
 */
export function withTimeout(timeout: number) {
  return function (target: any, propertyKey: string, descriptor: PropertyDescriptor) {
    const originalMethod = descriptor.value;
    descriptor.value = async function (...args: any[]) {
      const originalTimeout = jasmine.DEFAULT_TIMEOUT_INTERVAL || jest.setTimeout;
      jest.setTimeout(timeout);
      try {
        return await originalMethod.apply(this, args);
      } finally {
        jest.setTimeout(originalTimeout as number);
      }
    };
    return descriptor;
  };
}

/**
 * Helper to wrap test functions with custom timeout
 */
export function testWithTimeout(
  name: string,
  fn: jest.ProvidesCallback,
  timeout: number = TEST_TIMEOUTS.DEFAULT
): void {
  test(name, fn, timeout);
}

/**
 * Helper for async test with timeout
 */
export function itWithTimeout(
  name: string,
  fn: jest.ProvidesCallback,
  timeout: number = TEST_TIMEOUTS.DEFAULT
): void {
  it(name, fn, timeout);
}

// Export a setup function that can be called in jest.setup.js
export function setupGlobalTestTimeout(timeout: number = TEST_TIMEOUTS.DEFAULT): void {
  jest.setTimeout(timeout);
}