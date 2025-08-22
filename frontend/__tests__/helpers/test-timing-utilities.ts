/**
 * Test Timing Utilities
 * Utilities for handling timing, async operations, and test synchronization
 */

import { act } from '@testing-library/react';

export async function safeAct(fn: () => void | Promise<void>): Promise<void> {
  await act(async () => {
    await fn();
  });
}

export async function waitForCondition(
  condition: () => boolean | Promise<boolean>,
  timeout = 5000,
  interval = 100
): Promise<void> {
  const start = Date.now();
  
  while (Date.now() - start < timeout) {
    const result = await condition();
    if (result) {
      return;
    }
    await new Promise(resolve => setTimeout(resolve, interval));
  }
  
  throw new Error(`Condition not met within ${timeout}ms`);
}

export function flushPromises(): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, 0));
}

export async function waitForNextTick(): Promise<void> {
  return new Promise(resolve => process.nextTick(resolve));
}

export function createTimeout(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

export function mockTimers(): void {
  jest.useFakeTimers();
}

export function restoreTimers(): void {
  jest.useRealTimers();
}

export function advanceTimersByTime(ms: number): void {
  jest.advanceTimersByTime(ms);
}

export function runAllTimers(): void {
  jest.runAllTimers();
}