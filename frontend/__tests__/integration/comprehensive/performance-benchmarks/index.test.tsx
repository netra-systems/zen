import './render-performance.test';
import './interaction-latency.test';
import './resource-utilization.test';
import './concurrent-performance.test';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
 backward compatibility while leveraging modular test architecture.
 */

// Import all test suites to maintain backward compatibility
import './render-performance.test';
import './interaction-latency.test';
import './resource-utilization.test';
import './concurrent-performance.test';

/**
 * This index file maintains backward compatibility by importing all 
 * performance benchmark test modules. The original 701-line file has been 
 * split into focused modules:
 * 
 * - render-performance.test.tsx (render times, re-renders, virtual scrolling)
 * - interaction-latency.test.tsx (user interactions, computations, debouncing)
 * - resource-utilization.test.tsx (memory, bundle size, DOM management)  
 * - concurrent-performance.test.tsx (concurrent updates, priorities)
 * - performance-test-helpers.tsx (shared utilities and components)
 * 
 * Each module is ≤300 lines and follows the CLAUDE.md architecture requirements.
 */

describe('Performance Benchmarks Integration Tests Suite', () => {
    jest.setTimeout(10000);
  it('should load all performance test modules', () => {
    // This test ensures all modules are properly imported
    expect(true).toBe(true);
  });
});

// Re-export helpers for external use
export * from './performance-test-helpers';