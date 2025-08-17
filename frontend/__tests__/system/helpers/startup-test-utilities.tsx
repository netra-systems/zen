/**
 * Shared Test Utilities for Frontend System Startup Tests
 * Provides common mocks, setup functions, and test helpers
 */

import React from 'react';
import { render } from '@testing-library/react';
import { TestProviders } from '../../test-utils/providers';

// Mock Environment Variables
export const mockEnv = {
  NEXT_PUBLIC_API_URL: 'http://localhost:8000',
  NEXT_PUBLIC_WS_URL: 'ws://localhost:8000',
};

// Setup Environment for Tests
export const setupTestEnvironment = () => {
  process.env = { ...process.env, ...mockEnv };
  jest.clearAllMocks();
  global.fetch = jest.fn();
};

// Cleanup Test Environment
export const cleanupTestEnvironment = () => {
  jest.restoreAllMocks();
};

// Mock Fetch Response Helper
export const createMockResponse = (data: any, ok = true) => ({
  ok,
  json: async () => data,
  headers: new Headers(),
});

// Mock Health Response
export const createHealthResponse = () => ({
  status: 'OK',
  timestamp: new Date().toISOString(),
  version: '1.0.0',
});

// Setup Fetch Mock with Retry Logic
export const setupFetchWithRetry = (failCount = 2) => {
  let attempts = 0;
  (fetch as jest.Mock).mockImplementation(async () => {
    attempts++;
    if (attempts <= failCount) {
      throw new Error('Connection failed');
    }
    return createMockResponse({ status: 'OK' });
  });
  return { getAttemptCount: () => attempts };
};

// Create CORS Headers
export const createCORSHeaders = () => new Headers({
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
});

// Mock WebSocket Setup
export const createMockWebSocket = () => ({
  readyState: WebSocket.CONNECTING,
  close: jest.fn(),
  send: jest.fn(),
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
});

// Setup WebSocket Mocks
export const setupWebSocketMocks = () => {
  const mockWebSocket = createMockWebSocket();
  const mockConstructor = jest.fn(() => mockWebSocket);
  (global as any).WebSocket = mockConstructor;
  return { mockWebSocket, mockConstructor };
};

// Setup Fetch for WebSocket Config
export const setupWebSocketFetch = () => {
  (fetch as jest.Mock).mockResolvedValue(
    createMockResponse({ ws_url: 'ws://localhost:8000' })
  );
};

// Create Test Components
export const createTestComponents = () => {
  const MockedProviders = ({ children }: { children: any }) => (
    <TestProviders>{children}</TestProviders>
  );
  return { MockedProviders };
};

// Find Event Handler in WebSocket Mock
export const findEventHandler = (wsInstance: any, eventType: string) => {
  return wsInstance.addEventListener.mock.calls.find(
    (call: any[]) => call[0] === eventType
  )?.[1];
};

// Setup Timer Mocks
export const setupTimerMocks = () => {
  jest.useFakeTimers();
  return { cleanup: () => jest.useRealTimers() };
};

// Mock User Data
export const createMockUser = () => ({
  id: 'test',
  email: 'test@example.com',
});

// Setup LocalStorage Mocks
export const setupLocalStorageMocks = () => {
  const mockUser = createMockUser();
  localStorage.setItem('jwt_token', 'test-token');
  localStorage.setItem('user', JSON.stringify(mockUser));
  return { mockUser };
};

// Clear Storage
export const clearStorage = () => {
  localStorage.clear();
  sessionStorage.clear();
};

// Mock Service Worker
export const createMockServiceWorker = () => ({
  update: jest.fn(),
});

// Setup Service Worker Mocks
export const setupServiceWorkerMocks = () => {
  const mockRegistration = createMockServiceWorker();
  navigator.serviceWorker = {
    register: jest.fn().mockResolvedValue(mockRegistration),
    ready: Promise.resolve(mockRegistration as any),
  } as any;
  return { mockRegistration };
};

// Mock matchMedia for Theme Tests
export const setupThemeMocks = () => {
  window.matchMedia = jest.fn().mockImplementation(query => ({
    matches: query === '(prefers-color-scheme: dark)',
    media: query,
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
  })) as any;
};

// Performance Measurement Helper
export const measurePerformance = async (operation: () => Promise<void>) => {
  const startTime = performance.now();
  await operation();
  const endTime = performance.now();
  return endTime - startTime;
};

// Mock Console Methods
export const mockConsole = () => {
  const originalError = console.error;
  const originalLog = console.log;
  console.error = jest.fn();
  console.log = jest.fn();
  
  return {
    restore: () => {
      console.error = originalError;
      console.log = originalLog;
    }
  };
};

// Default Settings for First-Time Run
export const createDefaultSettings = () => ({
  theme: 'light',
  notifications: true,
  autoSave: true,
});

// Load Optional Dependency Helper
export const loadOptionalDependency = (name: string) => {
  try {
    return require(name);
  } catch {
    return null;
  }
};

// App Configuration Helper
export const createAppConfig = () => ({
  apiUrl: process.env.NEXT_PUBLIC_API_URL,
  wsUrl: process.env.NEXT_PUBLIC_WS_URL,
  environment: process.env.NODE_ENV,
  version: '1.0.0',
});