/**
 * Test Setup Utilities
 * Common setup functions for integration tests
 */

import WS from 'jest-websocket-mock';
import { useAuthStore } from '@/store/authStore';
import { useChatStore } from '@/store/chatStore';
import { useThreadStore } from '@/store/threadStore';

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
  useAuthStore.setState({ user: null, token: null, isAuthenticated: false });
  useChatStore.setState({ messages: [], currentThread: null });
  useThreadStore.setState({ threads: [], currentThread: null, currentThreadId: null });
};

export const setupGlobalFetch = (): void => {
  global.fetch = jest.fn();
};

export const cleanupWebSocket = (): void => {
  WS.clean();
  jest.restoreAllMocks();
};