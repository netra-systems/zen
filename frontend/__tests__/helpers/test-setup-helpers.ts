/**
 * Test Setup Helpers - Reusable setup/teardown logic
 * Keeps test functions ≤8 lines by extracting common patterns
 */

import WS from 'jest-websocket-mock';
import { useAuthStore } from '@/store/authStore';
import { useChatStore } from '@/store/chatStore';
import { useThreadStore } from '@/store/threadStore';
import { createWebSocketManager } from './websocket-test-manager';

export const setupTestEnvironment = () => {
  process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000';
  process.env.NEXT_PUBLIC_WS_URL = 'ws://localhost:8000';
  jest.clearAllMocks();
};

export const cleanupTestEnvironment = () => {
  try {
    WS.clean();
  } catch (error) {
    // Ignore cleanup errors for non-existent servers
  }
  jest.restoreAllMocks();
};

export const clearTestStorage = () => {
  localStorage.clear();
  sessionStorage.clear();
};

export const resetTestStores = () => {
  // Use proper reset methods instead of setState for zustand stores
  if (typeof useAuthStore.getState === 'function') {
    useAuthStore.getState().reset();
  }
  if (typeof useChatStore.getState === 'function') {
    useChatStore.getState().reset();
  }
  if (typeof useThreadStore.getState === 'function') {
    useThreadStore.getState().reset();
  }
};

export const setupMockServer = () => {
  const wsManager = createWebSocketManager();
  return wsManager.setup();
};

export const createWebSocketTestManager = () => {
  return createWebSocketManager();
};

export const setupMockFetch = () => {
  global.fetch = jest.fn((url) => {
    if (url.includes('/api/config')) {
      return createMockResponse({ ws_url: 'ws://localhost:8000/ws' });
    }
    return createMockResponse({});
  }) as jest.Mock;
};

export const createMockResponse = (data: any) => {
  return Promise.resolve({
    json: () => Promise.resolve(data),
    ok: true
  });
};

export const createTestUser = () => ({
  id: '123',
  email: 'test@example.com',
  full_name: 'Test User',
  name: 'Test User'
});

export const createMockToken = () => 'test-jwt-token';

export const setAuthenticatedState = () => {
  const user = createTestUser();
  const token = createMockToken();
  // Use proper login method instead of setState
  if (typeof useAuthStore.getState === 'function') {
    useAuthStore.getState().login(user, token);
  }
  return { user, token };
};
export const setupMockFetchForConfig = () => {
  global.fetch = jest.fn((url) => {
    if (url.includes('/api/config')) {
      return createMockResponse({ ws_url: 'ws://localhost:8000/ws' });
    }
    return createMockResponse({});
  }) as jest.Mock;
};

export const setupPersistedAuthState = (user: any, token: string) => {
  useAuthStore.getState().login(user, token);
  localStorage.setItem('auth_token', token);
  localStorage.setItem('user', JSON.stringify(user));
};
