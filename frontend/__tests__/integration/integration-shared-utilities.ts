/**
 * Shared Integration Test Utilities
 * Common utilities for integration tests
 */

import React from 'react';
import WS from 'jest-websocket-mock';
import { jest } from '@jest/globals';
import { safeWebSocketCleanup } from '../helpers/websocket-test-manager';

// Test environment setup
export const setupIntegrationTest = (): WS => {
  process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000';
  process.env.NEXT_PUBLIC_WS_URL = 'ws://localhost:8000';
  const server = new WS('ws://localhost:8000/ws');
  jest.clearAllMocks();
  localStorage.clear();
  sessionStorage.clear();
  return server;
};

export const teardownIntegrationTest = (): void => {
  safeWebSocketCleanup();
  jest.restoreAllMocks();
};

// Store creators
export const createLLMCacheStore = () => {
  return jest.fn(() => ({
    cache: new Map(),
    setCache: jest.fn(),
    getCache: jest.fn(),
    clearCache: jest.fn(),
    reset: jest.fn()
  }));
};

export const createLLMCacheService = () => ({
  queryCache: jest.fn(),
  warmCache: jest.fn(),
  evictCache: jest.fn(),
  getCacheStats: jest.fn()
});

export const createTaskStore = () => {
  return jest.fn(() => ({
    tasks: [],
    addTask: jest.fn(),
    updateTask: jest.fn(),
    removeTask: jest.fn(),
    reset: jest.fn()
  }));
};

export const createTaskService = () => ({
  queueTask: jest.fn(),
  retryTask: jest.fn(),
  cancelTask: jest.fn(),
  getTaskStatus: jest.fn()
});

export const createHealthStore = () => {
  return jest.fn(() => ({
    status: 'healthy',
    services: {},
    setStatus: jest.fn(),
    updateService: jest.fn(),
    reset: jest.fn()
  }));
};

export const createHealthService = () => ({
  checkHealth: jest.fn(),
  monitorServices: jest.fn(),
  getServiceStatus: jest.fn()
});

export const createCorpusStore = () => {
  return jest.fn(() => ({
    documents: [],
    addDocument: jest.fn(),
    removeDocument: jest.fn(),
    searchDocuments: jest.fn(),
    reset: jest.fn()
  }));
};

export const createCorpusService = () => ({
  uploadDocument: jest.fn(),
  searchCorpus: jest.fn(),
  deleteDocument: jest.fn(),
  exportCorpus: jest.fn()
});

export const createSyntheticDataStore = () => {
  return jest.fn(() => ({
    data: [],
    generateData: jest.fn(),
    clearData: jest.fn(),
    reset: jest.fn()
  }));
};

export const createSyntheticDataService = () => ({
  generateSyntheticData: jest.fn(),
  exportData: jest.fn(),
  validateData: jest.fn()
});

// Component creators
export const createCacheManagementComponent = () => {
  return function CacheManagement() {
    return React.createElement('div', { 'data-testid': 'cache-management' }, 'Cache Management');
  };
};

export const createTaskRetryComponent = () => {
  return function TaskRetry() {
    return React.createElement('div', { 'data-testid': 'task-retry' }, 'Task Retry');
  };
};

export const createHealthMonitorComponent = () => {
  return function HealthMonitor() {
    return React.createElement('div', { 'data-testid': 'health-monitor' }, 'Health Monitor');
  };
};

export const createTestComponent = (children: React.ReactNode) => {
  return React.createElement('div', { 'data-testid': 'test-wrapper' }, children);
};

// Mock creators
export const createMockUseUnifiedChatStore = () => {
  return jest.fn(() => ({
    messages: [],
    addMessage: jest.fn(),
    clearMessages: jest.fn(),
    isLoading: false,
    setLoading: jest.fn()
  }));
};

export const createMockUseWebSocket = () => {
  return jest.fn(() => ({
    socket: null,
    connected: false,
    connect: jest.fn(),
    disconnect: jest.fn(),
    send: jest.fn()
  }));
};

export const createMockUseAgent = () => {
  return jest.fn(() => ({
    agent: null,
    isProcessing: false,
    processMessage: jest.fn(),
    reset: jest.fn()
  }));
};

export const createMockUseAuthStore = () => {
  return jest.fn(() => ({
    user: null,
    token: null,
    isAuthenticated: false,
    login: jest.fn(),
    logout: jest.fn()
  }));
};

export const createMockUseLoadingState = () => {
  return jest.fn(() => ({
    isLoading: false,
    setLoading: jest.fn()
  }));
};

export const createMockUseThreadNavigation = () => {
  return jest.fn(() => ({
    currentThread: null,
    navigateToThread: jest.fn(),
    createThread: jest.fn()
  }));
};

// Setup helpers
export const setupDefaultHookMocks = () => {
  // Default mock implementations
};

export const setupAuthMocks = () => {
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      json: async () => ({ token: 'test-token', user: { id: '1', email: 'test@example.com' } })
    })
  ) as jest.Mock;
};

export const setupLoadingMocks = () => {
  // Loading state mocks
};

// Mock setup functions
export const setupAllMocks = () => {
  setupDefaultHookMocks();
  setupAuthMocks();
  setupLoadingMocks();
};

export const setupLLMCacheResponseMocks = () => {
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      json: async () => ({ cached: false, response: 'test response' })
    })
  ) as jest.Mock;
};

export const setupCacheSizeLimitMock = () => {
  // Cache size limit mock
};

export const setupCacheWarmingMock = (prompts: string[]) => {
  // Cache warming mock
};

export const setupCacheCollisionMock = (prompts: string[]) => {
  // Cache collision mock
};

export const setupTaskProcessingMock = () => {
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      json: async () => ({ task: { id: '1', status: 'completed' } })
    })
  ) as jest.Mock;
};

export const setupTaskRetryMock = () => {
  // Task retry mock
};

export const setupHealthMock = () => {
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      json: async () => ({ status: 'healthy', services: {} })
    })
  ) as jest.Mock;
};

export const setupDegradedHealthMock = () => {
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      json: async () => ({ status: 'degraded', services: { api: 'down' } })
    })
  ) as jest.Mock;
};

export const setupCorpusUploadMock = () => {
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      json: async () => ({ document: { id: '1', name: 'test.txt' } })
    })
  ) as jest.Mock;
};

export const setupCorpusSearchMock = () => {
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      json: async () => ({ results: [] })
    })
  ) as jest.Mock;
};

export const setupGenerationMock = () => {
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      json: async () => ({ job: { id: '1', status: 'running' } })
    })
  ) as jest.Mock;
};

export const setupExportMock = () => {
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      blob: async () => new Blob(['export data'])
    })
  ) as jest.Mock;
};

// Utility functions
export const queryLLMCache = async (prompt: string, model: string) => {
  const response = await fetch('/api/llm/cache', {
    method: 'POST',
    body: JSON.stringify({ prompt, model })
  });
  return response.json();
};

export const clearCacheAndVerify = async (getByText: Function) => {
  const clearButton = getByText('Clear Cache');
  clearButton.click();
  // Verification logic
};

export const fillCacheToLimit = async () => {
  // Fill cache logic
};

export const verifyCacheEviction = () => {
  // Verify eviction logic
};

export const warmCache = async (prompts: string[]) => {
  // Warm cache logic
};

export const verifyCacheWarmed = (count: number) => {
  // Verify cache warmed logic
};

export const handleCacheCollisions = async (prompts: string[]) => {
  // Handle collisions logic
};

export const verifyCacheHitMiss = (response1: any, response2: any) => {
  expect(response1.cached).toBe(false);
  expect(response2.cached).toBe(true);
};

export const createMockTask = (overrides = {}) => ({
  id: '1',
  type: 'process',
  status: 'pending',
  ...overrides
});

export const queueTask = async (task: any) => {
  const response = await fetch('/api/tasks', {
    method: 'POST',
    body: JSON.stringify(task)
  });
  return response.json();
};

export const createMockDocument = (overrides = {}) => ({
  id: '1',
  name: 'document.txt',
  content: 'test content',
  ...overrides
});

export const createMockSearchResults = (count = 3) => {
  return Array.from({ length: count }, (_, i) => ({
    id: `result-${i}`,
    score: 1.0 - i * 0.1,
    content: `Result ${i}`
  }));
};

export const createMockGenerationJob = (overrides = {}) => ({
  id: '1',
  status: 'pending',
  progress: 0,
  ...overrides
});

export const createMockExportData = () => ({
  format: 'json',
  data: { documents: [], metadata: {} }
});

export const createMockHealthStatus = () => ({
  status: 'healthy',
  timestamp: Date.now(),
  services: {
    api: 'healthy',
    database: 'healthy',
    cache: 'healthy'
  }
});

export const createMockDegradedHealth = () => ({
  status: 'degraded',
  timestamp: Date.now(),
  services: {
    api: 'healthy',
    database: 'degraded',
    cache: 'healthy'
  }
});