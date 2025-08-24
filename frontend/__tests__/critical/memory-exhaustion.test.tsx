/**
 * Frontend Memory Exhaustion Critical Tests
 * 
 * Tests for critical memory exhaustion issues found in GCP Cloud Run logs:
 * - Memory usage grows over time indicating memory leaks
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
  const [intervalIds] = useState<Set<NodeJS.Timeout>>(new Set());
  const websocketRefs = useRef<WebSocket[]>([]);
  const eventListeners = useRef<Array<() => void>>([]);

  useEffect(() => {
    // Simulate memory leak: continuously adding data without cleanup
    const interval = setInterval(() => {
      act(() => {
        setData(prev => [
          ...prev,
          {
            id: Date.now(),
            content: 'Large content string '.repeat(1000), // ~20KB per item
          }
        ]);
      });
    }, 10);
    intervalIds.add(interval);

    // Simulate WebSocket connection leaks
    const ws = new WebSocket('ws://localhost:3001/memory-test');
    websocketRefs.current.push(ws);

    // Simulate event listener leaks
    const handleResize = () => {
      // Memory-intensive operation
      const largeArray = new Array(10000).fill('memory leak');
      console.log(largeArray.length); // Prevent optimization
    };
    window.addEventListener('resize', handleResize);
    eventListeners.current.push(() => window.removeEventListener('resize', handleResize));

    // Missing cleanup - this is the leak!
    // return () => {
    //   clearInterval(interval);
    //   websocketRefs.current.forEach(ws => ws.close());
    //   eventListeners.current.forEach(cleanup => cleanup());
    // };
  }, [intervalIds]);

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

  const generateLargeObjects = async () => {
    setIsGenerating(true);
    const objects: ArrayBuffer[] = [];
    
    // Generate objects that exceed typical container memory limits
    for (let i = 0; i < 50; i++) {
      // Create 10MB ArrayBuffers - total ~500MB
      const buffer = new ArrayBuffer(10 * 1024 * 1024);
      const view = new Uint8Array(buffer);
      view.fill(i % 256); // Fill with data
      objects.push(buffer);
      
      // Allow React to update
      if (i % 10 === 0) {
        await new Promise(resolve => setTimeout(resolve, 10));
      }
    }
    
    setLargeObjects(objects);
    setIsGenerating(false);
  };

  useEffect(() => {
    generateLargeObjects();
  }, []);

  return (
    <div data-testid="high-memory-pressure-component">
      <h2>High Memory Pressure Component</h2>
      <p>Status: {isGenerating ? 'Generating...' : 'Complete'}</p>
      <p>Large objects: {largeObjects.length}</p>
      <p>Estimated memory: {largeObjects.length * 10}MB</p>
    </div>
  );
};

describe('Frontend Memory Exhaustion Critical Tests', () => {
  let memoryMonitor: MemoryMonitor;

  beforeEach(() => {
    memoryMonitor = new MemoryMonitor();
    // Force garbage collection if available (Node.js --expose-gc)
    if (global.gc) {
      global.gc();
    }
  });

  afterEach(() => {
    memoryMonitor.stopMonitoring();
    memoryMonitor.reset();
    cleanup();
    // Force garbage collection if available
    if (global.gc) {
      global.gc();
    }
  });

  describe('Memory Leak Detection', () => {
    it('SHOULD FAIL: detects memory leaks in component lifecycle', async () => {
      memoryMonitor.startMonitoring(50);
      
      const initialSnapshot = memoryMonitor.takeSnapshot();
      
      // Render component that leaks memory
      const { rerender } = render(<MemoryLeakyComponent />);
      
      // Simulate multiple re-renders that should accumulate leaks
      for (let i = 0; i < 10; i++) {
        await act(async () => {
          rerender(<MemoryLeakyComponent key={i} />);
          await new Promise(resolve => setTimeout(resolve, 100));
        });
      }
      
      // Wait for memory to accumulate
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      memoryMonitor.stopMonitoring();
      const finalSnapshot = memoryMonitor.takeSnapshot();
      const memoryGrowth = finalSnapshot.heapUsed - initialSnapshot.heapUsed;
      
      // THIS SHOULD FAIL - indicating memory leak detected
      expect(memoryGrowth).toBeLessThan(10 * 1024 * 1024); // Less than 10MB growth
      expect(memoryMonitor.detectMemoryLeak()).toBe(false);
    });

    it('SHOULD FAIL: detects uncleaned intervals and timers', async () => {
      const activeTimers = new Set<NodeJS.Timeout>();
      
      // Mock setInterval to track active timers
      const originalSetInterval = global.setInterval;
      global.setInterval = jest.fn().mockImplementation((callback, delay) => {
        const id = originalSetInterval(callback, delay);
        activeTimers.add(id);
        return id;
      });
      
      const originalClearInterval = global.clearInterval;
      global.clearInterval = jest.fn().mockImplementation((id) => {
        activeTimers.delete(id);
        return originalClearInterval(id);
      });
      
      render(<MemoryLeakyComponent />);
      
      // Wait for intervals to be created
      await new Promise(resolve => setTimeout(resolve, 200));
      
      cleanup();
      
      // THIS SHOULD FAIL - timers not cleaned up
      expect(activeTimers.size).toBe(0);
      expect(global.setInterval).toHaveBeenCalled();
      expect(global.clearInterval).toHaveBeenCalledTimes(
        (global.setInterval as jest.Mock).mock.calls.length
      );
      
      // Cleanup
      activeTimers.forEach(id => clearInterval(id));
      global.setInterval = originalSetInterval;
      global.clearInterval = originalClearInterval;
    });

    it('SHOULD FAIL: detects WebSocket connection leaks', async () => {
      const activeConnections = new Set<WebSocket>();
      
      // Mock WebSocket to track connections
      const OriginalWebSocket = global.WebSocket;
      global.WebSocket = jest.fn().mockImplementation((url) => {
        const ws = {
          url,
          readyState: 1,
          close: jest.fn(() => activeConnections.delete(ws as any)),
          send: jest.fn(),
          addEventListener: jest.fn(),
          removeEventListener: jest.fn(),
        };
        activeConnections.add(ws as any);
        return ws;
      }) as any;
      
      render(<MemoryLeakyComponent />);
      
      // Wait for WebSocket connections to be created
      await new Promise(resolve => setTimeout(resolve, 100));
      
      cleanup();
      
      // THIS SHOULD FAIL - WebSocket connections not closed
      expect(activeConnections.size).toBe(0);
      
      // Cleanup
      activeConnections.forEach(ws => ws.close());
      global.WebSocket = OriginalWebSocket;
    });
  });

  describe('Memory Pressure and Container Limits', () => {
    it('SHOULD FAIL: handles memory pressure exceeding container limits', async () => {
      memoryMonitor.startMonitoring();
      const initialMemory = memoryMonitor.takeSnapshot();
      
      // This should fail due to excessive memory allocation
      const { getByTestId } = render(<HighMemoryPressureComponent />);
      
      // Wait for component to generate large objects
      await waitFor(() => {
        expect(getByTestId('high-memory-pressure-component')).toHaveTextContent('Complete');
      }, { timeout: 10000 });
      
      memoryMonitor.stopMonitoring();
      const finalMemory = memoryMonitor.takeSnapshot();
      const memoryIncrease = finalMemory.heapUsed - initialMemory.heapUsed;
      
      // THIS SHOULD FAIL - memory usage should stay under container limits
      // Assuming 512MB container limit
      expect(memoryIncrease).toBeLessThan(512 * 1024 * 1024);
    });

    it('SHOULD FAIL: recovers gracefully from memory pressure', async () => {
      let errorCaught = false;
      
      // Mock console.error to catch memory-related errors
      const originalError = console.error;
      console.error = jest.fn().mockImplementation((...args) => {
        if (args.some(arg => 
          typeof arg === 'string' && 
          (arg.includes('memory') || arg.includes('heap') || arg.includes('allocation'))
        )) {
          errorCaught = true;
        }
        originalError(...args);
      });
      
      try {
        render(<HighMemoryPressureComponent />);
        
        // Wait for potential memory errors
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        // THIS SHOULD FAIL - memory errors should not occur
        expect(errorCaught).toBe(false);
        expect(console.error).not.toHaveBeenCalled();
        
      } finally {
        console.error = originalError;
      }
    });

    it('SHOULD FAIL: maintains performance under memory constraints', async () => {
      const performanceMarks: number[] = [];
      
      const startTime = performance.now();
      
      render(<HighMemoryPressureComponent />);
      
      // Measure render performance over time
      for (let i = 0; i < 5; i++) {
        const markStart = performance.now();
        
        await act(async () => {
          // Force re-render
          await new Promise(resolve => setTimeout(resolve, 200));
        });
        
        const markEnd = performance.now();
        performanceMarks.push(markEnd - markStart);
      }
      
      const totalTime = performance.now() - startTime;
      const averageRenderTime = performanceMarks.reduce((a, b) => a + b, 0) / performanceMarks.length;
      
      // THIS SHOULD FAIL - performance should not degrade significantly
      expect(totalTime).toBeLessThan(5000); // Under 5 seconds total
      expect(averageRenderTime).toBeLessThan(500); // Under 500ms per render
    });
  });

  describe('Container Resource Monitoring', () => {
    it('SHOULD FAIL: monitors heap growth patterns', async () => {
      memoryMonitor.startMonitoring(100);
      
      // Render multiple components to stress memory
      const components = [];
      for (let i = 0; i < 5; i++) {
        components.push(render(<MemoryLeakyComponent key={i} />));
        await new Promise(resolve => setTimeout(resolve, 100));
      }
      
      // Let memory accumulate
      await new Promise(resolve => setTimeout(resolve, 1000));
      
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
      
      // THIS SHOULD FAIL - memory growth should be minimal
      expect(averageGrowth).toBeLessThan(1024 * 1024); // Less than 1MB average growth
      expect(maxGrowth).toBeLessThan(10 * 1024 * 1024); // Less than 10MB max growth
      
      // Cleanup
      components.forEach(comp => comp.unmount());
    });

    it('SHOULD FAIL: detects container memory limit approach', async () => {
      memoryMonitor.startMonitoring();
      
      const { rerender } = render(<div>Initial</div>);
      
      // Gradually increase memory usage
      const memorySteps = [];
      for (let step = 0; step < 10; step++) {
        rerender(<HighMemoryPressureComponent key={step} />);
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
    });
  });

  describe('Memory Cleanup Verification', () => {
    it('SHOULD FAIL: verifies proper component unmount cleanup', async () => {
      const cleanupTracking = {
        intervalsCleared: 0,
        websocketsClosed: 0,
        eventListenersRemoved: 0
      };
      
      // Mock cleanup functions to track calls
      const originalClearInterval = global.clearInterval;
      global.clearInterval = jest.fn().mockImplementation((id) => {
        cleanupTracking.intervalsCleared++;
        return originalClearInterval(id);
      });
      
      const { unmount } = render(<MemoryLeakyComponent />);
      
      // Wait for component to set up resources
      await new Promise(resolve => setTimeout(resolve, 200));
      
      unmount();
      
      // Wait for cleanup
      await new Promise(resolve => setTimeout(resolve, 100));
      
      // THIS SHOULD FAIL - cleanup should have been called
      expect(cleanupTracking.intervalsCleared).toBeGreaterThan(0);
      
      global.clearInterval = originalClearInterval;
    });

    it('SHOULD FAIL: ensures garbage collection effectiveness', async () => {
      if (!global.gc) {
        console.warn('Garbage collection not available, skipping test');
        return;
      }
      
      memoryMonitor.startMonitoring();
      
      const beforeGC = memoryMonitor.takeSnapshot();
      
      // Create and destroy components to generate garbage
      for (let i = 0; i < 3; i++) {
        const { unmount } = render(<MemoryLeakyComponent key={i} />);
        await new Promise(resolve => setTimeout(resolve, 100));
        unmount();
      }
      
      // Force garbage collection
      global.gc();
      
      // Wait for GC to complete
      await new Promise(resolve => setTimeout(resolve, 500));
      
      const afterGC = memoryMonitor.takeSnapshot();
      memoryMonitor.stopMonitoring();
      
      const memoryDifference = afterGC.heapUsed - beforeGC.heapUsed;
      
      // THIS SHOULD FAIL - memory should be reclaimed after GC
      expect(memoryDifference).toBeLessThan(5 * 1024 * 1024); // Less than 5MB retained
    });
  });
});
