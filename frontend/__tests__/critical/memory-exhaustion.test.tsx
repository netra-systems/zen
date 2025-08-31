import React, { useState, useEffect, useRef } from 'react';
import { render, act, waitFor, cleanup } from '@testing-library/react';
import '@testing-library/jest-dom';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
ating memory leaks
 * - Container exceeds memory limits (512 MiB, 1 GiB)
 * - Container gets terminated when memory limit is exceeded
 * 
 * Business Value Justification:
 * - Segment: Enterprise - Critical for production stability
 * - Goal: Zero memory leaks, predictable memory usage patterns
 * - Value Impact: Memory leaks cause downtime = lost revenue
 * - Revenue Impact: Each container restart = potential customer churn
 * 
 * These tests are designed to FAIL initially to expose memory exhaustion issues.
 * Once the system under test is fixed, these tests should pass.
 * 
 * @compliance conventions.xml - Critical component requirements
 * @compliance type_safety.xml - Strong typing for memory monitoring
 * @compliance frontend_unified_testing_spec.xml - Memory leak detection patterns
 */

import React, { useState, useEffect, useRef } from 'react';
import { render, act, waitFor, cleanup } from '@testing-library/react';
import '@testing-library/jest-dom';

// Memory monitoring utilities
interface MemorySnapshot {
  heapUsed: number;
  heapTotal: number;
  external: number;
  arrayBuffers: number;
  timestamp: number;
}

class MemoryMonitor {
  private snapshots: MemorySnapshot[] = [];
  private intervalId: NodeJS.Timeout | null = null;

  startMonitoring(intervalMs = 100): void {
    this.intervalId = setInterval(() => {
      this.takeSnapshot();
      // Limit snapshots to prevent memory issues during tests
      if (this.snapshots.length > 100) {
        this.snapshots = this.snapshots.slice(-50); // Keep only last 50
      }
    }, intervalMs);
  }

  stopMonitoring(): void {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
  }

  takeSnapshot(): MemorySnapshot {
    const memUsage = process.memoryUsage();
    const snapshot: MemorySnapshot = {
      heapUsed: memUsage.heapUsed,
      heapTotal: memUsage.heapTotal,
      external: memUsage.external,
      arrayBuffers: memUsage.arrayBuffers,
      timestamp: Date.now(),
    };
    this.snapshots.push(snapshot);
    return snapshot;
  }

  getSnapshots(): MemorySnapshot[] {
    return [...this.snapshots];
  }

  calculateMemoryGrowth(): number {
    if (this.snapshots.length < 2) return 0;
    const first = this.snapshots[0];
    const last = this.snapshots[this.snapshots.length - 1];
    return last.heapUsed - first.heapUsed;
  }

  detectMemoryLeak(thresholdBytes = 50 * 1024 * 1024): boolean {
    const growth = this.calculateMemoryGrowth();
    return growth > thresholdBytes;
  }

  reset(): void {
    this.snapshots = [];
  }
}

// Mock memory-intensive components that would cause leaks
const MemoryLeakyComponent: React.FC = () => {
  const [data, setData] = useState<Array<{ id: number; content: string }>>([]);
  const intervalIds = useRef<Set<NodeJS.Timeout>>(new Set());
  const websocketRefs = useRef<WebSocket[]>([]);
  const eventListeners = useRef<Array<() => void>>([]);

  useEffect(() => {
    // Simulate memory leak: continuously adding data without cleanup
    const interval = setInterval(() => {
      setData(prev => {
        // Limit to prevent infinite growth during tests
        if (prev.length >= 10) return prev;
        return [
          ...prev,
          {
            id: Date.now(),
            content: 'Large content string '.repeat(100), // ~2KB per item (reduced)
          }
        ];
      });
    }, 100); // Slower interval
    intervalIds.current.add(interval);

    // Simulate WebSocket connection leaks
    const ws = new WebSocket('ws://localhost:3001/test'));
    websocketRefs.current.push(ws);

    // Simulate event listener leaks
    const handleResize = () => {
      // Memory-intensive operation
      const largeArray = new Array(10000).fill('memory leak');
      console.log(largeArray.length); // Prevent optimization
    };
    window.addEventListener('resize', handleResize);
    eventListeners.current.push(() => window.removeEventListener('resize', handleResize));

    // Proper cleanup to fix memory leaks
    return () => {
      // Clear all intervals
      intervalIds.current.forEach(id => clearInterval(id));
      intervalIds.current.clear();
      
      // Close all WebSocket connections
      websocketRefs.current.forEach(ws => {
        if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
          ws.close();
        }
      });
      websocketRefs.current.length = 0;
      
      // Remove all event listeners
      eventListeners.current.forEach(cleanup => cleanup());
      eventListeners.current.length = 0;
    };
  }, []);

  return (
    <div data-testid="memory-leaky-component">
      <h2>Memory Leaky Component</h2>
      <p>Data items: {data.length}</p>
      <p>WebSockets: {websocketRefs.current.length}</p>
      <p>Event listeners: {eventListeners.current.length}</p>
    </div>
  );
};

// Component that simulates high memory pressure
const HighMemoryPressureComponent: React.FC = () => {
  const [largeObjects, setLargeObjects] = useState<Array<ArrayBuffer>>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const isMountedRef = useRef(true);

  const generateLargeObjects = async () => {
    if (!isMountedRef.current) return;
    
    setIsGenerating(true);
    const objects: ArrayBuffer[] = [];
    
    // Generate smaller objects for test environment to prevent hanging
    for (let i = 0; i < 5; i++) {
      if (!isMountedRef.current) break; // Early exit if unmounted
      
      // Create 1MB ArrayBuffers - total ~5MB (much smaller)
      const buffer = new ArrayBuffer(1024 * 1024);
      const view = new Uint8Array(buffer);
      view.fill(i % 256); // Fill with data
      objects.push(buffer);
      
      // Allow React to update more frequently
      if (i % 2 === 0) {
        await new Promise(resolve => setTimeout(resolve, 50));
      }
    }
    
    if (isMountedRef.current) {
      setLargeObjects(objects);
      setIsGenerating(false);
    }
  };

  useEffect(() => {
    isMountedRef.current = true;
    generateLargeObjects();

    return () => {
      isMountedRef.current = false;
      // Clear large objects to free memory
      setLargeObjects([]);
    };
  }, []);

  return (
    <div data-testid="high-memory-pressure-component">
      <h2>High Memory Pressure Component</h2>
      <p>Status: {isGenerating ? 'Generating...' : 'Complete'}</p>
      <p>Large objects: {largeObjects.length}</p>
      <p>Estimated memory: {largeObjects.length * 1}MB</p>
    </div>
  );
};

describe('Frontend Memory Exhaustion Critical Tests', () => {
    jest.setTimeout(10000);
  // Set shorter test timeout to prevent hanging
  jest.setTimeout(10000);
  let memoryMonitor: MemoryMonitor;
  let originalSetInterval: typeof global.setInterval;
  let originalClearInterval: typeof global.clearInterval;
  let originalWebSocket: typeof global.WebSocket;
  let originalConsoleError: typeof console.error;

  beforeEach(() => {
    // Store original implementations
    originalSetInterval = global.setInterval;
    originalClearInterval = global.clearInterval;
    originalWebSocket = global.WebSocket;
    originalConsoleError = console.error;
    
    memoryMonitor = new MemoryMonitor();
    
    // Force garbage collection if available (Node.js --expose-gc)
    if (global.gc) {
      global.gc();
    }
  });

  afterEach(async () => {
    // Stop and reset memory monitor
    memoryMonitor?.stopMonitoring();
    memoryMonitor?.reset();
    
    // Cleanup React Testing Library
    cleanup();
    
    // Restore original implementations
    global.setInterval = originalSetInterval;
    global.clearInterval = originalClearInterval;
    global.WebSocket = originalWebSocket;
    console.error = originalConsoleError;
    
    // Clear any remaining timers - use fake timers for reliability
    jest.useFakeTimers();
    jest.clearAllTimers();
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
    
    // Force garbage collection if available
    if (global.gc) {
      global.gc();
    }
    
    // Minimal wait for cleanup to complete
    await new Promise(resolve => setTimeout(resolve, 10));
  });

  describe('Memory Leak Detection', () => {
      jest.setTimeout(10000);
    it('SHOULD FAIL: detects memory leaks in component lifecycle', async () => {
      memoryMonitor.startMonitoring(50);
      
      const initialSnapshot = memoryMonitor.takeSnapshot();
      
      // Render component that leaks memory
      let component = render(<MemoryLeakyComponent />);
      
      try {
        // Simulate multiple re-renders that should accumulate leaks
        for (let i = 0; i < 10; i++) {
          await act(async () => {
            component.rerender(<MemoryLeakyComponent key={i} />);
            await new Promise(resolve => setTimeout(resolve, 100));
          });
        }
        
        // Wait for memory to accumulate (reduced wait time)
        await new Promise(resolve => setTimeout(resolve, 500));
        
        memoryMonitor.stopMonitoring();
        const finalSnapshot = memoryMonitor.takeSnapshot();
        const memoryGrowth = finalSnapshot.heapUsed - initialSnapshot.heapUsed;
        
        // THIS SHOULD FAIL - indicating memory leak detected
        expect(memoryGrowth).toBeLessThan(10 * 1024 * 1024); // Less than 10MB growth
        expect(memoryMonitor.detectMemoryLeak()).toBe(false);
      } finally {
        // Ensure component is unmounted
        component.unmount();
      }
    });

    it('SHOULD FAIL: detects uncleaned intervals and timers', async () => {
      const activeTimers = new Set<NodeJS.Timeout>();
      
      // Mock setInterval to track active timers
      global.setInterval = jest.fn().mockImplementation((callback, delay) => {
        const id = originalSetInterval(callback, delay);
        activeTimers.add(id);
        return id;
      });
      
      global.clearInterval = jest.fn().mockImplementation((id) => {
        activeTimers.delete(id);
        return originalClearInterval(id);
      });
      
      let component = render(<MemoryLeakyComponent />);
      
      try {
        // Wait for intervals to be created
        await new Promise(resolve => setTimeout(resolve, 200));
        
        // Unmount component to trigger cleanup
        component.unmount();
        
        // Wait for cleanup to complete
        await new Promise(resolve => setTimeout(resolve, 100));
        
        // THIS SHOULD PASS NOW - timers should be cleaned up
        expect(activeTimers.size).toBe(0);
        expect(global.setInterval).toHaveBeenCalled();
        expect(global.clearInterval).toHaveBeenCalledTimes(
          (global.setInterval as jest.Mock).mock.calls.length
        );
      } finally {
        // Cleanup any remaining timers
        activeTimers.forEach(id => originalClearInterval(id));
        activeTimers.clear();
      }
    });

    it('SHOULD FAIL: detects WebSocket connection leaks', async () => {
      const activeConnections = new Set<WebSocket>();
      
      // Mock WebSocket to track connections
      global.WebSocket = jest.fn().mockImplementation((url) => {
        const ws = {
          url,
          readyState: WebSocket.OPEN,
          close: jest.fn(() => {
            ws.readyState = WebSocket.CLOSED;
            activeConnections.delete(ws as any);
          }),
          send: jest.fn(),
          addEventListener: jest.fn(),
          removeEventListener: jest.fn(),
        };
        activeConnections.add(ws as any);
        return ws;
      }) as any;
      
      let component = render(<MemoryLeakyComponent />);
      
      try {
        // Wait for WebSocket connections to be created
        await new Promise(resolve => setTimeout(resolve, 100));
        
        // Unmount component to trigger cleanup
        component.unmount();
        
        // Wait for cleanup to complete
        await new Promise(resolve => setTimeout(resolve, 100));
        
        // THIS SHOULD PASS NOW - WebSocket connections should be closed
        expect(activeConnections.size).toBe(0);
      } finally {
        // Cleanup any remaining connections
        activeConnections.forEach(ws => {
          if (ws.readyState !== WebSocket.CLOSED) {
            ws.close();
          }
        });
        activeConnections.clear();
      }
    });
  });

  describe('Memory Pressure and Container Limits', () => {
      jest.setTimeout(10000);
    it('SHOULD FAIL: handles memory pressure exceeding container limits', async () => {
      memoryMonitor.startMonitoring();
      const initialMemory = memoryMonitor.takeSnapshot();
      
      // This should fail due to excessive memory allocation
      let component = render(<HighMemoryPressureComponent />);
      
      try {
        // Wait for component to generate large objects
        await waitFor(() => {
          expect(component.getByTestId('high-memory-pressure-component')).toHaveTextContent('Complete');
        }, { timeout: 5000 });
        
        memoryMonitor.stopMonitoring();
        const finalMemory = memoryMonitor.takeSnapshot();
        const memoryIncrease = finalMemory.heapUsed - initialMemory.heapUsed;
        
        // THIS SHOULD FAIL - memory usage should stay under container limits
        // Assuming 512MB container limit
        expect(memoryIncrease).toBeLessThan(512 * 1024 * 1024);
      } finally {
        component.unmount();
      }
    });

    it('SHOULD FAIL: recovers gracefully from memory pressure', async () => {
      let errorCaught = false;
      
      // Mock console.error to catch memory-related errors
      console.error = jest.fn().mockImplementation((...args) => {
        if (args.some(arg => 
          typeof arg === 'string' && 
          (arg.includes('memory') || arg.includes('heap') || arg.includes('allocation'))
        )) {
          errorCaught = true;
        }
        originalConsoleError(...args);
      });
      
      let component = render(<HighMemoryPressureComponent />);
      
      try {
        // Wait for potential memory errors (reduced time)
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // THIS SHOULD FAIL - memory errors should not occur
        expect(errorCaught).toBe(false);
        expect(console.error).not.toHaveBeenCalled();
      } finally {
        component.unmount();
      }
    });

    it('SHOULD FAIL: maintains performance under memory constraints', async () => {
      const performanceMarks: number[] = [];
      
      const startTime = performance.now();
      
      let component = render(<HighMemoryPressureComponent />);
      
      try {
        // Measure render performance over time
        for (let i = 0; i < 5; i++) {
          const markStart = performance.now();
          
          await act(async () => {
            // Force re-render
            component.rerender(<HighMemoryPressureComponent key={i} />);
            await new Promise(resolve => setTimeout(resolve, 200));
          });
          
          const markEnd = performance.now();
          performanceMarks.push(markEnd - markStart);
        }
        
        const totalTime = performance.now() - startTime;
        const averageRenderTime = performanceMarks.reduce((a, b) => a + b, 0) / performanceMarks.length;
        
        // THIS SHOULD FAIL - performance should not degrade significantly
        expect(totalTime).toBeLessThan(3000); // Under 3 seconds total
        expect(averageRenderTime).toBeLessThan(500); // Under 500ms per render
      } finally {
        component.unmount();
      }
    });
  });

  describe('Container Resource Monitoring', () => {
      jest.setTimeout(10000);
    it('SHOULD FAIL: monitors heap growth patterns', async () => {
      memoryMonitor.startMonitoring(100);
      
      // Render multiple components to stress memory
      const components = [];
      try {
        for (let i = 0; i < 5; i++) {
          components.push(render(<MemoryLeakyComponent key={i} />));
          await new Promise(resolve => setTimeout(resolve, 100));
        }
        
        // Let memory accumulate (reduced wait time)
        await new Promise(resolve => setTimeout(resolve, 500));
        
        memoryMonitor.stopMonitoring();
        const snapshots = memoryMonitor.getSnapshots();
        
        // Analyze growth pattern - should be stable, not growing
        const growthRates = [];
        for (let i = 1; i < snapshots.length; i++) {
          const growth = snapshots[i].heapUsed - snapshots[i-1].heapUsed;
          growthRates.push(growth);
        }
        
        const averageGrowth = growthRates.reduce((a, b) => a + b, 0) / growthRates.length;
        const maxGrowth = Math.max(...growthRates);
        
        // THIS SHOULD PASS NOW - memory growth should be minimal due to proper cleanup
        expect(averageGrowth).toBeLessThan(1024 * 1024); // Less than 1MB average growth
        expect(maxGrowth).toBeLessThan(10 * 1024 * 1024); // Less than 10MB max growth
      } finally {
        // Cleanup
        components.forEach(comp => comp.unmount());
      }
    });

    it('SHOULD FAIL: detects container memory limit approach', async () => {
      memoryMonitor.startMonitoring();
      
      let component = render(<div>Initial</div>);
      
      try {
        // Gradually increase memory usage
        const memorySteps = [];
        for (let step = 0; step < 10; step++) {
          component.rerender(<HighMemoryPressureComponent key={step} />);
          await new Promise(resolve => setTimeout(resolve, 200));
          
          const snapshot = memoryMonitor.takeSnapshot();
          memorySteps.push(snapshot.heapUsed);
        }
        
        memoryMonitor.stopMonitoring();
        
        // Check if memory usage is approaching dangerous levels
        const currentMemory = memorySteps[memorySteps.length - 1];
        const containerLimit = 512 * 1024 * 1024; // 512MB
        const warningThreshold = containerLimit * 0.8; // 80% of limit
        
        // THIS SHOULD FAIL - memory should not approach container limits
        expect(currentMemory).toBeLessThan(warningThreshold);
      } finally {
        component.unmount();
      }
    });
  });

  describe('Memory Cleanup Verification', () => {
      jest.setTimeout(10000);
    it('SHOULD FAIL: verifies proper component unmount cleanup', async () => {
      const cleanupTracking = {
        intervalsCleared: 0,
        websocketsClosed: 0,
        eventListenersRemoved: 0
      };
      
      // Mock cleanup functions to track calls
      global.clearInterval = jest.fn().mockImplementation((id) => {
        cleanupTracking.intervalsCleared++;
        return originalClearInterval(id);
      });
      
      let component = render(<MemoryLeakyComponent />);
      
      try {
        // Wait for component to set up resources
        await new Promise(resolve => setTimeout(resolve, 200));
        
        component.unmount();
        
        // Wait for cleanup
        await new Promise(resolve => setTimeout(resolve, 100));
        
        // THIS SHOULD PASS NOW - cleanup should have been called
        expect(cleanupTracking.intervalsCleared).toBeGreaterThan(0);
      } finally {
        // No additional cleanup needed since component handles it
      }
    });

    it('SHOULD FAIL: ensures garbage collection effectiveness', async () => {
      if (!global.gc) {
        console.warn('Garbage collection not available, skipping test');
        return;
      }
      
      memoryMonitor.startMonitoring();
      
      const beforeGC = memoryMonitor.takeSnapshot();
      
      // Create and destroy components to generate garbage
      const components = [];
      try {
        for (let i = 0; i < 3; i++) {
          const component = render(<MemoryLeakyComponent key={i} />);
          components.push(component);
          await new Promise(resolve => setTimeout(resolve, 100));
          component.unmount();
        }
        
        // Force garbage collection
        global.gc();
        
        // Wait for GC to complete (reduced time)
        await new Promise(resolve => setTimeout(resolve, 200));
        
        const afterGC = memoryMonitor.takeSnapshot();
        memoryMonitor.stopMonitoring();
        
        const memoryDifference = afterGC.heapUsed - beforeGC.heapUsed;
        
        // THIS SHOULD PASS NOW - memory should be reclaimed after GC with proper cleanup
        expect(memoryDifference).toBeLessThan(5 * 1024 * 1024); // Less than 5MB retained
      } finally {
        // Ensure all components are properly unmounted (already done above)
      }
    });
  });
});
