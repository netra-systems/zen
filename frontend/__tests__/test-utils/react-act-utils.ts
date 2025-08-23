/**
 * React Act Testing Utilities
 * 
 * Comprehensive helpers for wrapping all state updates in act() to prevent warnings.
 * Use these utilities whenever you need to perform actions that trigger React state changes.
 */

import { act } from '@testing-library/react';

/**
 * Wrap a Promise or timeout in act() for async operations
 */
export async function actWait(ms: number = 0): Promise<void> {
  await act(async () => {
    await new Promise(resolve => setTimeout(resolve, ms));
  });
}

/**
 * Wrap an async function call in act()
 */
export async function actAsync<T>(fn: () => Promise<T>): Promise<T> {
  let result: T;
  await act(async () => {
    result = await fn();
  });
  return result!;
}

/**
 * Wrap a synchronous function call in act()
 */
export function actSync<T>(fn: () => T): T {
  let result: T;
  act(() => {
    result = fn();
  });
  return result!;
}

/**
 * Create a callback wrapper that automatically wraps state updates in act()
 * Perfect for event handlers, WebSocket callbacks, and other async callbacks
 */
export function createActCallback<T extends (...args: any[]) => void>(callback: T): T {
  return ((...args: any[]) => {
    act(() => {
      callback(...args);
    });
  }) as T;
}

/**
 * Create an async callback wrapper that automatically wraps state updates in act()
 */
export function createActAsyncCallback<T extends (...args: any[]) => Promise<void>>(callback: T): T {
  return (async (...args: any[]) => {
    await act(async () => {
      await callback(...args);
    });
  }) as T;
}

/**
 * Wrap timer-based operations in act()
 */
export async function actTimer(fn: () => void, delay: number = 0): Promise<void> {
  await act(async () => {
    return new Promise<void>(resolve => {
      setTimeout(() => {
        fn();
        resolve();
      }, delay);
    });
  });
}

/**
 * Wrap state setter functions to always use act()
 */
export function wrapStateSetterWithAct<T>(setter: (value: T | ((prev: T) => T)) => void) {
  return (value: T | ((prev: T) => T)) => {
    act(() => {
      setter(value);
    });
  };
}

export { act };