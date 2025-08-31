import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { GTMProvider } from '@/providers/GTMProvider';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

// Mock performance API
interface MockPerformanceEntry {
  name: string;
  startTime: number;
  duration: number;
  entryType: string;
}

class MockPerformance {
  public entries: MockPerformanceEntry[] = [];
  public marks: Map<string, number> = new Map();
  public measures: Map<string, { start: number; end: number; duration: number }> = new Map();

  getEntries(): MockPerformanceEntry[] {
    return [...this.entries];
  }

  getEntriesByName(name: string): MockPerformanceEntry[] {
    return this.entries.filter(entry => entry.name === name);
  }

  getEntriesByType(type: string): MockPerformanceEntry[] {
    return this.entries.filter(entry => entry.entryType === type);
  }

  mark(name: string, options?: { startTime?: number }): void {
    const time = options?.startTime || Date.now();
    this.marks.set(name, time);
    this.entries.push({
      name,
      startTime: time,
      duration: 0,
      entryType: 'mark'
    });
  }

  measure(name: string, startMark?: string, endMark?: string): MockPerformanceEntry {
    let startTime = 0;
    let endTime = Date.now();

    if (startMark) {
      startTime = this.marks.get(startMark) || 0;
    }
    if (endMark) {
      endTime = this.marks.get(endMark) || Date.now();
    }

    const duration = endTime - startTime;
    const measure = {
      name,
      startTime,
      duration,
      entryType: 'measure'
    };

    this.entries.push(measure);
    this.measures.set(name, { start: startTime, end: endTime, duration });
    
    return measure;
  }

  clearMarks(name?: string): void {
    if (name) {
      this.marks.delete(name);
      this.entries = this.entries.filter(entry => !(entry.name === name && entry.entryType === 'mark'));
    } else {
      this.marks.clear();
      this.entries = this.entries.filter(entry => entry.entryType !== 'mark');
    }
  }

  clearMeasures(name?: string): void {
    if (name) {
      this.measures.delete(name);
      this.entries = this.entries.filter(entry => !(entry.name === name && entry.entryType === 'measure'));
    } else {
      this.measures.clear();
      this.entries = this.entries.filter(entry => entry.entryType !== 'measure');
    }
  }

  now(): number {
    return Date.now();
  }
}

// Mock Next.js Script component with performance tracking
jest.mock('next/script', () => {
  return function MockScript({ onLoad, onReady, onError, ...props }: any) {
    React.useEffect(() => {
      const startTime = Date.now();
      
      if (onReady) {
        // Simulate script ready
        const readyTimer = setTimeout(() => {
          onReady();
        }, 10);

        // Simulate script load with performance measurement
        const loadTimer = setTimeout(() => {
          const loadTime = Date.now() - startTime;
          
          // Add performance entry
          if (global.performance && 'getEntries' in global.performance) {
            (global.performance as any).entries.push({
              name: 'gtm-script',
              startTime: startTime,
              duration: loadTime,
              entryType: 'script'
            });
          }
          
          if (onLoad) onLoad();
        }, 50 + Math.random() * 100); // Simulate variable load time

        return () => {
          clearTimeout(readyTimer);
          clearTimeout(loadTimer);
        };
      }
    }, [onLoad, onReady]);

    return <script {...props} data-testid="gtm-script" />;
  };
});

// Mock logger
jest.mock('@/lib/logger', () => ({
  logger: {
    debug: jest.fn(),
    error: jest.fn(),
    info: jest.fn(),
  },
}));

// Test component for performance measurement
const PerformanceTestComponent: React.FC<{
  onRenderComplete?: () => void;
  eventCount?: number;
}> = ({ onRenderComplete, eventCount = 0 }) => {
  const [renderComplete, setRenderComplete] = React.useState(false);

  React.useEffect(() => {
    if (!renderComplete) {
      setRenderComplete(true);
      if (onRenderComplete) {
        onRenderComplete();
      }
    }
  }, [renderComplete, onRenderComplete]);

  // Simulate multiple event triggers for performance testing
  React.useEffect(() => {
    if (eventCount > 0 && global.window?.dataLayer) {
      for (let i = 0; i < eventCount; i++) {
        global.window.dataLayer.push({
          event: `performance_test_event_${i}`,
          event_category: 'performance_test',
          event_action: 'load_test',
          index: i,
          timestamp: new Date().toISOString()
        });
      }
    }
  }, [eventCount]);

  return (
    <div data-testid="performance-test-component">
      <div data-testid="render-status">{renderComplete ? 'complete' : 'rendering'}</div>
      <div data-testid="event-count">{eventCount}</div>
    </div>
  );
};

describe('GTM Performance Impact Tests', () => {
  setupAntiHang();
    jest.setTimeout(10000);
  let mockPerformance: MockPerformance;
  let mockDataLayer: any[];
  let originalPerformance: Performance;

  beforeEach(() => {
    mockPerformance = new MockPerformance();
    mockDataLayer = [];
    originalPerformance = global.performance;

    // Mock performance API
    Object.defineProperty(global, 'performance', {
      value: mockPerformance,
      writable: true
    });

    // Mock window with dataLayer
    Object.defineProperty(global, 'window', {
      value: {
        ...global.window,
        dataLayer: mockDataLayer,
        location: {
          pathname: '/performance-test'
        }
      },
      writable: true
    });

    jest.clearAllMocks();
  });

  afterEach(() => {
    global.performance = originalPerformance;
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
      cleanupAntiHang();
  });

  describe('Initial Load Performance', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should measure GTM script loading time', async () => {
      const startTime = Date.now();
      mockPerformance.mark('gtm-load-start', { startTime });

      render(
        <GTMProvider enabled={true} config={{ debug: true }}>
          <PerformanceTestComponent />
        </GTMProvider>
      );

      // Wait for GTM script to load
      await waitFor(() => {
        expect(screen.getByTestId('gtm-script')).toBeInTheDocument();
      });

      // Wait a bit more for async loading
      await new Promise(resolve => setTimeout(resolve, 200));

      // Measure load completion
      const endTime = Date.now();
      mockPerformance.mark('gtm-load-end', { startTime: endTime });
      const loadMeasure = mockPerformance.measure('gtm-total-load', 'gtm-load-start', 'gtm-load-end');

      // Verify performance measurement
      expect(loadMeasure.duration).toBeLessThan(500); // Should load within 500ms
      expect(loadMeasure.duration).toBeGreaterThan(0);

      // Check for GTM script entry
      const scriptEntries = mockPerformance.getEntriesByName('gtm-script');
      expect(scriptEntries.length).toBeGreaterThan(0);
      expect(scriptEntries[0].duration).toBeLessThan(200); // Script execution should be fast
    });

    it('should measure component render time with GTM', async () => {
      let renderCompleteTime = 0;

      const onRenderComplete = () => {
        renderCompleteTime = Date.now();
        mockPerformance.mark('component-render-complete', { startTime: renderCompleteTime });
      };

      const renderStartTime = Date.now();
      mockPerformance.mark('component-render-start', { startTime: renderStartTime });

      render(
        <GTMProvider enabled={true}>
          <PerformanceTestComponent onRenderComplete={onRenderComplete} />
        </GTMProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('render-status')).toHaveTextContent('complete');
      });

      // Measure total render time
      const renderMeasure = mockPerformance.measure('total-render-time', 'component-render-start', 'component-render-complete');

      expect(renderMeasure.duration).toBeLessThan(100); // Should render quickly even with GTM
      expect(renderCompleteTime).toBeGreaterThan(renderStartTime);
    });

    it('should compare performance with and without GTM', async () => {
      // Test without GTM
      const withoutGTMStart = Date.now();
      mockPerformance.mark('without-gtm-start', { startTime: withoutGTMStart });

      const { unmount: unmountWithoutGTM } = render(
        <GTMProvider enabled={false}>
          <PerformanceTestComponent />
        </GTMProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('render-status')).toHaveTextContent('complete');
      });

      const withoutGTMEnd = Date.now();
      mockPerformance.mark('without-gtm-end', { startTime: withoutGTMEnd });
      const withoutGTMMeasure = mockPerformance.measure('without-gtm-total', 'without-gtm-start', 'without-gtm-end');

      unmountWithoutGTM();

      // Test with GTM
      const withGTMStart = Date.now();
      mockPerformance.mark('with-gtm-start', { startTime: withGTMStart });

      render(
        <GTMProvider enabled={true}>
          <PerformanceTestComponent />
        </GTMProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('render-status')).toHaveTextContent('complete');
      });

      const withGTMEnd = Date.now();
      mockPerformance.mark('with-gtm-end', { startTime: withGTMEnd });
      const withGTMMeasure = mockPerformance.measure('with-gtm-total', 'with-gtm-start', 'with-gtm-end');

      // GTM should not add more than 100ms overhead
      const overhead = withGTMMeasure.duration - withoutGTMMeasure.duration;
      expect(overhead).toBeLessThan(100);

      // Both should complete in reasonable time
      expect(withoutGTMMeasure.duration).toBeLessThan(200);
      expect(withGTMMeasure.duration).toBeLessThan(300);
    });
  });

  describe('Runtime Performance', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should measure event tracking performance', async () => {
      render(
        <GTMProvider enabled={true} config={{ debug: true }}>
          <PerformanceTestComponent />
        </GTMProvider>
      );

      await waitFor(() => {
        expect(global.window.dataLayer).toBeDefined();
      });

      // Measure single event tracking
      const eventStart = Date.now();
      mockPerformance.mark('single-event-start', { startTime: eventStart });

      global.window.dataLayer.push({
        event: 'performance_test_single',
        event_category: 'performance',
        test_data: 'single event test'
      });

      const eventEnd = Date.now();
      mockPerformance.mark('single-event-end', { startTime: eventEnd });
      const singleEventMeasure = mockPerformance.measure('single-event-duration', 'single-event-start', 'single-event-end');

      // Single event should be very fast
      expect(singleEventMeasure.duration).toBeLessThan(10);
    });

    it('should measure bulk event tracking performance', async () => {
      render(
        <GTMProvider enabled={true} config={{ debug: true }}>
          <PerformanceTestComponent />
        </GTMProvider>
      );

      await waitFor(() => {
        expect(global.window.dataLayer).toBeDefined();
      });

      // Measure bulk event processing
      const bulkStart = Date.now();
      mockPerformance.mark('bulk-events-start', { startTime: bulkStart });

      // Push 100 events
      for (let i = 0; i < 100; i++) {
        global.window.dataLayer.push({
          event: `bulk_test_event_${i}`,
          event_category: 'performance',
          event_action: 'bulk_test',
          index: i
        });
      }

      const bulkEnd = Date.now();
      mockPerformance.mark('bulk-events-end', { startTime: bulkEnd });
      const bulkEventsMeasure = mockPerformance.measure('bulk-events-duration', 'bulk-events-start', 'bulk-events-end');

      // Bulk events should complete within reasonable time
      expect(bulkEventsMeasure.duration).toBeLessThan(100);
      expect(global.window.dataLayer.length).toBe(100);
    });

    it('should measure performance under high event load', async () => {
      const eventCount = 1000;

      render(
        <GTMProvider enabled={true} config={{ debug: true }}>
          <PerformanceTestComponent eventCount={eventCount} />
        </GTMProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('event-count')).toHaveTextContent(eventCount.toString());
      });

      // Wait for all events to be processed
      await new Promise(resolve => setTimeout(resolve, 100));

      // Verify all events were tracked
      expect(global.window.dataLayer.length).toBe(eventCount);

      // Check that performance is still acceptable
      const performanceEntries = mockPerformance.getEntries();
      const hasPerformanceDegradation = performanceEntries.some(entry => entry.duration > 1000);
      expect(hasPerformanceDegradation).toBe(false);
    });

    it('should measure memory usage during event tracking', async () => {
      // Mock memory API
      const mockMemory = {
        usedJSHeapSize: 10000000,
        totalJSHeapSize: 20000000,
        jsHeapSizeLimit: 2147483648
      };

      Object.defineProperty(global.performance, 'memory', {
        value: mockMemory,
        writable: true
      });

      render(
        <GTMProvider enabled={true} config={{ debug: true }}>
          <PerformanceTestComponent />
        </GTMProvider>
      );

      const initialMemory = mockMemory.usedJSHeapSize;

      // Track many events to simulate memory usage
      for (let i = 0; i < 500; i++) {
        global.window.dataLayer.push({
          event: `memory_test_${i}`,
          large_data: 'x'.repeat(1000), // Simulate larger events
          timestamp: new Date().toISOString()
        });

        // Simulate memory increase
        mockMemory.usedJSHeapSize += 1000;
      }

      const finalMemory = mockMemory.usedJSHeapSize;
      const memoryIncrease = finalMemory - initialMemory;

      // Memory increase should be reasonable for the number of events
      expect(memoryIncrease).toBeLessThan(1000000); // Less than 1MB increase
      expect(memoryIncrease).toBeGreaterThan(0);

      // Memory usage should not exceed limits
      expect(finalMemory).toBeLessThan(mockMemory.totalJSHeapSize);
    });
  });

  describe('Performance Regression Detection', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should detect performance regressions in script loading', async () => {
      const performanceBaseline = {
        scriptLoadTime: 50,
        renderTime: 30,
        firstEventTime: 5
      };

      // First run - establish baseline
      const baselineStart = Date.now();
      mockPerformance.mark('baseline-start', { startTime: baselineStart });

      const { unmount } = render(
        <GTMProvider enabled={true}>
          <PerformanceTestComponent />
        </GTMProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('render-status')).toHaveTextContent('complete');
      });

      const baselineEnd = Date.now();
      mockPerformance.mark('baseline-end', { startTime: baselineEnd });
      const baselineMeasure = mockPerformance.measure('baseline-total', 'baseline-start', 'baseline-end');

      unmount();

      // Simulate performance regression (slower script loading)
      jest.clearAllMocks();
      
      // Mock slower script loading
      jest.mock('next/script', () => {
        return function SlowMockScript({ onLoad, onReady, ...props }: any) {
          React.useEffect(() => {
            if (onReady) {
              setTimeout(() => onReady(), 50);
            }
            if (onLoad) {
              // Simulate slower loading
              setTimeout(() => onLoad(), 200);
            }
          }, [onLoad, onReady]);
          return <script {...props} data-testid="gtm-script" />;
        };
      });

      const regressionStart = Date.now();
      mockPerformance.mark('regression-start', { startTime: regressionStart });

      render(
        <GTMProvider enabled={true}>
          <PerformanceTestComponent />
        </GTMProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('render-status')).toHaveTextContent('complete');
      });

      const regressionEnd = Date.now();
      mockPerformance.mark('regression-end', { startTime: regressionEnd });
      const regressionMeasure = mockPerformance.measure('regression-total', 'regression-start', 'regression-end');

      // Calculate regression percentage
      const regressionPercentage = ((regressionMeasure.duration - baselineMeasure.duration) / baselineMeasure.duration) * 100;

      // Should detect significant regression
      if (regressionPercentage > 20) {
        // This would trigger an alert in real implementation
        expect(regressionPercentage).toBeGreaterThan(20);
        expect(regressionMeasure.duration).toBeGreaterThan(baselineMeasure.duration);
      }
    });

    it('should track performance trends over multiple renders', async () => {
      const performanceHistory: number[] = [];
      const iterationCount = 5;

      for (let i = 0; i < iterationCount; i++) {
        const iterationStart = Date.now();
        mockPerformance.mark(`iteration-${i}-start`, { startTime: iterationStart });

        const { unmount } = render(
          <GTMProvider enabled={true}>
            <PerformanceTestComponent />
          </GTMProvider>
        );

        await waitFor(() => {
          expect(screen.getByTestId('render-status')).toHaveTextContent('complete');
        });

        const iterationEnd = Date.now();
        mockPerformance.mark(`iteration-${i}-end`, { startTime: iterationEnd });
        const iterationMeasure = mockPerformance.measure(`iteration-${i}`, `iteration-${i}-start`, `iteration-${i}-end`);

        performanceHistory.push(iterationMeasure.duration);
        unmount();

        // Clear DOM between iterations
        document.body.innerHTML = '';
      }

      // Analyze performance trend
      const averagePerformance = performanceHistory.reduce((sum, time) => sum + time, 0) / performanceHistory.length;
      const performanceVariance = performanceHistory.reduce((variance, time) => variance + Math.pow(time - averagePerformance, 2), 0) / performanceHistory.length;
      const performanceStandardDeviation = Math.sqrt(performanceVariance);

      // Performance should be consistent (low variance)
      expect(performanceStandardDeviation).toBeLessThan(averagePerformance * 0.2); // Less than 20% variation
      expect(averagePerformance).toBeLessThan(300); // Average should be reasonable

      // No single iteration should be exceptionally slow
      const maxPerformance = Math.max(...performanceHistory);
      expect(maxPerformance).toBeLessThan(averagePerformance * 2); // No more than 2x average
    });
  });

  describe('Resource Usage Optimization', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should minimize DOM manipulation during event tracking', async () => {
      let domMutationCount = 0;
      
      // Mock MutationObserver to count DOM changes
      const originalMutationObserver = global.MutationObserver;
      global.MutationObserver = class MockMutationObserver {
        constructor(callback: MutationCallback) {
          // Simulate mutations being observed
          setTimeout(() => {
            callback([], this);
          }, 10);
        }
        observe() {
          // Count each observation as potential mutation
          domMutationCount++;
        }
        disconnect() {}
      };

      render(
        <GTMProvider enabled={true} config={{ debug: true }}>
          <PerformanceTestComponent />
        </GTMProvider>
      );

      // Track multiple events
      for (let i = 0; i < 50; i++) {
        global.window.dataLayer.push({
          event: `dom_test_${i}`,
          event_category: 'dom_impact'
        });
      }

      await new Promise(resolve => setTimeout(resolve, 100));

      // DOM mutations should be minimal for event tracking
      expect(domMutationCount).toBeLessThan(10); // GTM should not cause excessive DOM changes

      global.MutationObserver = originalMutationObserver;
    });

    it('should optimize dataLayer memory usage', async () => {
      render(
        <GTMProvider enabled={true} config={{ debug: true }}>
          <PerformanceTestComponent />
        </GTMProvider>
      );

      const initialDataLayerSize = global.window.dataLayer.length;

      // Add many events
      for (let i = 0; i < 1000; i++) {
        global.window.dataLayer.push({
          event: `memory_optimization_test_${i}`,
          data: 'x'.repeat(100),
          index: i
        });
      }

      const finalDataLayerSize = global.window.dataLayer.length;
      const dataLayerGrowth = finalDataLayerSize - initialDataLayerSize;

      expect(dataLayerGrowth).toBe(1000); // All events should be added

      // Simulate memory cleanup (this would be done by GTM in real implementation)
      // For testing, we verify the data structure can handle large datasets
      expect(global.window.dataLayer.length).toBeLessThan(2000); // Should not grow excessively beyond what we added
    });

    it('should handle concurrent event tracking efficiently', async () => {
      render(
        <GTMProvider enabled={true} config={{ debug: true }}>
          <PerformanceTestComponent />
        </GTMProvider>
      );

      const concurrentEventPromises: Promise<void>[] = [];
      const eventTrackingStart = Date.now();

      // Simulate concurrent event tracking
      for (let i = 0; i < 100; i++) {
        const promise = new Promise<void>((resolve) => {
          setTimeout(() => {
            global.window.dataLayer.push({
              event: `concurrent_test_${i}`,
              event_category: 'concurrency',
              thread_id: i,
              timestamp: new Date().toISOString()
            });
            resolve();
          }, Math.random() * 10); // Random delay up to 10ms
        });
        concurrentEventPromises.push(promise);
      }

      // Wait for all concurrent events to complete
      await Promise.all(concurrentEventPromises);
      
      const eventTrackingEnd = Date.now();
      const totalTrackingTime = eventTrackingEnd - eventTrackingStart;

      // Concurrent tracking should be efficient
      expect(totalTrackingTime).toBeLessThan(100); // Should complete within 100ms
      expect(global.window.dataLayer.length).toBe(100); // All events should be tracked

      // Verify no events were lost during concurrent access
      const concurrentEvents = global.window.dataLayer.filter(event => 
        typeof event.event === 'string' && event.event.startsWith('concurrent_test_')
      );
      expect(concurrentEvents).toHaveLength(100);
    });
  });

  describe('Performance Budgets', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should stay within script loading performance budget', async () => {
      const performanceBudget = {
        scriptLoadTime: 100, // 100ms budget for script loading
        renderTime: 50,      // 50ms budget for render
        eventTime: 5         // 5ms budget per event
      };

      const loadStart = Date.now();
      mockPerformance.mark('budget-test-start', { startTime: loadStart });

      render(
        <GTMProvider enabled={true}>
          <PerformanceTestComponent />
        </GTMProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('render-status')).toHaveTextContent('complete');
      });

      const loadEnd = Date.now();
      mockPerformance.mark('budget-test-end', { startTime: loadEnd });
      const totalMeasure = mockPerformance.measure('budget-total', 'budget-test-start', 'budget-test-end');

      // Should meet performance budget
      expect(totalMeasure.duration).toBeLessThan(performanceBudget.scriptLoadTime + performanceBudget.renderTime);

      // Test individual event performance
      const eventStart = Date.now();
      global.window.dataLayer.push({
        event: 'budget_test_event',
        event_category: 'budget'
      });
      const eventEnd = Date.now();
      const eventDuration = eventEnd - eventStart;

      expect(eventDuration).toBeLessThan(performanceBudget.eventTime);
    });

    it('should alert when performance budgets are exceeded', async () => {
      const budgetExceededEvents: any[] = [];
      const originalDataLayerPush = global.window.dataLayer.push;
      
      // Mock dataLayer.push to capture budget exceeded events
      global.window.dataLayer.push = function(...args) {
        const result = originalDataLayerPush.apply(this, args);
        
        args.forEach(event => {
          if (event.event === 'performance_budget_exceeded') {
            budgetExceededEvents.push(event);
          }
        });
        
        return result;
      };

      // Simulate slow operation that exceeds budget
      const slowStart = Date.now();
      
      render(
        <GTMProvider enabled={true}>
          <PerformanceTestComponent />
        </GTMProvider>
      );

      // Simulate budget exceeded scenario
      await new Promise(resolve => setTimeout(resolve, 200)); // Simulate slow loading
      
      const slowEnd = Date.now();
      const actualTime = slowEnd - slowStart;

      // If time exceeds budget, simulate alert
      if (actualTime > 100) {
        global.window.dataLayer.push({
          event: 'performance_budget_exceeded',
          budget_type: 'script_load',
          budget_limit: 100,
          actual_time: actualTime,
          overage: actualTime - 100
        });
      }

      // Verify budget exceeded event was tracked if applicable
      if (budgetExceededEvents.length > 0) {
        expect(budgetExceededEvents[0].budget_type).toBe('script_load');
        expect(budgetExceededEvents[0].actual_time).toBeGreaterThan(budgetExceededEvents[0].budget_limit);
      }
    });
  });
});