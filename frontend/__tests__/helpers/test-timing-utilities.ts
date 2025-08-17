/**
 * Test Timing Utilities - Handles DOM timing issues and act() wrapping
 * Fixes common timing patterns affecting multiple tests
 * All functions ≤8 lines for maintainability
 */

import { act, waitFor } from '@testing-library/react';

// Safe act wrapper for async operations
export const safeAct = async (action: () => Promise<void> | void): Promise<void> => {
  await act(async () => {
    await action();
  });
};

// Wait for condition with proper error handling
export const waitForCondition = async (condition: () => boolean, timeout = 5000) => {
  return waitFor(() => {
    if (!condition()) throw new Error('Condition not met');
    return true;
  }, { timeout });
};

// Flush all pending promises and timers
export const flushPromises = async (): Promise<void> => {
  await act(async () => {
    await new Promise(resolve => setTimeout(resolve, 0));
  });
};

// Wait for next tick with act wrapping
export const waitForNextTick = async (): Promise<void> => {
  await act(async () => {
    await new Promise(resolve => process.nextTick(resolve));
  });
};

// Safe timer advance for testing
export const advanceTimersSafely = (ms: number): void => {
  act(() => {
    jest.advanceTimersByTime(ms);
  });
};

// Wait for loading states to resolve
export const waitForLoadingToComplete = async (timeout = 3000): Promise<void> => {
  await waitFor(() => {
    const loadingElements = document.querySelectorAll('[data-testid*="loading"]');
    if (loadingElements.length > 0) throw new Error('Still loading');
  }, { timeout });
};