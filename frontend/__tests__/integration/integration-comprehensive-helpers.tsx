/**
 * Comprehensive Integration Test Helpers
 * Helper functions for comprehensive integration testing
 */

import React from 'react';
import WS from 'jest-websocket-mock';
import { jest } from '@jest/globals';
import { safeWebSocketCleanup } from '../helpers/websocket-test-manager';

// Setup functions
export const setupComprehensiveTestEnvironment = (): WS => {
  process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000';
  process.env.NEXT_PUBLIC_WS_URL = 'ws://localhost:8000';
  const server = new WS('ws://localhost:8000/ws');
  jest.clearAllMocks();
  localStorage.clear();
  sessionStorage.clear();
  return server;
};

export const cleanupComprehensiveTestEnvironment = (): void => {
  safeWebSocketCleanup();
  jest.restoreAllMocks();
};

// Mock setup
export const setupComprehensiveMocks = () => {
  const mockUseUnifiedChatStore = jest.fn(() => ({
    messages: [],
    addMessage: jest.fn(),
    clearMessages: jest.fn(),
    isLoading: false,
    setLoading: jest.fn()
  }));

  const mockUseWebSocket = jest.fn(() => ({
    socket: null,
    connected: false,
    connect: jest.fn(),
    disconnect: jest.fn(),
    send: jest.fn()
  }));

  const mockUseAgent = jest.fn(() => ({
    agent: null,
    isProcessing: false,
    processMessage: jest.fn(),
    reset: jest.fn()
  }));

  const mockUseAuthStore = jest.fn(() => ({
    user: null,
    token: null,
    isAuthenticated: false,
    login: jest.fn(),
    logout: jest.fn()
  }));

  const mockUseLoadingState = jest.fn(() => ({
    isLoading: false,
    setLoading: jest.fn()
  }));

  const mockUseThreadNavigation = jest.fn(() => ({
    currentThread: null,
    navigateToThread: jest.fn(),
    createThread: jest.fn()
  }));

  return {
    mockUseUnifiedChatStore,
    mockUseWebSocket,
    mockUseAgent,
    mockUseAuthStore,
    mockUseLoadingState,
    mockUseThreadNavigation
  };
};

export const setupComprehensiveHookMocks = () => {
  // Additional hook mocks
};

export const setupComprehensiveAuthMocks = () => {
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      json: async () => ({ token: 'test-token', user: { id: '1', email: 'test@example.com' } })
    })
  ) as jest.Mock;
};

// Store creators
export const createComprehensiveCorpusStore = () => {
  return jest.fn(() => ({
    documents: [],
    addDocument: jest.fn(),
    removeDocument: jest.fn(),
    searchDocuments: jest.fn(),
    reset: jest.fn()
  }));
};

export const createComprehensiveSyntheticStore = () => {
  return jest.fn(() => ({
    data: [],
    generateData: jest.fn(),
    clearData: jest.fn(),
    reset: jest.fn()
  }));
};

// Service creators
export const createComprehensiveCorpusService = () => ({
  uploadDocument: jest.fn(),
  searchCorpus: jest.fn(),
  deleteDocument: jest.fn(),
  exportCorpus: jest.fn()
});

export const createComprehensiveSyntheticService = () => ({
  generateSyntheticData: jest.fn(),
  exportData: jest.fn(),
  validateData: jest.fn()
});

export const createComprehensiveLLMService = () => ({
  queryCache: jest.fn(),
  warmCache: jest.fn(),
  evictCache: jest.fn(),
  getCacheStats: jest.fn()
});

export const createComprehensiveHealthService = () => ({
  checkHealth: jest.fn(),
  monitorServices: jest.fn(),
  getServiceStatus: jest.fn()
});

// Mock data creators
export const createComprehensiveMockDocument = (overrides = {}) => ({
  id: '1',
  name: 'document.txt',
  content: 'test content',
  size: 1024,
  type: 'text/plain',
  ...overrides
});

export const createComprehensiveMockSearchResults = (count = 3) => {
  return Array.from({ length: count }, (_, i) => ({
    id: `result-${i}`,
    score: 1.0 - i * 0.1,
    content: `Result ${i}`,
    document_id: `doc-${i}`
  }));
};

export const createComprehensiveMockGenerationJob = (overrides = {}) => ({
  id: '1',
  status: 'pending',
  progress: 0,
  total: 100,
  ...overrides
});

export const createComprehensiveMockExportData = () => ({
  format: 'json',
  timestamp: Date.now(),
  data: { 
    documents: [], 
    metadata: {
      version: '1.0',
      exportDate: new Date().toISOString()
    }
  }
});

export const createComprehensiveMockHealthStatus = () => ({
  status: 'healthy',
  timestamp: Date.now(),
  services: {
    api: 'healthy',
    database: 'healthy',
    cache: 'healthy',
    websocket: 'healthy'
  }
});

export const createComprehensiveMockDegradedHealth = () => ({
  status: 'degraded',
  timestamp: Date.now(),
  services: {
    api: 'healthy',
    database: 'degraded',
    cache: 'healthy',
    websocket: 'healthy'
  }
});

// Component creators
export const createComprehensiveGenerationTestComponent = () => {
  return function GenerationTest() {
    return <div data-testid="generation-test">Generation Test</div>;
  };
};

export const createComprehensiveCacheManagementComponent = () => {
  return function CacheManagement() {
    return <div data-testid="cache-management">Cache Management</div>;
  };
};

export const createComprehensiveTaskRetryComponent = () => {
  return function TaskRetry() {
    return <div data-testid="task-retry">Task Retry</div>;
  };
};

export const createComprehensiveHealthMonitorComponent = () => {
  return function HealthMonitor() {
    return <div data-testid="health-monitor">Health Monitor</div>;
  };
};

// Mock setup functions
export const setupComprehensiveCorpusUploadMock = () => {
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      json: async () => ({ 
        document: createComprehensiveMockDocument()
      })
    })
  ) as jest.Mock;
};

export const setupComprehensiveCorpusSearchMock = () => {
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      json: async () => ({ 
        results: createComprehensiveMockSearchResults()
      })
    })
  ) as jest.Mock;
};

export const setupComprehensiveGenerationMock = () => {
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      json: async () => ({ 
        job: createComprehensiveMockGenerationJob()
      })
    })
  ) as jest.Mock;
};

export const setupComprehensiveExportMock = () => {
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      blob: async () => new Blob(['export data'], { type: 'application/json' })
    })
  ) as jest.Mock;
};

export const setupComprehensiveLLMCacheResponseMocks = () => {
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      json: async () => ({ 
        cached: false, 
        response: 'test response',
        model: 'gemini-2.5-flash',
        tokens: 100
      })
    })
  ) as jest.Mock;
};

export const setupComprehensiveHealthMock = () => {
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      json: async () => createComprehensiveMockHealthStatus()
    })
  ) as jest.Mock;
};

export const setupComprehensiveDegradedHealthMock = () => {
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      json: async () => createComprehensiveMockDegradedHealth()
    })
  ) as jest.Mock;
};

// Task helpers
export const createComprehensiveMockTask = (overrides = {}) => ({
  id: '1',
  type: 'process',
  status: 'pending',
  priority: 'normal',
  created_at: Date.now(),
  ...overrides
});

export const queueComprehensiveTask = async (task: any) => {
  const response = await fetch('/api/tasks', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(task)
  });
  return response.json();
};