/**
 * React Act Testing Utilities
 */

import { act } from '@testing-library/react';

export async function actWait(ms: number = 0): Promise<void> {
  await act(async () => {
    await new Promise(resolve => setTimeout(resolve, ms));
  });
}

export async function actAsync<T>(fn: () => Promise<T>): Promise<T> {
  let result: T;
  await act(async () => {
    result = await fn();
  });
  return result!;
}

export { act };