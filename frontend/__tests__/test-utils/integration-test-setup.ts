/**
 * Integration Test Setup and Shared Utilities
 * 
 * Provides common setup, mocks, and helper functions
 * for all frontend integration tests.
 */

import WS from 'jest-websocket-mock';
import { safeWebSocketCleanup } from '../helpers/websocket-test-manager';

// Mock Next.js router
export const mockNextRouter = () => {
  jest.mock('next/navigation', () => ({
    useRouter: () => ({
      push: jest.fn(),
      replace: jest.fn(),
      refresh: jest.fn(),
      back: jest.fn(),
      forward: jest.fn(),
      pathname: '/',
      query: {},
      asPath: '/',
    }),
    usePathname: () => '/',
    useSearchParams: () => new URLSearchParams(),
  }));
};

// Environment configuration
export const setupTestEnvironment = () => {
  process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000';
  process.env.NEXT_PUBLIC_WS_URL = 'ws://localhost:8000';
};

// WebSocket server setup
export const createWebSocketServer = (): WS => {
  return new WS('ws://localhost:8000/ws');
};

// Reset test state
export const resetTestState = () => {
  jest.clearAllMocks();
  localStorage.clear();
  sessionStorage.clear();
  
  // Store reset is handled by individual test mocks
  // to avoid import issues with mock declarations
};

// Common test data
export const mockUser = {
  id: 'test-user-id',
  email: 'test@example.com',
  name: 'Test User',
};

export const mockAuthToken = 'test-auth-token';

export const mockMessage = {
  id: 'msg-1',
  content: 'Test message',
  timestamp: new Date().toISOString(),
  author: 'user',
  threadId: 'thread-1',
};

export const mockThread = {
  id: 'thread-1',
  title: 'Test Thread',
  createdAt: new Date().toISOString(),
  messages: [],
};

// Common test assertions
export const expectAuthenticatedState = () => {
  // Use mock expectations when store is mocked
  if (typeof useAuthStore.getState === 'function') {
    const authState = useAuthStore.getState();
    expect(authState.isAuthenticated).toBe(true);
    expect(authState.user).toEqual(mockUser);
    expect(authState.token).toBe(mockAuthToken);
  } else {
    // For mocked environments, just verify mock was called correctly
    expect(useAuthStore).toHaveBeenCalledWith(expect.objectContaining({
      isAuthenticated: true
    }));
  }
};

export const expectUnauthenticatedState = () => {
  // Use mock expectations when store is mocked
  if (typeof useAuthStore.getState === 'function') {
    const authState = useAuthStore.getState();
    expect(authState.isAuthenticated).toBe(false);
    expect(authState.user).toBe(null);
    expect(authState.token).toBe(null);
  } else {
    // For mocked environments, just verify mock was called correctly
    expect(useAuthStore).toHaveBeenCalledWith(expect.objectContaining({
      isAuthenticated: false
    }));
  }
};

// WebSocket message helpers
export const sendWebSocketMessage = (server: WS, message: any) => {
  server.send(JSON.stringify(message));
};

export const expectWebSocketConnection = async (server: WS) => {
  await expect(server).toReceiveMessage();
  expect(server).toHaveReceivedMessages([]);
};

// Cleanup utilities
export const cleanupWebSocketServer = (server: WS) => {
  safeWebSocketCleanup();
  server.close();
};

export const performFullCleanup = (server: WS) => {
  cleanupWebSocketServer(server);
  resetTestState();
};