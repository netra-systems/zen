/**
 * Test Cleanup Utilities
 */

export function cleanupAfterTest(): void {
  jest.clearAllMocks();
  jest.clearAllTimers();
}

export function resetTestEnvironment(): void {
  localStorage.clear();
  sessionStorage.clear();
  document.body.innerHTML = '';
}