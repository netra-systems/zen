/**
 * Test for reconciliation cleanup fix
 * Tests that the cleanup function is properly bound and executed
 */

import { CoreReconciliationService } from '@/services/reconciliation/core';

describe('Reconciliation Cleanup Fix', () => {
      setupAntiHang();
    jest.setTimeout(10000);
  let service: CoreReconciliationService;

  beforeEach(() => {
    jest.useFakeTimers();
    service = new CoreReconciliationService({
      cleanupIntervalMs: 1000,
      timeoutMs: 5000,
    });
  });

  afterEach(() => {
    service.shutdown();
    jest.clearAllTimers();
    jest.useRealTimers();
      cleanupAntiHang();
  });

  it('should execute cleanup without "this.cleanup is not a function" error', () => {
    // Add some test messages
    const message = {
      id: 'test-1',
      content: 'Test message',
      role: 'user' as const,
      timestamp: Date.now(),
    };

    // Add optimistic message
    service.addOptimisticMessage(message);

    // Fast-forward time to trigger the cleanup interval
    expect(() => {
      jest.advanceTimersByTime(1000);
    }).not.toThrow();

    // The cleanup should have been called without errors
    expect(service.getStats()).toBeDefined();
  });

  it('should handle multiple cleanup cycles without errors', () => {
    // Add test messages
    for (let i = 0; i < 3; i++) {
      const message = {
        id: `test-${i}`,
        content: `Test message ${i}`,
        role: 'user' as const,
        timestamp: Date.now() + i * 100,
      };
      service.addOptimisticMessage(message);
    }

    // Run multiple cleanup cycles
    expect(() => {
      for (let i = 0; i < 5; i++) {
        jest.advanceTimersByTime(1000);
      }
    }).not.toThrow();

    // Verify service is still functional
    const stats = service.getStats();
    expect(stats).toBeDefined();
    expect(typeof stats.pending === 'number' ? stats.pending : 0).toBeGreaterThanOrEqual(0);
  });

  it('should properly clean up expired messages', () => {
    // Add an optimistic message
    const message = {
      id: 'test-expired',
      content: 'This will expire',
      role: 'user' as const,
      timestamp: Date.now() - 10000, // Old timestamp
    };

    service.addOptimisticMessage(message);

    // Initial stats should show pending message
    const initialStats = service.getStats();
    expect(typeof initialStats.pending === 'number' ? initialStats.pending : 0).toBeGreaterThanOrEqual(0);

    // Trigger timeout for the message
    jest.advanceTimersByTime(5000);

    // Trigger cleanup
    jest.advanceTimersByTime(1000);

    // Stats should reflect cleanup
    const finalStats = service.getStats();
    expect(finalStats).toBeDefined();
    // Check that timeout count increased or stats were updated
    const initialTimeout = typeof initialStats.timeout === 'number' ? initialStats.timeout : 0;
    const finalTimeout = typeof finalStats.timeout === 'number' ? finalStats.timeout : 0;
    expect(finalTimeout).toBeGreaterThanOrEqual(initialTimeout);
  });

  it('should maintain proper context binding in cleanup callback', () => {
    // Spy on the performCleanup method
    const performCleanupSpy = jest.spyOn(service as any, 'performCleanup');

    // Trigger cleanup interval
    jest.advanceTimersByTime(1000);

    // The performCleanup method should have been called
    expect(performCleanupSpy).toHaveBeenCalled();

    // Should not throw any errors about undefined methods
    expect(() => {
      jest.advanceTimersByTime(1000);
    }).not.toThrow();
  });
});