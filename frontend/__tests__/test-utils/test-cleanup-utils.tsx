/**
 * Test Cleanup Utilities for Integration Tests
 * CRITICAL: Ensures proper cleanup of async operations to prevent test interference
 * Addresses memory leaks and resource cleanup issues
 * ≤300 lines, ≤8 lines per function
 */

import { act, cleanup } from '@testing-library/react';
import { HeartbeatRegistry } from './heartbeat-timing-fix';

export interface CleanupTracker {
  resources: Set<string>;
  timers: Set<NodeJS.Timeout>;
  promises: Set<Promise<any>>;
  listeners: Map<string, Function[]>;
  cleanupFunctions: Function[];
}

/**
 * Global cleanup tracker
 */
export class GlobalCleanupTracker {
  private static instance: GlobalCleanupTracker;
  private tracker: CleanupTracker;

  private constructor() {
    this.tracker = {
      resources: new Set(),
      timers: new Set(),
      promises: new Set(),
      listeners: new Map(),
      cleanupFunctions: []
    };
  }

  static getInstance(): GlobalCleanupTracker {
    if (!this.instance) {
      this.instance = new GlobalCleanupTracker();
    }
    return this.instance;
  }

  addResource(resourceId: string): void {
    this.tracker.resources.add(resourceId);
  }

  addTimer(timerId: NodeJS.Timeout): void {
    this.tracker.timers.add(timerId);
  }

  addPromise(promise: Promise<any>): void {
    this.tracker.promises.add(promise);
  }

  addListener(event: string, listener: Function): void {
    if (!this.tracker.listeners.has(event)) {
      this.tracker.listeners.set(event, []);
    }
    this.tracker.listeners.get(event)!.push(listener);
  }

  addCleanupFunction(cleanupFn: Function): void {
    this.tracker.cleanupFunctions.push(cleanupFn);
  }

  async cleanup(): Promise<void> {
    await act(async () => {
      // Run custom cleanup functions
      for (const cleanupFn of this.tracker.cleanupFunctions) {
        try {
          await cleanupFn();
        } catch (error) {
          console.warn('Cleanup function failed:', error);
        }
      }

      // Clear timers
      for (const timerId of this.tracker.timers) {
        clearTimeout(timerId);
        clearInterval(timerId);
      }

      // Wait for pending promises (with timeout)
      if (this.tracker.promises.size > 0) {
        try {
          await Promise.race([
            Promise.allSettled([...this.tracker.promises]),
            new Promise(resolve => setTimeout(resolve, 1000))
          ]);
        } catch (error) {
          console.warn('Promise cleanup failed:', error);
        }
      }

      // Reset tracker
      this.tracker = {
        resources: new Set(),
        timers: new Set(),
        promises: new Set(),
        listeners: new Map(),
        cleanupFunctions: []
      };
    });
  }

  getStats(): { resources: number; timers: number; promises: number; listeners: number } {
    return {
      resources: this.tracker.resources.size,
      timers: this.tracker.timers.size,
      promises: this.tracker.promises.size,
      listeners: Array.from(this.tracker.listeners.values()).reduce((sum, arr) => sum + arr.length, 0)
    };
  }
}

/**
 * Async cleanup utilities
 */
export const AsyncCleanupUtils = {
  async waitForAsyncOperations(timeout = 1000): Promise<void> {
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, Math.min(timeout, 100)));
    });
  },

  async flushPromises(): Promise<void> {
    await act(async () => {
      await new Promise(resolve => setImmediate ? setImmediate(resolve) : setTimeout(resolve, 0));
    });
  },

  async flushMicrotasks(): Promise<void> {
    await act(async () => {
      await new Promise(resolve => queueMicrotask(() => resolve(undefined)));
    });
  },

  async flushTimers(): Promise<void> {
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 0));
    });
  },

  async fullFlush(): Promise<void> {
    await this.flushMicrotasks();
    await this.flushPromises();
    await this.flushTimers();
    await this.waitForAsyncOperations(50);
  }
};

/**
 * WebSocket cleanup utilities
 */
export const WebSocketCleanupUtils = {
  cleanupConnections: new Set<any>(),

  registerConnection(connection: any): void {
    this.cleanupConnections.add(connection);
  },

  async cleanup(): Promise<void> {
    await act(async () => {
      for (const connection of this.cleanupConnections) {
        try {
          if (connection && typeof connection.close === 'function') {
            connection.close();
          }
          if (connection && typeof connection.cleanup === 'function') {
            connection.cleanup();
          }
        } catch (error) {
          console.warn('WebSocket cleanup failed:', error);
        }
      }
      this.cleanupConnections.clear();
    });
  }
};

/**
 * React cleanup utilities
 */
export const ReactCleanupUtils = {
  async cleanupComponents(): Promise<void> {
    await act(async () => {
      cleanup();
      await AsyncCleanupUtils.fullFlush();
    });
  },

  async cleanupHooks(): Promise<void> {
    await act(async () => {
      // Force cleanup of any remaining hook effects
      await new Promise(resolve => setTimeout(resolve, 10));
    });
  },

  async cleanupContext(): Promise<void> {
    await act(async () => {
      // Clean up any context providers
      await AsyncCleanupUtils.flushMicrotasks();
    });
  }
};

/**
 * Store cleanup utilities
 */
export const StoreCleanupUtils = {
  stores: new Set<any>(),

  registerStore(store: any): void {
    this.stores.add(store);
  },

  async cleanup(): Promise<void> {
    await act(async () => {
      for (const store of this.stores) {
        try {
          if (store && typeof store.reset === 'function') {
            store.reset();
          }
          if (store && typeof store.cleanup === 'function') {
            store.cleanup();
          }
        } catch (error) {
          console.warn('Store cleanup failed:', error);
        }
      }
      this.stores.clear();
    });
  }
};

/**
 * Comprehensive test cleanup
 */
export const TestCleanup = {
  async beforeEach(): Promise<void> {
    // Reset global state
    const tracker = GlobalCleanupTracker.getInstance();
    await tracker.cleanup();
  },

  async afterEach(): Promise<void> {
    await act(async () => {
      // Cleanup in order of dependency
      await WebSocketCleanupUtils.cleanup();
      await StoreCleanupUtils.cleanup();
      HeartbeatRegistry.cleanupAll();
      await ReactCleanupUtils.cleanupComponents();
      await AsyncCleanupUtils.fullFlush();
      
      const tracker = GlobalCleanupTracker.getInstance();
      await tracker.cleanup();
    });
  },

  async afterAll(): Promise<void> {
    await this.afterEach();
    
    // Final cleanup
    HeartbeatRegistry.cleanupAll();
    WebSocketCleanupUtils.cleanupConnections.clear();
    StoreCleanupUtils.stores.clear();
  }
};

/**
 * Cleanup decorator for test functions
 */
export const withCleanup = <T extends any[], R>(
  testFn: (...args: T) => Promise<R>
) => {
  return async (...args: T): Promise<R> => {
    await TestCleanup.beforeEach();
    
    try {
      return await testFn(...args);
    } finally {
      await TestCleanup.afterEach();
    }
  };
};

/**
 * Auto-cleanup hook for test setup
 */
export const useTestCleanup = () => {
  const tracker = GlobalCleanupTracker.getInstance();

  const addCleanup = (cleanupFn: Function) => {
    tracker.addCleanupFunction(cleanupFn);
  };

  const addResource = (resourceId: string) => {
    tracker.addResource(resourceId);
  };

  const addTimer = (timerId: NodeJS.Timeout) => {
    tracker.addTimer(timerId);
  };

  return {
    addCleanup,
    addResource,
    addTimer,
    cleanup: () => tracker.cleanup(),
    stats: () => tracker.getStats()
  };
};

/**
 * Memory leak detection utilities
 */
export const MemoryLeakDetection = {
  initialStats: null as any,

  captureInitialState(): void {
    this.initialStats = {
      timers: GlobalCleanupTracker.getInstance().getStats().timers,
      promises: GlobalCleanupTracker.getInstance().getStats().promises,
      listeners: GlobalCleanupTracker.getInstance().getStats().listeners
    };
  },

  checkForLeaks(): { hasLeaks: boolean; details: any } {
    if (!this.initialStats) {
      return { hasLeaks: false, details: null };
    }

    const currentStats = GlobalCleanupTracker.getInstance().getStats();
    const leaks = {
      timers: currentStats.timers - this.initialStats.timers,
      promises: currentStats.promises - this.initialStats.promises,
      listeners: currentStats.listeners - this.initialStats.listeners
    };

    const hasLeaks = Object.values(leaks).some(leak => leak > 0);
    
    return {
      hasLeaks,
      details: hasLeaks ? leaks : null
    };
  }
};

/**
 * Export all utilities
 */
export const CleanupUtils = {
  Global: GlobalCleanupTracker,
  Async: AsyncCleanupUtils,
  WebSocket: WebSocketCleanupUtils,
  React: ReactCleanupUtils,
  Store: StoreCleanupUtils,
  Test: TestCleanup,
  Memory: MemoryLeakDetection,
  withCleanup,
  useTestCleanup
};

export default CleanupUtils;