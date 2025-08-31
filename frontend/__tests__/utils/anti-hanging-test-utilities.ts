/**
 * Anti-Hanging Test Utilities
 * 
 * This file provides utilities to prevent tests from hanging by:
 * 1. Limiting timeouts to reasonable values
 * 2. Cleaning up timers and resources
 * 3. Providing safe alternatives to problematic patterns
 * 
 * Usage in test files:
 * import { setupAntiHang, cleanupAntiHang, safeWaitFor } from '@/__tests__/utils/anti-hanging-test-utilities';
 * 
 * describe('Your Test Suite', () => {
 *   setupAntiHang();
 *   
 *   afterEach(() => {
 *     cleanupAntiHang();
 *   });
 * });
 */

import { TEST_TIMEOUTS, setTestTimeout } from '../config/test-timeouts';

// Maximum allowed timeout for any test operation
const MAX_TIMEOUT_MS = 5000;

// Track active timers for cleanup
let activeTimers = new Set<NodeJS.Timeout>();
let activeIntervals = new Set<NodeJS.Timeout>();

// Original timer functions
let originalSetTimeout: typeof setTimeout;
let originalSetInterval: typeof setInterval;
let originalClearTimeout: typeof clearTimeout;
let originalClearInterval: typeof clearInterval;

/**
 * Setup anti-hanging utilities for a test suite
 * Call this in your describe block
 */
export function setupAntiHang(customTimeout: number = TEST_TIMEOUTS.DEFAULT): void {
  // Set Jest timeout using centralized configuration
  setTestTimeout(customTimeout);
  
  // Store original timer functions only if not already stored
  if (!originalSetTimeout || global.setTimeout === originalSetTimeout) {
    originalSetTimeout = global.setTimeout;
  }
  if (!originalSetInterval || global.setInterval === originalSetInterval) {
    originalSetInterval = global.setInterval;
  }
  if (!originalClearTimeout || global.clearTimeout === originalClearTimeout) {
    originalClearTimeout = global.clearTimeout;
  }
  if (!originalClearInterval || global.clearInterval === originalClearInterval) {
    originalClearInterval = global.clearInterval;
  }
  
  // Override setTimeout to track timers
  global.setTimeout = ((callback: TimerHandler, delay?: number, ...args: any[]) => {
    // Limit delay to prevent hanging
    const safeDelay = Math.min(delay || 0, MAX_TIMEOUT_MS);
    const id = originalSetTimeout(callback, safeDelay, ...args);
    activeTimers.add(id);
    return id;
  }) as typeof setTimeout;
  
  // Override setInterval to track intervals
  global.setInterval = ((callback: TimerHandler, delay?: number, ...args: any[]) => {
    // Limit delay and add safety checks
    const safeDelay = Math.max(Math.min(delay || 100, MAX_TIMEOUT_MS), 50); // Min 50ms
    const id = originalSetInterval(() => {
      try {
        callback();
      } catch (error) {
        console.warn('Interval callback error:', error);
        // Clear problematic interval
        clearInterval(id);
      }
    }, safeDelay, ...args);
    activeIntervals.add(id);
    return id;
  }) as typeof setInterval;
  
  // Override clearTimeout to track cleanup
  global.clearTimeout = ((id: NodeJS.Timeout) => {
    activeTimers.delete(id);
    return originalClearTimeout(id);
  }) as typeof clearTimeout;
  
  // Override clearInterval to track cleanup
  global.clearInterval = ((id: NodeJS.Timeout) => {
    activeIntervals.delete(id);
    return originalClearInterval(id);
  }) as typeof clearInterval;
}

/**
 * Cleanup anti-hanging utilities
 * Call this in afterEach
 */
export function cleanupAntiHang(): void {
  // Clear all tracked timers
  for (const id of activeTimers) {
    originalClearTimeout(id);
  }
  activeTimers.clear();
  
  // Clear all tracked intervals
  for (const id of activeIntervals) {
    originalClearInterval(id);
  }
  activeIntervals.clear();
  
  // Use Jest fake timers to clear any remaining timers
  jest.useFakeTimers();
  jest.clearAllTimers();
  jest.runOnlyPendingTimers();
  jest.useRealTimers();
  
  // Restore original timer functions if they were overridden
  if (originalSetTimeout) {
    global.setTimeout = originalSetTimeout;
  }
  if (originalSetInterval) {
    global.setInterval = originalSetInterval;
  }
  if (originalClearTimeout) {
    global.clearTimeout = originalClearTimeout;
  }
  if (originalClearInterval) {
    global.clearInterval = originalClearInterval;
  }
}

/**
 * Restore anti-hanging utilities
 * Call this in afterAll if needed
 */
export function restoreAntiHang(): void {
  cleanupAntiHang();
}

/**
 * Safe waitFor with automatic timeout limiting
 */
export function safeWaitFor(
  callback: () => void | Promise<void>,
  options: { timeout?: number; interval?: number } = {}
): Promise<void> {
  const { timeout = 3000, interval = 50 } = options;
  const safeTimeout = Math.min(timeout, MAX_TIMEOUT_MS);
  
  return new Promise((resolve, reject) => {
    const startTime = Date.now();
    const timeoutId = setTimeout(() => {
      reject(new Error(`safeWaitFor timed out after ${safeTimeout}ms`));
    }, safeTimeout);
    
    const checkCondition = async () => {
      try {
        await callback();
        clearTimeout(timeoutId);
        resolve();
      } catch (error) {
        if (Date.now() - startTime >= safeTimeout) {
          clearTimeout(timeoutId);
          reject(error);
        } else {
          setTimeout(checkCondition, interval);
        }
      }
    };
    
    checkCondition();
  });
}

/**
 * Safe promise that automatically rejects after timeout
 */
export function safePromise<T>(
  promise: Promise<T>,
  timeoutMs: number = 3000
): Promise<T> {
  const safeTimeout = Math.min(timeoutMs, MAX_TIMEOUT_MS);
  
  return new Promise((resolve, reject) => {
    const timeoutId = setTimeout(() => {
      reject(new Error(`Promise timed out after ${safeTimeout}ms`));
    }, safeTimeout);
    
    promise
      .then((result) => {
        clearTimeout(timeoutId);
        resolve(result);
      })
      .catch((error) => {
        clearTimeout(timeoutId);
        reject(error);
      });
  });
}

/**
 * Safe delay with maximum timeout
 */
export function safeDelay(ms: number): Promise<void> {
  const safeMs = Math.min(ms, MAX_TIMEOUT_MS);
  return new Promise(resolve => setTimeout(resolve, safeMs));
}

/**
 * Create a mock WebSocket that won't cause hanging
 */
export function createSafeMockWebSocket(url?: string): MockWebSocket {
  return new MockWebSocket(url);
}

class MockWebSocket {
  public readonly CONNECTING = 0;
  public readonly OPEN = 1;
  public readonly CLOSING = 2;
  public readonly CLOSED = 3;

  public readyState = this.CONNECTING;
  public url: string;
  public protocol = '';
  public extensions = '';
  public binaryType: 'blob' | 'arraybuffer' = 'blob';
  public bufferedAmount = 0;

  public onopen: ((event: Event) => void) | null = null;
  public onclose: ((event: CloseEvent) => void) | null = null;
  public onerror: ((event: Event) => void) | null = null;
  public onmessage: ((event: MessageEvent) => void) | null = null;

  private eventListeners = new Map<string, Set<EventListener>>();

  constructor(url: string = 'ws://localhost:3001/test') {
    this.url = url;
    
    // Simulate connection opening after a short delay
    setTimeout(() => {
      this.readyState = this.OPEN;
      const openEvent = new Event('open');
      this.onopen?.(openEvent);
      this.dispatchEvent(openEvent);
    }, 10);
  }

  send(data: string | ArrayBuffer | Blob | ArrayBufferView): void {
    if (this.readyState !== this.OPEN) {
      throw new Error('WebSocket is not open');
    }
    // Mock implementation - just log or store the data
  }

  close(code?: number, reason?: string): void {
    if (this.readyState === this.CLOSED || this.readyState === this.CLOSING) {
      return;
    }
    
    this.readyState = this.CLOSING;
    
    setTimeout(() => {
      this.readyState = this.CLOSED;
      const closeEvent = new CloseEvent('close', { code: code || 1000, reason });
      this.onclose?.(closeEvent);
      this.dispatchEvent(closeEvent);
    }, 10);
  }

  addEventListener(type: string, listener: EventListener): void {
    if (!this.eventListeners.has(type)) {
      this.eventListeners.set(type, new Set());
    }
    this.eventListeners.get(type)!.add(listener);
  }

  removeEventListener(type: string, listener: EventListener): void {
    this.eventListeners.get(type)?.delete(listener);
  }

  dispatchEvent(event: Event): boolean {
    const listeners = this.eventListeners.get(event.type);
    if (listeners) {
      listeners.forEach(listener => {
        try {
          listener(event);
        } catch (error) {
          console.warn('Event listener error:', error);
        }
      });
    }
    return true;
  }

  // Helper methods for testing
  simulateMessage(data: any): void {
    if (this.readyState === this.OPEN) {
      const messageData = typeof data === 'string' ? data : JSON.stringify(data);
      const event = new MessageEvent('message', { data: messageData });
      this.onmessage?.(event);
      this.dispatchEvent(event);
    }
  }

  simulateError(): void {
    const errorEvent = new Event('error');
    this.onerror?.(errorEvent);
    this.dispatchEvent(errorEvent);
  }
}

/**
 * Get statistics about active timers
 */
export function getTimerStats(): { timers: number; intervals: number } {
  return {
    timers: activeTimers.size,
    intervals: activeIntervals.size
  };
}

/**
 * Force cleanup of all resources (emergency cleanup)
 */
export function forceCleanupAll(): void {
  cleanupAntiHang();
  
  // Additional cleanup for stubborn resources
  if (typeof window !== 'undefined') {
    // Clear any window-level resources
    const highestTimeoutId = setTimeout(() => {}, 0);
    for (let i = 0; i <= highestTimeoutId; i++) {
      clearTimeout(i);
    }
  }
  
  // Force garbage collection if available
  if ((global as any).gc) {
    (global as any).gc();
  }
}

export default {
  setupAntiHang,
  cleanupAntiHang,
  restoreAntiHang,
  safeWaitFor,
  safePromise,
  safeDelay,
  createSafeMockWebSocket,
  getTimerStats,
  forceCleanupAll,
};