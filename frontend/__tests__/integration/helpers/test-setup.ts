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
  // Import stores dynamically to avoid circular dependency issues
  try {
    const { useChatStore } = require('@/store/chatStore');
    const { useThreadStore } = require('@/store/threadStore');
    
    // Reset both stores to their initial state
    useChatStore.getState().reset();
    useThreadStore.getState().reset();
  } catch (error) {
    console.warn('Could not reset stores:', error);
  }
};

export const setupGlobalFetch = (): void => {
  global.fetch = jest.fn();
};

export const cleanupWebSocket = (): void => {
  safeWebSocketCleanup();
  jest.restoreAllMocks();
};