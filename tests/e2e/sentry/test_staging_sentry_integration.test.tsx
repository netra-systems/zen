/**
 * E2E Tests: Staging Sentry Integration
 * 
 * Business Value Justification (BVJ):
 * - Segment: All (Free/Early/Mid/Enterprise) - Production Readiness
 * - Business Goal: Validate real Sentry error collection in staging environment
 * - Value Impact: Ensures reliable error monitoring before production deployment
 * - Strategic Impact: Validates complete error workflow in production-like environment
 * 
 * Test Focus: Real Sentry error collection and staging environment validation
 * Infrastructure: GCP Staging environment with real Sentry instance
 */

import { test, expect, Page, Browser } from '@playwright/test';

// Configuration for staging environment tests
const STAGING_CONFIG = {
  baseURL: process.env.STAGING_BASE_URL || 'https://staging.netra.ai',
  timeout: 30000,
  retries: 2,
  viewport: { width: 1280, height: 720 },
};

// Sentry integration utilities for E2E testing
class SentryE2EHelper {
  private page: Page;
  private capturedErrors: Array<any> = [];
  
  constructor(page: Page) {
    this.page = page;
  }

  async interceptSentryRequests() {
    // Intercept Sentry API calls to validate they're being made
    await this.page.route('**/sentry.io/**', async (route) => {
      const request = route.request();
      const response = await route.fetch();
      
      this.capturedErrors.push({
        url: request.url(),
        method: request.method(),
        headers: request.headers(),
        postData: request.postData(),
        timestamp: Date.now(),
        status: response.status(),
      });
      
      await route.fulfill({ response });
    });

    // Also intercept internal error API
    await this.page.route('**/api/errors', async (route) => {
      const request = route.request();
      const postData = request.postData();
      
      if (postData) {
        this.capturedErrors.push({
          url: request.url(),
          method: request.method(),
          data: JSON.parse(postData),
          timestamp: Date.now(),
          type: 'internal_api',
        });
      }
      
      await route.continue();
    });
  }

  getCapturedErrors() {
    return this.capturedErrors;
  }

  async clearCapturedErrors() {
    this.capturedErrors = [];
  }

  async triggerTestError(errorType: 'runtime' | 'network' | 'validation' = 'runtime') {
    // Inject JavaScript to trigger specific types of errors
    await this.page.evaluate((type) => {
      switch (type) {
        case 'runtime':
          // Trigger a runtime error
          setTimeout(() => {
            throw new Error('E2E Test Runtime Error - Sentry Integration Validation');
          }, 100);
          break;
        case 'network':
          // Trigger a network error
          fetch('/nonexistent-endpoint').catch(() => {
            throw new Error('E2E Test Network Error - Sentry Integration Validation');
          });
          break;
        case 'validation':
          // Trigger a validation error
          const form = document.querySelector('form');
          if (form) {
            form.dispatchEvent(new Event('submit'));
          } else {
            throw new Error('E2E Test Validation Error - Sentry Integration Validation');
          }
          break;
      }
    }, errorType);
  }

  async waitForErrorCapture(timeout: number = 5000): Promise<boolean> {
    const startTime = Date.now();
    
    while (Date.now() - startTime < timeout) {
      if (this.capturedErrors.length > 0) {
        return true;
      }
      await this.page.waitForTimeout(100);
    }
    
    return false;
  }

  async validateSentryConfiguration() {
    // Check if Sentry is properly initialized
    return await this.page.evaluate(() => {
      return !!(window as any).Sentry && typeof (window as any).Sentry.captureException === 'function';
    });
  }
}

// Performance monitoring utilities
class PerformanceMonitor {
  private measurements: Array<{ name: string; value: number; timestamp: number }> = [];

  async measureOperation(page: Page, operationName: string, operation: () => Promise<void>) {
    const startTime = performance.now();
    await operation();
    const endTime = performance.now();
    
    this.measurements.push({
      name: operationName,
      value: endTime - startTime,
      timestamp: Date.now(),
    });
  }

  getAverageDuration(operationName: string): number {
    const ops = this.measurements.filter(m => m.name === operationName);
    if (ops.length === 0) return 0;
    return ops.reduce((sum, op) => sum + op.value, 0) / ops.length;
  }

  getMaxDuration(operationName: string): number {
    const ops = this.measurements.filter(m => m.name === operationName);
    if (ops.length === 0) return 0;
    return Math.max(...ops.map(op => op.value));
  }

  clear() {
    this.measurements = [];
  }
}

test.describe('Staging Sentry Integration E2E Tests', () => {
  let sentryHelper: SentryE2EHelper;
  let performanceMonitor: PerformanceMonitor;

  test.beforeEach(async ({ page }) => {
    sentryHelper = new SentryE2EHelper(page);
    performanceMonitor = new PerformanceMonitor();
    
    // Set up Sentry request interception
    await sentryHelper.interceptSentryRequests();
    
    // Navigate to staging application
    await page.goto(STAGING_CONFIG.baseURL, { 
      waitUntil: 'networkidle',
      timeout: STAGING_CONFIG.timeout,
    });
  });

  test.afterEach(async () => {
    await sentryHelper.clearCapturedErrors();
    performanceMonitor.clear();
  });

  test('should initialize Sentry in staging environment', async ({ page }) => {
    // Verify Sentry is loaded and configured
    const sentryInitialized = await sentryHelper.validateSentryConfiguration();
    expect(sentryInitialized).toBe(true);

    // Check for Sentry configuration in browser
    const sentryConfig = await page.evaluate(() => {
      return {
        hasSentry: !!(window as any).Sentry,
        hasCapture: typeof (window as any).Sentry?.captureException === 'function',
        environment: process.env.NEXT_PUBLIC_ENVIRONMENT,
        dsn: process.env.NEXT_PUBLIC_SENTRY_DSN ? 'configured' : 'missing',
      };
    });

    expect(sentryConfig.hasSentry).toBe(true);
    expect(sentryConfig.hasCapture).toBe(true);
    expect(sentryConfig.environment).toBe('staging');
    expect(sentryConfig.dsn).toBe('configured');
  });

  test('should capture runtime errors and send to Sentry', async ({ page }) => {
    // Performance measurement for error capture
    await performanceMonitor.measureOperation(page, 'error-capture', async () => {
      // Trigger a test runtime error
      await sentryHelper.triggerTestError('runtime');
      
      // Wait for error to be captured and sent
      const errorCaptured = await sentryHelper.waitForErrorCapture(10000);
      expect(errorCaptured).toBe(true);
    });

    const capturedErrors = sentryHelper.getCapturedErrors();
    
    // Validate error was sent to Sentry
    const sentryErrors = capturedErrors.filter(error => error.url.includes('sentry.io'));
    expect(sentryErrors.length).toBeGreaterThan(0);

    // Validate error contains expected data
    const firstError = sentryErrors[0];
    expect(firstError.method).toBe('POST');
    expect(firstError.status).toBe(200);

    // Performance validation - error capture should be under 50ms
    const captureTime = performanceMonitor.getAverageDuration('error-capture');
    expect(captureTime).toBeLessThan(50);
  });

  test('should handle WebSocket errors during agent execution', async ({ page }) => {
    // Navigate to chat interface
    await page.goto(`${STAGING_CONFIG.baseURL}/chat`, { 
      waitUntil: 'networkidle' 
    });

    // Wait for WebSocket connection
    await page.waitForFunction(() => {
      return (window as any).WebSocket && 
             document.readyState === 'complete';
    }, { timeout: 10000 });

    // Simulate WebSocket error by disrupting connection
    await page.evaluate(() => {
      // Find existing WebSocket connections and close them abruptly
      const originalWebSocket = (window as any).WebSocket;
      (window as any).WebSocket = class extends originalWebSocket {
        constructor(...args: any[]) {
          super(...args);
          // Simulate connection failure after a brief delay
          setTimeout(() => {
            if (this.readyState === this.OPEN) {
              this.close(1006, 'E2E Test WebSocket Error');
            }
          }, 500);
        }
      };
    });

    // Try to send a message that should trigger WebSocket error
    await page.fill('[data-testid="chat-input"]', 'Test message for WebSocket error');
    await page.click('[data-testid="send-button"]');

    // Wait for WebSocket error to be captured
    const errorCaptured = await sentryHelper.waitForErrorCapture(15000);
    expect(errorCaptured).toBe(true);

    const capturedErrors = sentryHelper.getCapturedErrors();
    const websocketErrors = capturedErrors.filter(error => 
      error.data?.error?.includes('WebSocket') || 
      error.data?.context?.component === 'websocket'
    );
    
    expect(websocketErrors.length).toBeGreaterThan(0);
  });

  test('should capture errors across multiple user sessions', async ({ browser }) => {
    const contexts = await Promise.all([
      browser.newContext(),
      browser.newContext(),
      browser.newContext(),
    ]);

    const pages = await Promise.all(contexts.map(context => context.newPage()));
    const helpers = pages.map(page => new SentryE2EHelper(page));

    // Set up error interception for all pages
    await Promise.all(helpers.map(helper => helper.interceptSentryRequests()));

    // Navigate all pages to staging
    await Promise.all(pages.map(page => 
      page.goto(STAGING_CONFIG.baseURL, { waitUntil: 'networkidle' })
    ));

    // Trigger errors in each session
    await Promise.all(helpers.map((helper, index) => 
      helper.triggerTestError('runtime')
    ));

    // Wait for all errors to be captured
    const captureResults = await Promise.all(
      helpers.map(helper => helper.waitForErrorCapture(10000))
    );

    expect(captureResults.every(captured => captured)).toBe(true);

    // Validate session isolation
    const allCapturedErrors = helpers.map(helper => helper.getCapturedErrors());
    
    // Each session should capture its own errors
    expect(allCapturedErrors.every(errors => errors.length > 0)).toBe(true);

    // Clean up
    await Promise.all(contexts.map(context => context.close()));
  });

  test('should maintain performance under error reporting load', async ({ page }) => {
    const performanceBudget = {
      maxErrorCaptureTime: 50, // ms
      maxPageLoadImpact: 100,  // ms
      maxMemoryIncrease: 50,   // MB
    };

    // Measure baseline performance
    const baselineStart = await page.evaluate(() => performance.now());
    await page.reload({ waitUntil: 'networkidle' });
    const baselineEnd = await page.evaluate(() => performance.now());
    const baselineLoadTime = baselineEnd - baselineStart;

    // Generate multiple errors rapidly
    const errorCount = 10;
    const errorPromises = [];

    for (let i = 0; i < errorCount; i++) {
      errorPromises.push(
        performanceMonitor.measureOperation(page, 'rapid-error', async () => {
          await sentryHelper.triggerTestError('runtime');
          await page.waitForTimeout(100); // Brief delay between errors
        })
      );
    }

    await Promise.all(errorPromises);

    // Measure performance after errors
    const afterErrorsStart = await page.evaluate(() => performance.now());
    await page.reload({ waitUntil: 'networkidle' });
    const afterErrorsEnd = await page.evaluate(() => performance.now());
    const afterErrorsLoadTime = afterErrorsEnd - afterErrorsStart;

    // Validate performance impact
    const loadTimeImpact = afterErrorsLoadTime - baselineLoadTime;
    expect(loadTimeImpact).toBeLessThan(performanceBudget.maxPageLoadImpact);

    const avgErrorCaptureTime = performanceMonitor.getAverageDuration('rapid-error');
    expect(avgErrorCaptureTime).toBeLessThan(performanceBudget.maxErrorCaptureTime);

    // Check memory usage (basic check)
    const memoryInfo = await page.evaluate(() => {
      return (performance as any).memory ? {
        used: (performance as any).memory.usedJSHeapSize,
        total: (performance as any).memory.totalJSHeapSize,
      } : null;
    });

    if (memoryInfo) {
      // Memory should not grow excessively (basic heuristic)
      expect(memoryInfo.used / (1024 * 1024)).toBeLessThan(100); // Under 100MB
    }
  });

  test('should prevent multiple instance conflicts in staging', async ({ page }) => {
    // Navigate to application
    await page.goto(STAGING_CONFIG.baseURL, { waitUntil: 'networkidle' });

    // Check initial Sentry state
    const initialSentryState = await page.evaluate(() => ({
      hasSentry: !!(window as any).Sentry,
      initCount: (window as any)._sentryInitCount || 0,
    }));

    expect(initialSentryState.hasSentry).toBe(true);

    // Try to trigger multiple initializations (should be prevented)
    await page.evaluate(() => {
      // Simulate multiple SentryInit component mounts
      for (let i = 0; i < 5; i++) {
        try {
          // Try to initialize multiple times
          const script = document.createElement('script');
          script.textContent = `
            if (window.Sentry) {
              console.log('Sentry already initialized, preventing duplicate');
            }
          `;
          document.head.appendChild(script);
        } catch (e) {
          console.warn('Prevented duplicate initialization:', e);
        }
      }
    });

    // Wait for any potential side effects
    await page.waitForTimeout(2000);

    // Verify no conflicts occurred
    const finalSentryState = await page.evaluate(() => ({
      hasSentry: !!(window as any).Sentry,
      errors: (window as any).console?.errors || [],
    }));

    expect(finalSentryState.hasSentry).toBe(true);
    
    // Check for multiple instance error messages
    const consoleErrors = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('*')).some(el => 
        el.textContent?.includes('multiple instance') ||
        el.textContent?.includes('Already initialized')
      );
    });

    expect(consoleErrors).toBe(false);
  });

  test('should validate environment-specific configuration in staging', async ({ page }) => {
    // Check Sentry configuration matches staging requirements
    const sentryConfig = await page.evaluate(() => {
      const config = (window as any)?._sentryConfig || {};
      return {
        environment: config.environment,
        dsn: config.dsn ? config.dsn.includes('staging') : null,
        debug: config.debug,
        tracesSampleRate: config.tracesSampleRate,
        profilesSampleRate: config.profilesSampleRate,
      };
    });

    // Validate staging-specific configuration
    expect(sentryConfig.environment).toBe('staging');
    expect(sentryConfig.debug).toBe(false);
    expect(sentryConfig.tracesSampleRate).toBeGreaterThan(0);
    expect(sentryConfig.tracesSampleRate).toBeLessThanOrEqual(1);

    // Staging should have higher sample rates than production
    expect(sentryConfig.tracesSampleRate).toBeGreaterThanOrEqual(0.1);
  });

  test('should handle network failures gracefully', async ({ page }) => {
    // Navigate to application
    await page.goto(STAGING_CONFIG.baseURL, { waitUntil: 'networkidle' });

    // Block Sentry requests to simulate network failure
    await page.route('**/sentry.io/**', route => route.abort());

    // Trigger an error
    await sentryHelper.triggerTestError('network');

    // Wait for retry attempts
    await page.waitForTimeout(5000);

    // Application should continue functioning despite Sentry failures
    const appStillWorking = await page.evaluate(() => {
      return document.readyState === 'complete' && 
             !document.body.textContent?.includes('Application Error');
    });

    expect(appStillWorking).toBe(true);

    // Check if errors were queued for retry
    const queuedErrors = await page.evaluate(() => {
      return localStorage.getItem('chat_error_queue');
    });

    expect(queuedErrors).toBeDefined();
    if (queuedErrors) {
      const queue = JSON.parse(queuedErrors);
      expect(Array.isArray(queue)).toBe(true);
      expect(queue.length).toBeGreaterThan(0);
    }
  });
});