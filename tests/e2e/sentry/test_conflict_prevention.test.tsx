/**
 * E2E Tests: Sentry Multiple Instance Conflict Prevention
 * 
 * Business Value Justification (BVJ):
 * - Segment: All (Free/Early/Mid/Enterprise) - System Reliability
 * - Business Goal: Prevent original "multiple instance" errors that caused Sentry disabling
 * - Value Impact: Ensures stable error monitoring without system conflicts
 * - Strategic Impact: Validates resolution of core issue that blocked Sentry deployment
 * 
 * Test Focus: Multiple instance prevention and environment boundary enforcement
 * Infrastructure: GCP Staging environment with conflict simulation
 */

import { test, expect, Page, Browser } from '@playwright/test';

// Conflict prevention test configuration
const CONFLICT_PREVENTION_CONFIG = {
  baseURL: process.env.STAGING_BASE_URL || 'https://staging.netra.ai',
  testScenarios: {
    rapidMounting: { iterations: 10, delay: 100 },
    multiTab: { tabCount: 5, operationsPerTab: 3 },
    environmentSwitching: { switchCount: 5, delay: 500 },
  },
  timeouts: {
    operation: 10000,
    stabilization: 2000,
    verification: 5000,
  },
};

// Multiple instance detection utilities
class MultipleInstanceDetector {
  private detectedConflicts: Array<{
    type: string;
    timestamp: number;
    details: any;
    severity: 'low' | 'medium' | 'high' | 'critical';
  }> = [];

  async detectConflicts(page: Page): Promise<boolean> {
    const conflictIndicators = await page.evaluate(() => {
      const indicators = {
        multipleSentryInstances: false,
        conflictingEventListeners: false,
        duplicateInitialization: false,
        memoryLeaks: false,
        errorMessages: [],
        consoleWarnings: [],
      };

      // Check for multiple Sentry instances
      const sentryInstanceCount = Object.keys(window).filter(key => 
        key.includes('Sentry') || key.includes('sentry')
      ).length;

      if (sentryInstanceCount > 1) {
        indicators.multipleSentryInstances = true;
      }

      // Check for conflicting error handlers
      const errorHandlerCount = (window as any)._errorHandlerCount || 0;
      if (errorHandlerCount > 1) {
        indicators.conflictingEventListeners = true;
      }

      // Check for initialization conflicts
      const initCount = (window as any)._sentryInitCount || 0;
      if (initCount > 1) {
        indicators.duplicateInitialization = true;
      }

      // Check console for conflict-related messages
      const consoleMessages = (window as any)._consoleMessages || [];
      indicators.errorMessages = consoleMessages.filter((msg: string) => 
        msg.includes('multiple instance') || 
        msg.includes('already initialized') ||
        msg.includes('conflict')
      );

      indicators.consoleWarnings = consoleMessages.filter((msg: string) =>
        msg.includes('warn') && (
          msg.includes('sentry') || 
          msg.includes('duplicate') ||
          msg.includes('instance')
        )
      );

      return indicators;
    });

    // Record any detected conflicts
    if (conflictIndicators.multipleSentryInstances) {
      this.recordConflict('multiple_sentry_instances', conflictIndicators, 'critical');
    }

    if (conflictIndicators.conflictingEventListeners) {
      this.recordConflict('conflicting_event_listeners', conflictIndicators, 'high');
    }

    if (conflictIndicators.duplicateInitialization) {
      this.recordConflict('duplicate_initialization', conflictIndicators, 'high');
    }

    if (conflictIndicators.errorMessages.length > 0) {
      this.recordConflict('error_messages', conflictIndicators.errorMessages, 'medium');
    }

    return this.hasConflicts();
  }

  private recordConflict(type: string, details: any, severity: 'low' | 'medium' | 'high' | 'critical') {
    this.detectedConflicts.push({
      type,
      timestamp: Date.now(),
      details,
      severity,
    });
  }

  hasConflicts(): boolean {
    return this.detectedConflicts.length > 0;
  }

  getCriticalConflicts(): Array<any> {
    return this.detectedConflicts.filter(c => c.severity === 'critical');
  }

  getAllConflicts(): Array<any> {
    return [...this.detectedConflicts];
  }

  clear() {
    this.detectedConflicts = [];
  }
}

// Environment boundary testing utilities
class EnvironmentBoundaryTester {
  async testEnvironmentIsolation(page: Page, environments: string[]): Promise<{
    isolated: boolean;
    crossContamination: boolean;
    details: any;
  }> {
    const results = {
      isolated: true,
      crossContamination: false,
      details: {} as any,
    };

    for (const env of environments) {
      // Simulate environment switch
      await page.evaluate((environment) => {
        // Mock environment change
        process.env.NEXT_PUBLIC_ENVIRONMENT = environment;
        (window as any)._testEnvironment = environment;
      }, env);

      // Check if previous environment configuration persists
      const envState = await page.evaluate(() => {
        return {
          currentEnv: (window as any)._testEnvironment,
          sentryConfig: (window as any)._sentryConfig || {},
          persistedData: Object.keys(localStorage).filter(key => 
            key.includes('sentry') || key.includes('environment')
          ),
        };
      });

      results.details[env] = envState;

      // Check for cross-contamination
      if (envState.persistedData.length > 0) {
        results.crossContamination = true;
        results.isolated = false;
      }
    }

    return results;
  }
}

test.describe('Sentry Multiple Instance Conflict Prevention E2E Tests', () => {
  let conflictDetector: MultipleInstanceDetector;
  let boundaryTester: EnvironmentBoundaryTester;

  test.beforeEach(async ({ page }) => {
    conflictDetector = new MultipleInstanceDetector();
    boundaryTester = new EnvironmentBoundaryTester();

    // Set up conflict detection instrumentation
    await page.addInitScript(() => {
      // Track console messages for conflict analysis
      (window as any)._consoleMessages = [];
      const originalConsole = {
        log: console.log,
        warn: console.warn,
        error: console.error,
      };

      ['log', 'warn', 'error'].forEach(method => {
        console[method as keyof Console] = (...args: any[]) => {
          (window as any)._consoleMessages.push(`${method}: ${args.join(' ')}`);
          originalConsole[method as keyof typeof originalConsole].apply(console, args);
        };
      });

      // Track Sentry initialization attempts
      (window as any)._sentryInitCount = 0;
      (window as any)._errorHandlerCount = 0;

      // Monkey patch potential conflict sources
      const originalAddEventListener = window.addEventListener;
      window.addEventListener = function(type, listener, options) {
        if (type === 'error' || type === 'unhandledrejection') {
          (window as any)._errorHandlerCount = ((window as any)._errorHandlerCount || 0) + 1;
        }
        return originalAddEventListener.call(this, type, listener, options);
      };
    });

    // Navigate to application
    await page.goto(CONFLICT_PREVENTION_CONFIG.baseURL, { 
      waitUntil: 'networkidle',
      timeout: CONFLICT_PREVENTION_CONFIG.timeouts.operation,
    });
  });

  test.afterEach(async () => {
    conflictDetector.clear();
  });

  test('should prevent multiple instance conflicts during rapid component mounting', async ({ page }) => {
    // Simulate rapid SentryInit component mounting/unmounting
    for (let i = 0; i < CONFLICT_PREVENTION_CONFIG.testScenarios.rapidMounting.iterations; i++) {
      // Simulate component mount
      await page.evaluate((iteration) => {
        // Try to initialize Sentry multiple times rapidly
        if ((window as any).Sentry) {
          try {
            // Attempt multiple initializations
            const mockConfig = {
              dsn: 'https://test@sentry.io/123',
              environment: 'staging',
            };
            
            // This should be prevented by the existing instance check
            if (!(window as any).Sentry.isInitialized || !(window as any).Sentry.isInitialized()) {
              (window as any)._sentryInitCount = ((window as any)._sentryInitCount || 0) + 1;
            }
          } catch (error) {
            console.warn(`Prevented duplicate initialization ${iteration}:`, error);
          }
        }
      }, i);

      // Brief delay between mount attempts
      await page.waitForTimeout(CONFLICT_PREVENTION_CONFIG.testScenarios.rapidMounting.delay);

      // Check for conflicts after each iteration
      const hasConflicts = await conflictDetector.detectConflicts(page);
      if (hasConflicts) {
        break; // Stop if conflicts detected
      }
    }

    // Final conflict check
    const hasConflicts = await conflictDetector.detectConflicts(page);
    expect(hasConflicts).toBe(false);

    // Verify Sentry is still functional
    const sentryFunctional = await page.evaluate(() => {
      return !!(window as any).Sentry && typeof (window as any).Sentry.captureException === 'function';
    });

    expect(sentryFunctional).toBe(true);

    // Check initialization count
    const initCount = await page.evaluate(() => (window as any)._sentryInitCount || 0);
    expect(initCount).toBeLessThanOrEqual(1); // Should only initialize once
  });

  test('should handle multiple browser tabs without instance conflicts', async ({ browser }) => {
    const tabCount = CONFLICT_PREVENTION_CONFIG.testScenarios.multiTab.tabCount;
    const operationsPerTab = CONFLICT_PREVENTION_CONFIG.testScenarios.multiTab.operationsPerTab;

    // Create multiple browser contexts/tabs
    const contexts = await Promise.all(
      Array.from({ length: tabCount }, () => browser.newContext())
    );

    const pages = await Promise.all(contexts.map(context => context.newPage()));

    // Navigate all tabs to the application
    await Promise.all(pages.map(page => 
      page.goto(CONFLICT_PREVENTION_CONFIG.baseURL, { waitUntil: 'networkidle' })
    ));

    // Perform operations in each tab that might trigger conflicts
    const tabOperations = pages.map(async (page, tabIndex) => {
      const operations = [];

      for (let op = 0; op < operationsPerTab; op++) {
        operations.push(
          page.evaluate((tabIdx, opIdx) => {
            // Try to trigger Sentry operations in each tab
            if ((window as any).Sentry) {
              try {
                (window as any).Sentry.captureException(
                  new Error(`Multi-tab test error from tab ${tabIdx}, operation ${opIdx}`)
                );
                
                (window as any).Sentry.addBreadcrumb({
                  message: `Multi-tab breadcrumb from tab ${tabIdx}`,
                  level: 'info',
                });
              } catch (error) {
                console.error(`Tab ${tabIdx} operation ${opIdx} failed:`, error);
                throw error;
              }
            }
          }, tabIndex, op)
        );
      }

      return Promise.all(operations);
    });

    // Execute all tab operations concurrently
    await Promise.all(tabOperations);

    // Check each tab for conflicts
    for (let i = 0; i < pages.length; i++) {
      const detector = new MultipleInstanceDetector();
      const hasConflicts = await detector.detectConflicts(pages[i]);
      
      expect(hasConflicts).toBe(false);
      
      if (hasConflicts) {
        console.error(`Tab ${i} conflicts:`, detector.getAllConflicts());
      }
    }

    // Verify Sentry functionality in all tabs
    const functionalityChecks = await Promise.all(pages.map(page =>
      page.evaluate(() => ({
        hasSentry: !!(window as any).Sentry,
        canCapture: typeof (window as any).Sentry?.captureException === 'function',
        canAddBreadcrumb: typeof (window as any).Sentry?.addBreadcrumb === 'function',
      }))
    ));

    functionalityChecks.forEach((check, index) => {
      expect(check.hasSentry).toBe(true);
      expect(check.canCapture).toBe(true);
      expect(check.canAddBreadcrumb).toBe(true);
    });

    // Clean up
    await Promise.all(contexts.map(context => context.close()));
  });

  test('should maintain environment boundaries during configuration changes', async ({ page }) => {
    const environments = ['staging', 'production', 'development'];

    // Test environment boundary isolation
    const isolationResult = await boundaryTester.testEnvironmentIsolation(page, environments);

    expect(isolationResult.isolated).toBe(true);
    expect(isolationResult.crossContamination).toBe(false);

    // Test rapid environment switching
    for (let i = 0; i < CONFLICT_PREVENTION_CONFIG.testScenarios.environmentSwitching.switchCount; i++) {
      const env = environments[i % environments.length];
      
      // Simulate environment configuration change
      await page.evaluate((environment) => {
        // Mock environment change (in real scenario this would be server-side)
        (window as any)._testEnvironmentChange = environment;
        
        // Verify Sentry doesn't reinitialize with different config
        if ((window as any).Sentry && (window as any).Sentry.isInitialized) {
          const wasInitialized = (window as any).Sentry.isInitialized();
          if (wasInitialized) {
            console.log(`Environment switch to ${environment}: Sentry already initialized, skipping`);
          }
        }
      }, env);

      await page.waitForTimeout(CONFLICT_PREVENTION_CONFIG.testScenarios.environmentSwitching.delay);

      // Check for conflicts after environment switch
      const hasConflicts = await conflictDetector.detectConflicts(page);
      expect(hasConflicts).toBe(false);
    }

    // Verify final state is stable
    await page.waitForTimeout(CONFLICT_PREVENTION_CONFIG.timeouts.stabilization);
    
    const finalConflictCheck = await conflictDetector.detectConflicts(page);
    expect(finalConflictCheck).toBe(false);
  });

  test('should prevent conflicts during page refresh and navigation cycles', async ({ page }) => {
    const refreshCycles = 5;
    const navigationPaths = ['/chat', '/dashboard', '/settings', '/'];

    for (let cycle = 0; cycle < refreshCycles; cycle++) {
      // Navigate to different paths
      for (const path of navigationPaths) {
        await page.goto(`${CONFLICT_PREVENTION_CONFIG.baseURL}${path}`, { 
          waitUntil: 'networkidle' 
        });

        // Check for conflicts after navigation
        const hasConflicts = await conflictDetector.detectConflicts(page);
        expect(hasConflicts).toBe(false);

        // Trigger Sentry operation to verify functionality
        await page.evaluate((cyclePath) => {
          if ((window as any).Sentry) {
            (window as any).Sentry.addBreadcrumb({
              message: `Navigation test: ${cyclePath}`,
              category: 'navigation',
            });
          }
        }, path);

        await page.waitForTimeout(500);
      }

      // Page refresh
      await page.reload({ waitUntil: 'networkidle' });

      // Check for conflicts after refresh
      const hasConflictsAfterRefresh = await conflictDetector.detectConflicts(page);
      expect(hasConflictsAfterRefresh).toBe(false);

      // Verify Sentry still works after refresh
      const sentryWorking = await page.evaluate(() => {
        try {
          if ((window as any).Sentry) {
            (window as any).Sentry.captureException(new Error('Post-refresh test'));
            return true;
          }
          return false;
        } catch (error) {
          return false;
        }
      });

      expect(sentryWorking).toBe(true);
    }
  });

  test('should handle service worker conflicts and cleanup', async ({ page }) => {
    // Check if service workers might interfere with Sentry
    const serviceWorkerState = await page.evaluate(async () => {
      if ('serviceWorker' in navigator) {
        const registration = await navigator.serviceWorker.getRegistration();
        return {
          hasServiceWorker: !!registration,
          serviceWorkerState: registration?.active?.state,
          controlledByServiceWorker: !!navigator.serviceWorker.controller,
        };
      }
      return { hasServiceWorker: false };
    });

    // If service worker is present, test interaction with Sentry
    if (serviceWorkerState.hasServiceWorker) {
      // Simulate service worker message passing that might conflict with Sentry
      await page.evaluate(() => {
        if (navigator.serviceWorker.controller) {
          navigator.serviceWorker.controller.postMessage({
            type: 'TEST_MESSAGE',
            timestamp: Date.now(),
          });
        }
      });

      // Wait for potential conflicts to manifest
      await page.waitForTimeout(2000);

      // Check for conflicts
      const hasConflicts = await conflictDetector.detectConflicts(page);
      expect(hasConflicts).toBe(false);
    }

    // Test Sentry functionality with service worker present
    const sentryWithServiceWorker = await page.evaluate(() => {
      try {
        if ((window as any).Sentry) {
          (window as any).Sentry.captureException(new Error('Service worker interaction test'));
          return true;
        }
        return false;
      } catch (error) {
        console.error('Sentry failed with service worker:', error);
        return false;
      }
    });

    expect(sentryWithServiceWorker).toBe(true);
  });

  test('should reproduce and prevent original multiple instance error scenario', async ({ page }) => {
    // This test specifically reproduces the scenario that caused the original "multiple instance" error
    
    // Step 1: Simulate the original problematic scenario
    await page.evaluate(() => {
      // Mock the original problematic sequence that caused multiple instances
      
      // Simulate React strict mode double mounting
      let initAttempts = 0;
      
      const attemptInitialization = () => {
        initAttempts++;
        console.log(`Init attempt ${initAttempts}`);
        
        if ((window as any).Sentry) {
          // Check if already initialized (this should prevent multiple instances)
          if ((window as any).Sentry.isInitialized && (window as any).Sentry.isInitialized()) {
            console.log('Sentry already initialized, preventing duplicate');
            return false;
          }
          
          // If not initialized, this would be where the original error occurred
          console.log('Sentry not yet initialized, proceeding');
          return true;
        }
        
        return false;
      };

      // Simulate multiple initialization attempts (original error scenario)
      for (let i = 0; i < 5; i++) {
        setTimeout(() => attemptInitialization(), i * 100);
      }
    });

    // Wait for all initialization attempts to complete
    await page.waitForTimeout(1000);

    // Check that no conflicts occurred
    const hasConflicts = await conflictDetector.detectConflicts(page);
    expect(hasConflicts).toBe(false);

    // Verify error messages that would indicate the original problem
    const errorMessages = await page.evaluate(() => {
      return (window as any)._consoleMessages?.filter((msg: string) => 
        msg.includes('multiple instance') || 
        msg.includes('Already initialized') ||
        msg.includes('initialization failed')
      ) || [];
    });

    // Should not have the original error messages
    expect(errorMessages.filter(msg => msg.includes('multiple instance')).length).toBe(0);

    // Should have prevention messages
    const preventionMessages = errorMessages.filter(msg => 
      msg.includes('already initialized') || 
      msg.includes('preventing duplicate')
    );

    expect(preventionMessages.length).toBeGreaterThan(0);

    // Final verification that Sentry is working correctly
    const sentryStatus = await page.evaluate(() => {
      return {
        isAvailable: !!(window as any).Sentry,
        isInitialized: (window as any).Sentry?.isInitialized ? (window as any).Sentry.isInitialized() : false,
        canCapture: typeof (window as any).Sentry?.captureException === 'function',
      };
    });

    expect(sentryStatus.isAvailable).toBe(true);
    expect(sentryStatus.isInitialized).toBe(true);
    expect(sentryStatus.canCapture).toBe(true);

    console.log('Original multiple instance error scenario successfully prevented');
  });
});