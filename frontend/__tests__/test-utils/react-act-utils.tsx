/**
 * React Act() Utilities for WebSocket and Async Testing
 * CRITICAL: Fixes React act() warnings and timing synchronization issues
 * Ensures all state updates are properly wrapped in act()
 * ≤300 lines, ≤8 lines per function
 */

import { act, waitFor } from '@testing-library/react';
import { flushSync } from 'react-dom';

export interface ActWrapperOptions {
  timeout?: number;
  interval?: number;
  skipErrors?: boolean;
  flushSync?: boolean;
}

/**
 * Wraps async operations in act() to prevent React warnings
 */
export async function actAsync<T>(operation: () => Promise<T>): Promise<T> {
  let result: T;
  await act(async () => {
    result = await operation();
  });
  return result!;
}

/**
 * Wraps synchronous operations in act()
 */
export function actSync<T>(operation: () => T): T {
  let result: T;
  act(() => {
    result = operation();
  });
  return result!;
}

/**
 * Waits for condition with proper act() wrapping
 */
export async function actWaitFor<T>(
  callback: () => T,
  options: ActWrapperOptions = {}
): Promise<T> {
  const { timeout = 5000, interval = 50 } = options;
  
  return act(async () => {
    return waitFor(callback, { timeout, interval });
  });
}

/**
 * Delays execution with act() wrapping
 */
export async function actDelay(ms: number): Promise<void> {
  await act(async () => {
    await new Promise(resolve => setTimeout(resolve, ms));
  });
}

/**
 * Flushes pending React updates with act()
 */
export function actFlush(): void {
  act(() => {
    flushSync(() => {});
  });
}

/**
 * Wraps WebSocket operations in act()
 */
export async function actWebSocket<T>(operation: () => Promise<T>): Promise<T> {
  return actAsync(operation);
}

/**
 * WebSocket connection with proper act() handling
 */
export async function actWebSocketConnect(
  connectFn: () => Promise<void>
): Promise<void> {
  await act(async () => {
    await connectFn();
  });
}

/**
 * WebSocket message sending with act() wrapping
 */
export async function actWebSocketSend<T>(
  sendFn: () => T
): Promise<T> {
  return act(() => {
    return sendFn();
  });
}

/**
 * WebSocket disconnection with proper cleanup
 */
export async function actWebSocketDisconnect(
  disconnectFn: () => void
): Promise<void> {
  await act(async () => {
    disconnectFn();
    await actDelay(10); // Allow cleanup to complete
  });
}

/**
 * State update with act() wrapping
 */
export function actStateUpdate<T>(updateFn: () => T): T {
  return actSync(updateFn);
}

/**
 * Hook update with act() wrapping
 */
export async function actHookUpdate<T>(
  updateFn: () => Promise<T>
): Promise<T> {
  return actAsync(updateFn);
}

/**
 * Component interaction with act()
 */
export async function actUserInteraction<T>(
  interactionFn: () => Promise<T>
): Promise<T> {
  return actAsync(interactionFn);
}

/**
 * Batches multiple operations in single act()
 */
export async function actBatch<T>(
  operations: (() => Promise<any>)[]
): Promise<T[]> {
  return act(async () => {
    return Promise.all(operations.map(op => op()));
  });
}

/**
 * Retries operation with act() wrapping
 */
export async function actRetry<T>(
  operation: () => Promise<T>,
  maxAttempts: number = 3,
  delayMs: number = 100
): Promise<T> {
  let lastError: Error;
  
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await actAsync(operation);
    } catch (error) {
      lastError = error as Error;
      if (attempt < maxAttempts) {
        await actDelay(delayMs * attempt);
      }
    }
  }
  
  throw lastError!;
}

/**
 * Handles cleanup operations with act()
 */
export async function actCleanup(cleanupFn: () => void | Promise<void>): Promise<void> {
  await act(async () => {
    const result = cleanupFn();
    if (result instanceof Promise) {
      await result;
    }
  });
}

/**
 * Timer operations with act() wrapping
 */
export class ActTimer {
  private timeouts: NodeJS.Timeout[] = [];
  private intervals: NodeJS.Timeout[] = [];

  setTimeout(callback: () => void, delay: number): void {
    const timeout = setTimeout(() => {
      act(() => {
        callback();
      });
    }, delay);
    this.timeouts.push(timeout);
  }

  setInterval(callback: () => void, interval: number): void {
    const intervalId = setInterval(() => {
      act(() => {
        callback();
      });
    }, interval);
    this.intervals.push(intervalId);
  }

  clearAll(): void {
    act(() => {
      this.timeouts.forEach(clearTimeout);
      this.intervals.forEach(clearInterval);
      this.timeouts = [];
      this.intervals = [];
    });
  }

  async flush(): Promise<void> {
    await actDelay(0); // Flush microtasks
  }
}

/**
 * Creates act-wrapped timer
 */
export function createActTimer(): ActTimer {
  return new ActTimer();
}

/**
 * Microtask flush with act()
 */
export async function actMicrotask(): Promise<void> {
  await act(async () => {
    await new Promise(resolve => queueMicrotask(resolve));
  });
}

/**
 * Animation frame with act()
 */
export async function actAnimationFrame(): Promise<void> {
  await act(async () => {
    await new Promise(resolve => requestAnimationFrame(() => resolve(undefined)));
  });
}

/**
 * Network request simulation with act()
 */
export async function actNetworkRequest<T>(
  requestFn: () => Promise<T>,
  delayMs: number = 100
): Promise<T> {
  return actAsync(async () => {
    await new Promise(resolve => setTimeout(resolve, delayMs));
    return requestFn();
  });
}

/**
 * Error handling with act()
 */
export async function actErrorHandler<T>(
  operation: () => Promise<T>,
  errorHandler: (error: Error) => void
): Promise<T | null> {
  try {
    return await actAsync(operation);
  } catch (error) {
    act(() => {
      errorHandler(error as Error);
    });
    return null;
  }
}

/**
 * Component mount with act()
 */
export async function actMount<T>(mountFn: () => T): Promise<T> {
  return act(() => {
    return mountFn();
  });
}

/**
 * Component unmount with act()
 */
export async function actUnmount(unmountFn: () => void): Promise<void> {
  await act(async () => {
    unmountFn();
    await actDelay(10); // Allow cleanup
  });
}

/**
 * React Suspense with act()
 */
export async function actSuspense<T>(
  suspenseFn: () => Promise<T>
): Promise<T> {
  return actAsync(suspenseFn);
}

/**
 * Context updates with act()
 */
export function actContextUpdate<T>(
  updateFn: () => T
): T {
  return actSync(updateFn);
}

/**
 * Ref updates with act()
 */
export function actRefUpdate<T>(
  refUpdateFn: () => T
): T {
  return actSync(refUpdateFn);
}

/**
 * Effect cleanup with act()
 */
export async function actEffectCleanup(
  cleanupFn: () => void | Promise<void>
): Promise<void> {
  await actCleanup(cleanupFn);
}

/**
 * Global act utilities export
 */
export const ActUtils = {
  async: actAsync,
  sync: actSync,
  waitFor: actWaitFor,
  delay: actDelay,
  flush: actFlush,
  webSocket: actWebSocket,
  webSocketConnect: actWebSocketConnect,
  webSocketSend: actWebSocketSend,
  webSocketDisconnect: actWebSocketDisconnect,
  stateUpdate: actStateUpdate,
  hookUpdate: actHookUpdate,
  userInteraction: actUserInteraction,
  batch: actBatch,
  retry: actRetry,
  cleanup: actCleanup,
  microtask: actMicrotask,
  animationFrame: actAnimationFrame,
  networkRequest: actNetworkRequest,
  errorHandler: actErrorHandler,
  mount: actMount,
  unmount: actUnmount,
  suspense: actSuspense,
  contextUpdate: actContextUpdate,
  refUpdate: actRefUpdate,
  effectCleanup: actEffectCleanup
};