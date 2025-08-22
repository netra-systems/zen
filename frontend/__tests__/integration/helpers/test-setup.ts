/**
 * Test Setup Utilities
 * Common setup functions for integration tests
 */

import WS from 'jest-websocket-mock';
import { safeWebSocketCleanup } from '../../helpers/websocket-test-manager';

export const setupTestEnvironment = (): WS => {
  process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000';
  process.env.NEXT_PUBLIC_WS_URL = 'ws://localhost:8000';
  const server = new WS('ws://localhost:8000/ws');
  jest.clearAllMocks();
  return server;
};

export const clearStorages = (): void => {
  localStorage.clear();
  sessionStorage.clear();
};

export const resetStores = (): void => {
  // Store resetting is handled by individual test mocks
  // This function exists for compatibility but does nothing
  console.debug('resetStores called - handled by test mocks');
};

export const setupGlobalFetch = (): void => {
  global.fetch = jest.fn();
};

export const cleanupWebSocket = (): void => {
  safeWebSocketCleanup();
  jest.restoreAllMocks();
};