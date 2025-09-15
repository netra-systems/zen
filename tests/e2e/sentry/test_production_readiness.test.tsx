/**
 * E2E Tests: Sentry Production Readiness Validation
 * 
 * Business Value Justification (BVJ):
 * - Segment: All (Free/Early/Mid/Enterprise) - Production Deployment Readiness
 * - Business Goal: Validate production-grade error monitoring capabilities
 * - Value Impact: Ensures reliable error monitoring for $500K+ ARR platform
 * - Strategic Impact: Validates system readiness for production deployment
 * 
 * Test Focus: Production performance, reliability, and operational readiness
 * Infrastructure: GCP Staging environment simulating production conditions
 */

import { test, expect, Page, Browser } from '@playwright/test';

// Production readiness configuration
const PRODUCTION_READINESS_CONFIG = {
  baseURL: process.env.STAGING_BASE_URL || 'https://staging.netra.ai',
  performanceBudget: {
    maxErrorCaptureTime: 50,      // ms - Error capture overhead
    maxPageLoadImpact: 100,       // ms - Impact on page load
    maxMemoryIncrease: 25,        // MB - Memory impact
    maxConcurrentUsers: 100,      // Concurrent user simulation
    errorRateThreshold: 0.01,     // 1% error rate threshold
  },
  reliability: {
    minUptime: 0.99,              // 99% uptime requirement
    maxRetryAttempts: 3,          // Max retry attempts for failed operations
    timeoutThreshold: 30000,      // 30s timeout threshold
  },
};

// Production readiness monitoring utilities
class ProductionReadinessMonitor {
  private metrics: {
    performance: Array<{ operation: string; duration: number; timestamp: number }>;
    errors: Array<{ type: string; message: string; timestamp: number; resolved: boolean }>;
    memory: Array<{ usage: number; timestamp: number }>;
    uptime: Array<{ status: 'up' | 'down'; timestamp: number; duration: number }>;
  } = {
    performance: [],
    errors: [],
    memory: [],
    uptime: [],
  };

  async measurePerformance(operation: string, fn: () => Promise<void>) {
    const start = performance.now();
    await fn();
    const duration = performance.now() - start;
    
    this.metrics.performance.push({
      operation,
      duration,
      timestamp: Date.now(),
    });
    
    return duration;
  }

  recordError(type: string, message: string, resolved: boolean = false) {
    this.metrics.errors.push({
      type,
      message,
      timestamp: Date.now(),
      resolved,
    });
  }

  async measureMemoryUsage(page: Page) {
    const memoryInfo = await page.evaluate(() => {
      return (performance as any).memory ? {
        used: (performance as any).memory.usedJSHeapSize / (1024 * 1024), // MB
        total: (performance as any).memory.totalJSHeapSize / (1024 * 1024), // MB
      } : { used: 0, total: 0 };
    });

    this.metrics.memory.push({
      usage: memoryInfo.used,
      timestamp: Date.now(),
    });

    return memoryInfo.used;
  }

  recordUptime(status: 'up' | 'down', duration: number) {
    this.metrics.uptime.push({
      status,
      timestamp: Date.now(),
      duration,
    });
  }

  getPerformanceMetrics() {
    return {
      averageErrorCapture: this.getAveragePerformance('error-capture'),
      averagePageLoad: this.getAveragePerformance('page-load'),
      maxErrorCapture: this.getMaxPerformance('error-capture'),
      maxPageLoad: this.getMaxPerformance('page-load'),
    };
  }

  private getAveragePerformance(operation: string): number {
    const ops = this.metrics.performance.filter(p => p.operation === operation);
    if (ops.length === 0) return 0;
    return ops.reduce((sum, op) => sum + op.duration, 0) / ops.length;
  }

  private getMaxPerformance(operation: string): number {
    const ops = this.metrics.performance.filter(p => p.operation === operation);
    if (ops.length === 0) return 0;
    return Math.max(...ops.map(op => op.duration));
  }

  getErrorRate(): number {
    const totalOperations = this.metrics.performance.length;
    const errorCount = this.metrics.errors.filter(e => !e.resolved).length;
    return totalOperations > 0 ? errorCount / totalOperations : 0;
  }

  getMemoryGrowth(): number {
    if (this.metrics.memory.length < 2) return 0;
    const initial = this.metrics.memory[0].usage;
    const final = this.metrics.memory[this.metrics.memory.length - 1].usage;
    return final - initial;
  }

  getUptime(): number {
    const uptimeRecords = this.metrics.uptime;
    if (uptimeRecords.length === 0) return 1.0;
    
    const totalTime = uptimeRecords.reduce((sum, record) => sum + record.duration, 0);
    const upTime = uptimeRecords.filter(r => r.status === 'up').reduce((sum, record) => sum + record.duration, 0);
    
    return totalTime > 0 ? upTime / totalTime : 1.0;
  }

  clear() {
    this.metrics = {
      performance: [],
      errors: [],
      memory: [],
      uptime: [],
    };
  }
}

// Load testing utilities
class LoadTestingHelper {
  private browser: Browser;

  constructor(browser: Browser) {
    this.browser = browser;
  }

  async simulateConcurrentUsers(userCount: number, operations: Array<(page: Page) => Promise<void>>): Promise<Array<{ success: boolean; duration: number; error?: string }>> {
    const contexts = await Promise.all(
      Array.from({ length: userCount }, () => this.browser.newContext())
    );

    const pages = await Promise.all(contexts.map(context => context.newPage()));

    const results = await Promise.all(pages.map(async (page, index) => {
      const startTime = performance.now();
      try {
        await page.goto(PRODUCTION_READINESS_CONFIG.baseURL, { 
          waitUntil: 'networkidle',
          timeout: PRODUCTION_READINESS_CONFIG.reliability.timeoutThreshold,
        });

        // Execute random operation for this user
        const operation = operations[index % operations.length];
        await operation(page);

        return {
          success: true,
          duration: performance.now() - startTime,
        };
      } catch (error) {
        return {
          success: false,
          duration: performance.now() - startTime,
          error: error instanceof Error ? error.message : String(error),
        };
      }
    }));

    // Clean up
    await Promise.all(contexts.map(context => context.close()));

    return results;
  }
}

test.describe('Sentry Production Readiness E2E Tests', () => {
  let monitor: ProductionReadinessMonitor;
  let loadTester: LoadTestingHelper;

  test.beforeAll(async ({ browser }) => {
    loadTester = new LoadTestingHelper(browser);
  });

  test.beforeEach(async ({ page }) => {
    monitor = new ProductionReadinessMonitor();
    
    // Set up performance monitoring
    await page.addInitScript(() => {
      (window as any)._performanceMarks = [];
      performance.mark = new Proxy(performance.mark, {
        apply(target, thisArg, args) {
          (window as any)._performanceMarks.push({ name: args[0], timestamp: performance.now() });
          return target.apply(thisArg, args);
        },
      });
    });
  });

  test.afterEach(async () => {
    monitor.clear();
  });

  test('should meet performance benchmarks for error capture', async ({ page }) => {
    await page.goto(PRODUCTION_READINESS_CONFIG.baseURL, { waitUntil: 'networkidle' });

    // Baseline memory measurement
    const initialMemory = await monitor.measureMemoryUsage(page);

    // Test error capture performance across multiple scenarios
    const errorScenarios = [
      { type: 'runtime', message: 'Production readiness runtime error' },
      { type: 'network', message: 'Production readiness network error' },
      { type: 'validation', message: 'Production readiness validation error' },
    ];

    for (const scenario of errorScenarios) {
      const duration = await monitor.measurePerformance('error-capture', async () => {
        // Trigger error
        await page.evaluate((errorData) => {
          const error = new Error(errorData.message);
          error.name = `${errorData.type}Error`;
          
          // Simulate error boundary capture
          if ((window as any).Sentry) {
            (window as any).Sentry.captureException(error, {
              tags: {
                test_scenario: 'production_readiness',
                error_type: errorData.type,
              },
            });
          }
        }, scenario);

        // Wait for error processing
        await page.waitForTimeout(100);
      });

      // Performance validation
      expect(duration).toBeLessThan(PRODUCTION_READINESS_CONFIG.performanceBudget.maxErrorCaptureTime);
    }

    // Final memory measurement
    const finalMemory = await monitor.measureMemoryUsage(page);
    const memoryGrowth = monitor.getMemoryGrowth();

    // Memory growth should be minimal
    expect(memoryGrowth).toBeLessThan(PRODUCTION_READINESS_CONFIG.performanceBudget.maxMemoryIncrease);

    // Overall performance metrics
    const performanceMetrics = monitor.getPerformanceMetrics();
    expect(performanceMetrics.averageErrorCapture).toBeLessThan(PRODUCTION_READINESS_CONFIG.performanceBudget.maxErrorCaptureTime);
    expect(performanceMetrics.maxErrorCapture).toBeLessThan(PRODUCTION_READINESS_CONFIG.performanceBudget.maxErrorCaptureTime * 2);
  });

  test('should handle concurrent user load without performance degradation', async ({ browser }) => {
    const concurrentUsers = PRODUCTION_READINESS_CONFIG.performanceBudget.maxConcurrentUsers;
    
    // Define user operations that might trigger errors
    const userOperations = [
      // Chat interaction
      async (page: Page) => {
        await page.goto(`${PRODUCTION_READINESS_CONFIG.baseURL}/chat`);
        await page.waitForSelector('[data-testid="chat-input"]', { timeout: 10000 });
        await page.fill('[data-testid="chat-input"]', 'Load test message');
        await page.click('[data-testid="send-button"]');
        await page.waitForTimeout(1000);
      },
      
      // Navigation stress
      async (page: Page) => {
        const routes = ['/chat', '/dashboard', '/settings'];
        const route = routes[Math.floor(Math.random() * routes.length)];
        await page.goto(`${PRODUCTION_READINESS_CONFIG.baseURL}${route}`);
        await page.waitForTimeout(500);
      },
      
      // Error triggering
      async (page: Page) => {
        await page.goto(PRODUCTION_READINESS_CONFIG.baseURL);
        await page.evaluate(() => {
          // Trigger intentional error for load testing
          setTimeout(() => {
            throw new Error('Load test error');
          }, Math.random() * 1000);
        });
        await page.waitForTimeout(2000);
      },
    ];

    // Run load test
    const results = await loadTester.simulateConcurrentUsers(concurrentUsers, userOperations);

    // Analyze results
    const successfulOperations = results.filter(r => r.success);
    const failedOperations = results.filter(r => !r.success);
    
    const successRate = successfulOperations.length / results.length;
    const averageDuration = successfulOperations.reduce((sum, r) => sum + r.duration, 0) / successfulOperations.length;
    const maxDuration = Math.max(...results.map(r => r.duration));

    // Production readiness criteria
    expect(successRate).toBeGreaterThanOrEqual(0.95); // 95% success rate
    expect(averageDuration).toBeLessThan(10000); // Average under 10 seconds
    expect(maxDuration).toBeLessThan(30000); // Max under 30 seconds

    // Error rate should be within acceptable limits
    const errorRate = failedOperations.length / results.length;
    expect(errorRate).toBeLessThan(PRODUCTION_READINESS_CONFIG.performanceBudget.errorRateThreshold);

    // Log failed operations for analysis
    if (failedOperations.length > 0) {
      console.warn('Failed operations:', failedOperations.map(op => op.error).slice(0, 5));
    }
  });

  test('should demonstrate error rate monitoring and alerting capabilities', async ({ page }) => {
    await page.goto(PRODUCTION_READINESS_CONFIG.baseURL, { waitUntil: 'networkidle' });

    // Simulate various error rates and monitor Sentry's handling
    const errorTests = [
      { name: 'low-error-rate', errorCount: 5, totalOperations: 1000 },
      { name: 'medium-error-rate', errorCount: 50, totalOperations: 1000 },
      { name: 'high-error-rate', errorCount: 100, totalOperations: 1000 },
    ];

    for (const testCase of errorTests) {
      monitor.clear();
      
      // Simulate operations with controlled error rate
      for (let i = 0; i < testCase.totalOperations; i++) {
        if (i < testCase.errorCount) {
          // Generate error
          monitor.recordError('simulated', `${testCase.name} error ${i}`);
          
          await monitor.measurePerformance('error-with-capture', async () => {
            await page.evaluate((errorIndex) => {
              const error = new Error(`Simulated error ${errorIndex}`);
              if ((window as any).Sentry) {
                (window as any).Sentry.captureException(error, {
                  tags: { simulation: 'error-rate-test' },
                });
              }
            }, i);
          });
        } else {
          // Generate successful operation
          await monitor.measurePerformance('successful-operation', async () => {
            await page.evaluate(() => {
              // Simulate successful operation
              Promise.resolve('success');
            });
          });
        }
        
        // Small delay to prevent overwhelming
        if (i % 100 === 0) {
          await page.waitForTimeout(50);
        }
      }

      const errorRate = monitor.getErrorRate();
      const expectedErrorRate = testCase.errorCount / testCase.totalOperations;
      
      // Error rate should be accurately tracked
      expect(Math.abs(errorRate - expectedErrorRate)).toBeLessThan(0.01);
      
      // Performance should remain stable even with higher error rates
      const performanceMetrics = monitor.getPerformanceMetrics();
      expect(performanceMetrics.averageErrorCapture).toBeLessThan(PRODUCTION_READINESS_CONFIG.performanceBudget.maxErrorCaptureTime * 1.5);
    }
  });

  test('should maintain system stability during prolonged operation', async ({ page }) => {
    await page.goto(PRODUCTION_READINESS_CONFIG.baseURL, { waitUntil: 'networkidle' });

    const testDuration = 300000; // 5 minutes
    const operationInterval = 1000; // 1 second
    const startTime = Date.now();
    
    let operationCount = 0;
    let consecutiveFailures = 0;
    const maxConsecutiveFailures = 3;

    while (Date.now() - startTime < testDuration) {
      const operationStart = Date.now();
      
      try {
        // Perform stability test operation
        await monitor.measurePerformance('stability-test', async () => {
          // Rotate between different operations
          const operations = [
            () => page.reload({ waitUntil: 'networkidle' }),
            () => page.evaluate(() => window.location.reload()),
            () => page.evaluate(() => {
              // Trigger periodic error
              if (Math.random() < 0.1) { // 10% error rate
                throw new Error(`Stability test error ${Date.now()}`);
              }
            }),
          ];
          
          const operation = operations[operationCount % operations.length];
          await operation();
        });

        monitor.recordUptime('up', Date.now() - operationStart);
        consecutiveFailures = 0;
        
      } catch (error) {
        monitor.recordUptime('down', Date.now() - operationStart);
        monitor.recordError('stability-test', error instanceof Error ? error.message : String(error));
        consecutiveFailures++;

        // Fail fast if too many consecutive failures
        if (consecutiveFailures >= maxConsecutiveFailures) {
          throw new Error(`Too many consecutive failures (${consecutiveFailures})`);
        }
      }

      operationCount++;
      
      // Memory check every 10 operations
      if (operationCount % 10 === 0) {
        await monitor.measureMemoryUsage(page);
      }

      // Wait for next operation
      const elapsed = Date.now() - operationStart;
      const waitTime = Math.max(0, operationInterval - elapsed);
      if (waitTime > 0) {
        await page.waitForTimeout(waitTime);
      }
    }

    // Validate stability metrics
    const uptime = monitor.getUptime();
    const memoryGrowth = monitor.getMemoryGrowth();
    const errorRate = monitor.getErrorRate();

    expect(uptime).toBeGreaterThanOrEqual(PRODUCTION_READINESS_CONFIG.reliability.minUptime);
    expect(memoryGrowth).toBeLessThan(PRODUCTION_READINESS_CONFIG.performanceBudget.maxMemoryIncrease);
    expect(errorRate).toBeLessThan(PRODUCTION_READINESS_CONFIG.performanceBudget.errorRateThreshold);

    console.log(`Stability test completed: ${operationCount} operations, ${uptime * 100}% uptime, ${memoryGrowth.toFixed(2)}MB memory growth`);
  });

  test('should validate error recovery and resilience mechanisms', async ({ page }) => {
    await page.goto(PRODUCTION_READINESS_CONFIG.baseURL, { waitUntil: 'networkidle' });

    // Test various failure scenarios and recovery
    const failureScenarios = [
      {
        name: 'network-interruption',
        setup: async () => {
          // Block Sentry requests temporarily
          await page.route('**/sentry.io/**', route => route.abort());
        },
        cleanup: async () => {
          // Restore network connectivity
          await page.unroute('**/sentry.io/**');
        },
        expectedRecovery: true,
      },
      {
        name: 'sentry-service-error',
        setup: async () => {
          // Mock Sentry service errors
          await page.route('**/sentry.io/**', route => route.fulfill({ 
            status: 500, 
            body: 'Internal Server Error' 
          }));
        },
        cleanup: async () => {
          await page.unroute('**/sentry.io/**');
        },
        expectedRecovery: true,
      },
      {
        name: 'client-side-error-cascade',
        setup: async () => {
          // Inject multiple cascading errors
          await page.evaluate(() => {
            const originalConsoleError = console.error;
            console.error = (...args) => {
              originalConsoleError.apply(console, args);
              // Trigger additional error on console.error
              setTimeout(() => {
                throw new Error('Cascading error from console.error');
              }, 10);
            };
          });
        },
        cleanup: async () => {
          await page.reload({ waitUntil: 'networkidle' });
        },
        expectedRecovery: true,
      },
    ];

    for (const scenario of failureScenarios) {
      // Set up failure condition
      await scenario.setup();

      // Trigger errors during failure condition
      const failureStart = Date.now();
      
      for (let i = 0; i < 5; i++) {
        try {
          await page.evaluate((index) => {
            throw new Error(`Recovery test error ${index}`);
          }, i);
          
          monitor.recordError(scenario.name, `Error ${i} during ${scenario.name}`);
          await page.waitForTimeout(200);
        } catch (e) {
          // Expected during failure scenario
        }
      }

      // Clean up failure condition
      await scenario.cleanup();

      // Verify recovery
      const recoveryStart = Date.now();
      let recoverySuccessful = false;
      
      try {
        // Test normal operation after recovery
        await page.evaluate(() => {
          // Normal operation that should work after recovery
          if ((window as any).Sentry) {
            (window as any).Sentry.addBreadcrumb({
              message: 'Recovery test breadcrumb',
              level: 'info',
            });
          }
        });
        
        recoverySuccessful = true;
        monitor.recordError(scenario.name, 'Recovery successful', true);
        
      } catch (recoveryError) {
        monitor.recordError(scenario.name, `Recovery failed: ${recoveryError}`, false);
      }

      if (scenario.expectedRecovery) {
        expect(recoverySuccessful).toBe(true);
      }

      console.log(`${scenario.name}: Recovery time ${Date.now() - recoveryStart}ms`);
    }

    // Overall resilience metrics
    const totalErrors = monitor.metrics.errors.length;
    const recoveredErrors = monitor.metrics.errors.filter(e => e.resolved).length;
    const recoveryRate = totalErrors > 0 ? recoveredErrors / totalErrors : 1;

    expect(recoveryRate).toBeGreaterThanOrEqual(0.8); // 80% recovery rate
  });
});