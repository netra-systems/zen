/**
 * State Timing Utilities
 */

export async function waitForStateUpdate(ms: number = 10): Promise<void> {
  await new Promise(resolve => setTimeout(resolve, ms));
}

export async function flushMicrotasks(): Promise<void> {
  await new Promise(resolve => setTimeout(resolve, 0));
}