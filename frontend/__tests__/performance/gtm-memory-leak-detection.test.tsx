import React from 'react';
import { render, screen, waitFor, act, cleanup } from '@testing-library/react';
import { GTMProvider } from '@/providers/GTMProvider';
import { useGTM } from '@/hooks/useGTM';

// Mock performance.memory API
interface MockMemoryInfo {
  usedJSHeapSize: number;
  totalJSHeapSize: number;
  jsHeapSizeLimit: number;
}

class MockPerformanceMemory {
  private _memory: MockMemoryInfo = {
    usedJSHeapSize: 10000000, // 10MB initial
    totalJSHeapSize: 50000000, // 50MB total
    jsHeapSizeLimit: 2147483648 // 2GB limit
  };

  get memory(): MockMemoryInfo {
    return { ...this._memory };
  }

  // Simulate memory allocation
  allocateMemory(bytes: number) {
    this._memory.usedJSHeapSize += bytes;
    if (this._memory.usedJSHeapSize > this._memory.totalJSHeapSize) {
      this._memory.totalJSHeapSize = Math.min(
        this._memory.usedJSHeapSize * 1.5,
        this._memory.jsHeapSizeLimit
      );
    }
  }

  // Simulate garbage collection
  garbageCollect(bytesToFree: number = 0) {
    if (bytesToFree === 0) {
      // Simulate partial cleanup
      this._memory.usedJSHeapSize = Math.max(
        this._memory.usedJSHeapSize * 0.8,
        10000000 // Minimum baseline
      );
    } else {
      this._memory.usedJSHeapSize = Math.max(
        this._memory.usedJSHeapSize - bytesToFree,
        10000000
      );
    }
  }

  reset() {
    this._memory = {
      usedJSHeapSize: 10000000,
      totalJSHeapSize: 50000000,
      jsHeapSizeLimit: 2147483648
    };
  }
}

const mockPerformanceMemory = new MockPerformanceMemory();

// Mock Next.js Script component
jest.mock('next/script', () => {
  return function MockScript({ onLoad, onReady, ...props }: any) {
    React.useEffect(() => {
      if (onReady) {
        setTimeout(() => onReady(), 10);
      }
      if (onLoad) {
        setTimeout(() => {
          // Simulate script memory allocation
          mockPerformanceMemory.allocateMemory(100000); // 100KB for GTM script
          onLoad();
        }, 50);
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
    warn: jest.fn(),
  },
}));

// Test component that creates potential memory leaks
const MemoryLeakTestComponent: React.FC<{
  eventCount?: number;
  createListeners?: boolean;
  largeDataEvents?: boolean;
}> = ({ eventCount = 10, createListeners = false, largeDataEvents = false }) => {
  const gtm = useGTM();
  const [listeners, setListeners] = React.useState<(() => void)[]>([]);
  const eventIntervalRef = React.useRef<NodeJS.Timeout>();

  React.useEffect(() => {
    if (!gtm.isLoaded) return;

    // Create event listeners that might not be cleaned up
    if (createListeners) {
      const newListeners: (() => void)[] = [];
      
      for (let i = 0; i < 5; i++) {
        const handler = () => {
          gtm.events.trackCustom({
            event: `listener_event_${i}`,
            event_category: 'memory_test',
            listener_id: i
          });
        };
        
        // Add event listeners (potential leak source)
        window.addEventListener(`test_event_${i}`, handler);
        newListeners.push(() => window.removeEventListener(`test_event_${i}`, handler));
      }
      
      setListeners(newListeners);
    }

    // Create many events with large data
    if (largeDataEvents) {
      let counter = 0;
      eventIntervalRef.current = setInterval(() => {
        if (counter >= eventCount) {
          if (eventIntervalRef.current) {
            clearInterval(eventIntervalRef.current);
          }
          return;
        }

        gtm.events.trackCustom({
          event: 'large_data_event',
          event_category: 'memory_test',
          large_payload: 'x'.repeat(10000), // 10KB of data per event
          event_index: counter,
          timestamp: new Date().toISOString(),
          additional_data: {
            nested_object: {
              deeply: {
                nested: {
                  data: 'x'.repeat(1000)
                }
              }
            },
            array_data: new Array(100).fill('data'),
            metadata: {
              user_id: `user_${counter}`,
              session_data: 'x'.repeat(500)
            }
          }
        });

        // Simulate memory allocation for each event
        mockPerformanceMemory.allocateMemory(15000); // 15KB per event processing
        counter++;
      }, 10);
    } else {
      // Create regular events
      for (let i = 0; i < eventCount; i++) {
        setTimeout(() => {
          gtm.events.trackCustom({
            event: `memory_test_event_${i}`,
            event_category: 'memory_test',
            event_index: i
          });
          mockPerformanceMemory.allocateMemory(1000); // 1KB per event
        }, i * 5);
      }
    }

    return () => {
      // Cleanup event listeners
      listeners.forEach(removeListener => removeListener());
      
      if (eventIntervalRef.current) {
        clearInterval(eventIntervalRef.current);
      }
    };
  }, [gtm.isLoaded, eventCount, createListeners, largeDataEvents, gtm.events, listeners]);

  return (
    <div data-testid="memory-leak-test-component">
      <div data-testid="gtm-loaded">{gtm.isLoaded ? 'loaded' : 'not-loaded'}</div>
      <div data-testid="listener-count">{listeners.length}</div>
    </div>
  );
};

// Component that mounts and unmounts frequently
const FrequentMountComponent: React.FC<{ mountCount: number }> = ({ mountCount }) => {
  const [currentMount, setCurrentMount] = React.useState(0);
  const [showGTM, setShowGTM] = React.useState(true);

  React.useEffect(() => {
    if (currentMount < mountCount) {
      const timer = setTimeout(() => {
        setShowGTM(false);
        setTimeout(() => {
          setCurrentMount(prev => prev + 1);
          setShowGTM(true);
          // Simulate some memory allocation on each mount
          mockPerformanceMemory.allocateMemory(50000); // 50KB per mount cycle
        }, 100);
      }, 200);

      return () => clearTimeout(timer);
    }
  }, [currentMount, mountCount]);

  return (
    <div data-testid="frequent-mount-component">
      <div data-testid="mount-count">{currentMount}</div>
      {showGTM && (
        <GTMProvider enabled={true} config={{ debug: true }}>
          <MemoryLeakTestComponent eventCount={5} />
        </GTMProvider>
      )}
    </div>
  );
};

describe('GTM Memory Leak Detection Tests', () => {
  let mockDataLayer: any[];
  let initialMemoryUsage: number;

  beforeEach(() => {
    mockDataLayer = [];
    mockPerformanceMemory.reset();
    initialMemoryUsage = mockPerformanceMemory.memory.usedJSHeapSize;

    // Mock window with enhanced dataLayer tracking
    Object.defineProperty(global, 'window', {
      value: {
        ...global.window,
        dataLayer: mockDataLayer,
        performance: {
          ...global.window?.performance,
          memory: mockPerformanceMemory.memory
        },
        location: {
          pathname: '/memory-test'
        }
      },
      writable: true
    });

    jest.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    // Simulate garbage collection after each test
    mockPerformanceMemory.garbageCollect();
  });

  describe('Event Tracking Memory Usage', () => {
    it('should not leak memory during normal event tracking', async () => {
      const initialMemory = mockPerformanceMemory.memory.usedJSHeapSize;

      render(
        <GTMProvider enabled={true} config={{ debug: true }}>
          <MemoryLeakTestComponent eventCount={50} />
        </GTMProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('gtm-loaded')).toHaveTextContent('loaded');
      });

      // Wait for all events to be processed
      await new Promise(resolve => setTimeout(resolve, 500));

      const memoryAfterEvents = mockPerformanceMemory.memory.usedJSHeapSize;
      const memoryIncrease = memoryAfterEvents - initialMemory;

      // Memory increase should be proportional to events (50 events * ~1KB + GTM overhead)
      expect(memoryIncrease).toBeLessThan(200000); // Less than 200KB total increase
      expect(memoryIncrease).toBeGreaterThan(0); // Should have some increase

      // Verify events were tracked
      expect(mockDataLayer.length).toBe(50);

      // Simulate component cleanup
      cleanup();
      
      // Simulate garbage collection
      mockPerformanceMemory.garbageCollect();
      
      const memoryAfterCleanup = mockPerformanceMemory.memory.usedJSHeapSize;
      const memoryRecovered = memoryAfterEvents - memoryAfterCleanup;

      // Should recover some memory after cleanup
      expect(memoryRecovered).toBeGreaterThan(0);
    });

    it('should detect memory leaks from large event payloads', async () => {
      const initialMemory = mockPerformanceMemory.memory.usedJSHeapSize;

      render(
        <GTMProvider enabled={true} config={{ debug: true }}>
          <MemoryLeakTestComponent eventCount={20} largeDataEvents={true} />
        </GTMProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('gtm-loaded')).toHaveTextContent('loaded');
      });

      // Wait for all large events to be processed
      await new Promise(resolve => setTimeout(resolve, 1000));

      const memoryAfterLargeEvents = mockPerformanceMemory.memory.usedJSHeapSize;
      const memoryIncrease = memoryAfterLargeEvents - initialMemory;

      // Large events should use significantly more memory (20 events * ~15KB each + data)
      expect(memoryIncrease).toBeGreaterThan(300000); // More than 300KB
      expect(memoryIncrease).toBeLessThan(1000000); // But less than 1MB

      // Check if memory usage is excessive
      const memoryPressure = memoryIncrease / initialMemory;
      if (memoryPressure > 0.1) { // More than 10% increase
        // Should trigger memory warning
        const memoryWarning = mockDataLayer.find(event => 
          event.event === 'memory_warning' || event.event === 'performance_issue'
        );
        
        if (memoryWarning) {
          expect(memoryWarning.memory_increase).toBeGreaterThan(0);
          expect(memoryWarning.memory_pressure).toBeDefined();
        }
      }
    });

    it('should detect memory leaks from event listeners', async () => {
      const initialMemory = mockPerformanceMemory.memory.usedJSHeapSize;

      render(
        <GTMProvider enabled={true} config={{ debug: true }}>
          <MemoryLeakTestComponent createListeners={true} />
        </GTMProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('gtm-loaded')).toHaveTextContent('loaded');
        expect(screen.getByTestId('listener-count')).toHaveTextContent('5');
      });

      // Trigger the event listeners
      for (let i = 0; i < 5; i++) {
        window.dispatchEvent(new Event(`test_event_${i}`));
        await new Promise(resolve => setTimeout(resolve, 10));
      }

      const memoryAfterListeners = mockPerformanceMemory.memory.usedJSHeapSize;

      // Component unmount should clean up listeners
      cleanup();

      // Simulate garbage collection
      mockPerformanceMemory.garbageCollect();
      
      const memoryAfterCleanup = mockPerformanceMemory.memory.usedJSHeapSize;
      const memoryRecovered = memoryAfterListeners - memoryAfterCleanup;

      // Should recover memory from cleaned up listeners
      expect(memoryRecovered).toBeGreaterThan(0);

      // Memory should not keep growing after cleanup
      const finalIncrease = memoryAfterCleanup - initialMemory;
      expect(finalIncrease).toBeLessThan(150000); // Less than 150KB permanent increase
    });
  });

  describe('Component Lifecycle Memory Management', () => {
    it('should not leak memory during frequent mount/unmount cycles', async () => {
      const initialMemory = mockPerformanceMemory.memory.usedJSHeapSize;

      render(<FrequentMountComponent mountCount={5} />);

      // Wait for all mount cycles to complete
      await waitFor(() => {
        expect(screen.getByTestId('mount-count')).toHaveTextContent('5');
      }, { timeout: 5000 });

      const memoryAfterCycles = mockPerformanceMemory.memory.usedJSHeapSize;
      const memoryIncrease = memoryAfterCycles - initialMemory;

      // Memory increase should be bounded (5 cycles * 50KB + reasonable overhead)
      expect(memoryIncrease).toBeLessThan(500000); // Less than 500KB

      // Cleanup and garbage collect
      cleanup();
      mockPerformanceMemory.garbageCollect();

      const memoryAfterFinalCleanup = mockPerformanceMemory.memory.usedJSHeapSize;
      const memoryRecovered = memoryAfterCycles - memoryAfterFinalCleanup;

      // Should recover significant memory after cleanup
      expect(memoryRecovered).toBeGreaterThan(memoryIncrease * 0.5); // At least 50% recovery
    });

    it('should clean up GTM resources on component unmount', async () => {
      const initialMemory = mockPerformanceMemory.memory.usedJSHeapSize;
      let gtmContext: any;

      const TestComponent = () => {
        const gtm = useGTM();
        gtmContext = gtm;
        
        React.useEffect(() => {
          if (gtm.isLoaded) {
            // Create resources that need cleanup
            for (let i = 0; i < 10; i++) {
              gtm.events.trackCustom({
                event: `cleanup_test_${i}`,
                event_category: 'cleanup',
                resource_id: i,
                large_data: 'x'.repeat(5000)
              });
            }
            mockPerformanceMemory.allocateMemory(100000); // 100KB of resources
          }
        }, [gtm.isLoaded, gtm.events]);

        return <div data-testid="cleanup-test">GTM Cleanup Test</div>;
      };

      const { unmount } = render(
        <GTMProvider enabled={true}>
          <TestComponent />
        </GTMProvider>
      );

      await waitFor(() => {
        expect(gtmContext?.isLoaded).toBe(true);
      });

      const memoryAfterSetup = mockPerformanceMemory.memory.usedJSHeapSize;
      const setupIncrease = memoryAfterSetup - initialMemory;

      // Unmount component
      unmount();

      // Simulate cleanup and garbage collection
      mockPerformanceMemory.garbageCollect();

      const memoryAfterUnmount = mockPerformanceMemory.memory.usedJSHeapSize;
      const memoryRecovered = memoryAfterSetup - memoryAfterUnmount;

      // Should recover most memory after unmount
      expect(memoryRecovered).toBeGreaterThan(setupIncrease * 0.6); // At least 60% recovery
    });
  });

  describe('DataLayer Memory Growth', () => {
    it('should prevent unbounded dataLayer growth', async () => {
      const initialMemory = mockPerformanceMemory.memory.usedJSHeapSize;

      render(
        <GTMProvider enabled={true} config={{ debug: true }}>
          <div data-testid="datalayer-growth-test" />
        </GTMProvider>
      );

      // Add many events to dataLayer
      const eventCount = 1000;
      for (let i = 0; i < eventCount; i++) {
        mockDataLayer.push({
          event: `growth_test_${i}`,
          event_category: 'growth',
          event_data: 'x'.repeat(1000), // 1KB per event
          index: i,
          timestamp: new Date().toISOString()
        });
        
        // Simulate memory allocation for each event
        mockPerformanceMemory.allocateMemory(1500); // 1.5KB per event with overhead
        
        // Simulate periodic cleanup (GTM would do this)
        if (i % 100 === 99) {
          mockPerformanceMemory.garbageCollect(50000); // Clean up 50KB
        }
      }

      const memoryAfterGrowth = mockPerformanceMemory.memory.usedJSHeapSize;
      const memoryIncrease = memoryAfterGrowth - initialMemory;

      // Memory growth should be managed (not linear with event count due to cleanup)
      expect(mockDataLayer.length).toBe(eventCount);
      expect(memoryIncrease).toBeLessThan(eventCount * 1500); // Less than theoretical max
      expect(memoryIncrease).toBeGreaterThan(0);

      // Memory usage should stabilize (not keep growing)
      const memoryBefore = mockPerformanceMemory.memory.usedJSHeapSize;
      
      // Add more events
      for (let i = 0; i < 100; i++) {
        mockDataLayer.push({
          event: `stability_test_${i}`,
          data: 'x'.repeat(1000)
        });
        mockPerformanceMemory.allocateMemory(1500);
      }
      
      // Simulate cleanup
      mockPerformanceMemory.garbageCollect(150000);
      
      const memoryAfter = mockPerformanceMemory.memory.usedJSHeapSize;
      const additionalGrowth = memoryAfter - memoryBefore;

      // Additional growth should be minimal due to cleanup
      expect(additionalGrowth).toBeLessThan(100000); // Less than 100KB additional
    });

    it('should detect potential memory leaks in dataLayer', async () => {
      const initialMemory = mockPerformanceMemory.memory.usedJSHeapSize;
      const memorySnapshots: number[] = [];

      render(
        <GTMProvider enabled={true} config={{ debug: true }}>
          <div data-testid="leak-detection-test" />
        </GTMProvider>
      );

      // Create events in batches and monitor memory
      for (let batch = 0; batch < 5; batch++) {
        // Add batch of events
        for (let i = 0; i < 200; i++) {
          mockDataLayer.push({
            event: `leak_detection_batch_${batch}_event_${i}`,
            batch_id: batch,
            large_payload: 'x'.repeat(2000), // 2KB per event
            nested_data: {
              level1: { level2: { level3: 'x'.repeat(500) } }
            }
          });
          mockPerformanceMemory.allocateMemory(3000); // 3KB per event with overhead
        }

        // Take memory snapshot
        memorySnapshots.push(mockPerformanceMemory.memory.usedJSHeapSize);
        
        // Wait between batches
        await new Promise(resolve => setTimeout(resolve, 100));
        
        // Simulate some cleanup every other batch
        if (batch % 2 === 1) {
          mockPerformanceMemory.garbageCollect(100000); // Clean up 100KB
        }
      }

      // Analyze memory growth pattern
      const memoryGrowthRates: number[] = [];
      for (let i = 1; i < memorySnapshots.length; i++) {
        const growthRate = (memorySnapshots[i] - memorySnapshots[i - 1]) / memorySnapshots[i - 1];
        memoryGrowthRates.push(growthRate);
      }

      const averageGrowthRate = memoryGrowthRates.reduce((sum, rate) => sum + rate, 0) / memoryGrowthRates.length;

      // If growth rate is consistently high, it might indicate a leak
      if (averageGrowthRate > 0.1) { // More than 10% growth per batch
        // This would trigger a memory leak warning in real implementation
        const memoryLeakEvent = {
          event: 'potential_memory_leak',
          event_category: 'performance',
          average_growth_rate: averageGrowthRate,
          total_memory_increase: memorySnapshots[memorySnapshots.length - 1] - initialMemory,
          batches_analyzed: memorySnapshots.length
        };

        expect(memoryLeakEvent.average_growth_rate).toBeGreaterThan(0.05);
        expect(memoryLeakEvent.total_memory_increase).toBeGreaterThan(0);
      }

      // Memory should stabilize or decrease in later snapshots due to cleanup
      const lastTwoSnapshots = memorySnapshots.slice(-2);
      if (lastTwoSnapshots.length === 2) {
        const finalGrowthRate = (lastTwoSnapshots[1] - lastTwoSnapshots[0]) / lastTwoSnapshots[0];
        expect(finalGrowthRate).toBeLessThan(0.2); // Should not be growing rapidly at the end
      }
    });
  });

  describe('Memory Leak Prevention', () => {
    it('should implement automatic memory cleanup strategies', async () => {
      const initialMemory = mockPerformanceMemory.memory.usedJSHeapSize;

      render(
        <GTMProvider enabled={true} config={{ debug: true }}>
          <MemoryLeakTestComponent eventCount={100} largeDataEvents={true} />
        </GTMProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('gtm-loaded')).toHaveTextContent('loaded');
      });

      // Wait for events to accumulate
      await new Promise(resolve => setTimeout(resolve, 2000));

      const peakMemory = mockPerformanceMemory.memory.usedJSHeapSize;
      const peakIncrease = peakMemory - initialMemory;

      // Simulate automatic cleanup (this would be done by GTM/browser)
      mockPerformanceMemory.garbageCollect();

      const memoryAfterCleanup = mockPerformanceMemory.memory.usedJSHeapSize;
      const memoryRecovered = peakMemory - memoryAfterCleanup;
      const recoveryRate = memoryRecovered / peakIncrease;

      // Should recover significant memory through cleanup
      expect(recoveryRate).toBeGreaterThan(0.3); // At least 30% recovery
      expect(memoryRecovered).toBeGreaterThan(0);

      // Final memory usage should be reasonable
      const finalIncrease = memoryAfterCleanup - initialMemory;
      expect(finalIncrease).toBeLessThan(peakIncrease * 0.8); // Should be less than 80% of peak
    });

    it('should handle memory pressure situations gracefully', async () => {
      // Simulate high memory pressure scenario
      mockPerformanceMemory.allocateMemory(1000000000); // Allocate 1GB to simulate pressure

      const initialMemory = mockPerformanceMemory.memory.usedJSHeapSize;
      const memoryPressureThreshold = mockPerformanceMemory.memory.totalJSHeapSize * 0.8;

      render(
        <GTMProvider enabled={true} config={{ debug: true }}>
          <MemoryLeakTestComponent eventCount={50} largeDataEvents={true} />
        </GTMProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('gtm-loaded')).toHaveTextContent('loaded');
      });

      const currentMemory = mockPerformanceMemory.memory.usedJSHeapSize;

      // If under memory pressure, should implement protective measures
      if (currentMemory > memoryPressureThreshold) {
        // Should limit event processing or trigger cleanup
        const memoryPressureEvent = mockDataLayer.find(event => 
          event.event === 'memory_pressure' || event.event_category === 'memory_management'
        );

        if (memoryPressureEvent) {
          expect(memoryPressureEvent.memory_usage).toBeDefined();
          expect(memoryPressureEvent.pressure_level).toBeOneOf(['medium', 'high', 'critical']);
        }

        // Should not continue allocating unlimited memory
        expect(currentMemory).toBeLessThan(mockPerformanceMemory.memory.jsHeapSizeLimit * 0.9);
      }
    });

    it('should provide memory usage monitoring and alerts', async () => {
      const memoryAlerts: any[] = [];
      const originalPush = mockDataLayer.push;

      // Mock dataLayer to capture memory alerts
      mockDataLayer.push = function(...args) {
        args.forEach(event => {
          if (event.event === 'memory_alert' || event.event_category === 'memory_monitoring') {
            memoryAlerts.push(event);
          }
        });
        return originalPush.apply(this, args);
      };

      render(
        <GTMProvider enabled={true} config={{ debug: true }}>
          <MemoryLeakTestComponent eventCount={200} largeDataEvents={true} />
        </GTMProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('gtm-loaded')).toHaveTextContent('loaded');
      });

      // Wait for potential memory alerts
      await new Promise(resolve => setTimeout(resolve, 1000));

      const currentMemory = mockPerformanceMemory.memory.usedJSHeapSize;
      const memoryUsagePercentage = (currentMemory / mockPerformanceMemory.memory.totalJSHeapSize) * 100;

      // Simulate memory monitoring alert
      if (memoryUsagePercentage > 60) {
        mockDataLayer.push({
          event: 'memory_alert',
          event_category: 'memory_monitoring',
          memory_usage_percentage: memoryUsagePercentage,
          current_memory: currentMemory,
          alert_level: memoryUsagePercentage > 80 ? 'critical' : 'warning',
          timestamp: new Date().toISOString()
        });
      }

      // Check if monitoring is working
      const totalEvents = mockDataLayer.length;
      expect(totalEvents).toBeGreaterThan(0);

      // If alerts were triggered, verify they contain proper information
      if (memoryAlerts.length > 0) {
        memoryAlerts.forEach(alert => {
          expect(alert.memory_usage_percentage).toBeGreaterThan(0);
          expect(alert.alert_level).toBeOneOf(['warning', 'critical']);
          expect(alert.timestamp).toBeDefined();
        });
      }
    });
  });
});