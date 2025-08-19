/**
 * Shared utilities for Integration tests
 * Module-based architecture: Common mocks and setup utilities ≤300 lines
 */

import React from 'react';
import WS from 'jest-websocket-mock';
import { TestProviders } from '../test-utils/providers';

// Mock store creators (≤8 lines each)
export const createMockUseUnifiedChatStore = () => jest.fn();
export const createMockUseWebSocket = () => jest.fn();
export const createMockUseAgent = () => jest.fn();
export const createMockUseAuthStore = () => jest.fn();
export const createMockUseLoadingState = () => jest.fn();
export const createMockUseThreadNavigation = () => jest.fn();

// Mock store implementations (≤8 lines each)
export const createCorpusStore = () => Object.assign(
  jest.fn(() => ({ documents: [], addDocument: jest.fn() })),
  { getState: jest.fn(() => ({ documents: [], addDocument: jest.fn() })) }
);

export const createSyntheticDataStore = () => Object.assign(
  jest.fn(() => ({ jobs: [], generateData: jest.fn() })),
  { getState: jest.fn(() => ({ jobs: [], generateData: jest.fn() })) }
);

export const createLLMCacheStore = () => Object.assign(
  jest.fn(() => ({ cacheSize: 0, clearCache: jest.fn(), setCacheTTL: jest.fn() })),
  { getState: jest.fn(() => ({ cacheSize: 0, clearCache: jest.fn(), setCacheTTL: jest.fn() })) }
);

// Mock service creators (≤8 lines each)
export const createCorpusService = () => ({ 
  uploadDocument: jest.fn().mockResolvedValue({}), 
  searchDocuments: jest.fn().mockResolvedValue([]) 
});

export const createSyntheticDataService = () => ({ 
  exportData: jest.fn().mockResolvedValue(new Blob(['data'])) 
});

export const createLLMCacheService = () => ({ 
  query: jest.fn().mockResolvedValue({ cached: false, response: 'response' }) 
});

export const createHealthService = () => ({ 
  checkHealth: jest.fn().mockResolvedValue({ 
    status: 'healthy', 
    services: { database: 'up', redis: 'up' } 
  }) 
});

// Mock data factories (≤8 lines each)
export const createMockDocument = () => ({
  id: 'doc-123',
  title: 'Test Document',
  content: 'Test content',
  embeddings: [0.1, 0.2, 0.3],
  created_at: Date.now()
});

export const createMockSearchResults = () => ([
  { id: 'result-1', title: 'Result 1', score: 0.95 },
  { id: 'result-2', title: 'Result 2', score: 0.87 }
]);

export const createMockGenerationJob = () => ({
  id: 'job-456',
  status: 'processing',
  template: 'customer_support',
  count: 100,
  progress: 0
});

export const createMockExportData = () => ({
  format: 'json',
  data: [{ id: 1, content: 'synthetic' }],
  size: 1024
});

export const createMockHealthStatus = () => ({
  status: 'healthy',
  services: { database: 'up', redis: 'up' }
});

export const createMockDegradedHealth = () => ({
  status: 'degraded',
  services: { database: 'up', redis: 'down' }
});

// Test setup helpers (≤8 lines each)
export const setupIntegrationTest = () => {
  const server = new WS('ws://localhost:8000/ws');
  global.fetch = jest.fn();
  clearTestStorage();
  resetTestStores();
  setupMockFetch();
  return server;
};

export const teardownIntegrationTest = () => {
  jest.clearAllMocks();
  jest.restoreAllMocks();
  localStorage.clear();
  sessionStorage.clear();
};

export const clearTestStorage = () => {
  localStorage.clear();
  sessionStorage.clear();
};

export const resetTestStores = () => {
  // Reset any global store state if needed
  jest.clearAllMocks();
};

export const setupMockFetch = () => {
  global.fetch = jest.fn().mockResolvedValue({
    ok: true,
    json: jest.fn().mockResolvedValue({})
  });
};

// Mock hook setup helpers (≤8 lines each)
export const setupDefaultHookMocks = (mocks: any) => {
  mocks.mockUseUnifiedChatStore.mockReturnValue({
    messages: [],
    threads: [],
    addMessage: jest.fn(),
    updateThread: jest.fn(),
    fastLayerData: null,
    updateFastLayer: jest.fn()
  });
  
  mocks.mockUseWebSocket.mockReturnValue({
    sendMessage: jest.fn(),
    isConnected: true,
    connectionState: 'connected'
  });
};

export const setupAuthMocks = (mocks: any) => {
  mocks.mockUseAgent.mockReturnValue({
    isProcessing: false,
    sendMessage: jest.fn()
  });
  
  mocks.mockUseAuthStore.mockReturnValue({
    isAuthenticated: true,
    user: { id: '1', email: 'test@example.com' }
  });
};

export const setupLoadingMocks = (mocks: any) => {
  mocks.mockUseLoadingState.mockReturnValue({
    isLoading: false,
    setLoading: jest.fn()
  });
  
  mocks.mockUseThreadNavigation.mockReturnValue({
    currentThreadId: 'thread-1',
    navigateToThread: jest.fn()
  });
};

// Test component helpers (≤8 lines each)
export const createTestComponent = (children: React.ReactNode) => {
  return (
    <TestProviders>
      {children}
    </TestProviders>
  );
};

export const createGenerationTestComponent = () => {
  return () => {
    const [step, setStep] = React.useState('upload');
    const [connected, setConnected] = React.useState(false);
    const [jobStatus, setJobStatus] = React.useState('idle');
    
    React.useEffect(() => {
      const timer = setTimeout(() => setConnected(true), 100);
      return () => clearTimeout(timer);
    }, []);
    
    const handleGenerate = async () => {
      setJobStatus('processing');
      await new Promise(resolve => setTimeout(resolve, 100));
    };
    
    return (
      <div>
        <button onClick={handleGenerate}>Generate</button>
        <div data-testid="job-status">{jobStatus}</div>
        <div data-testid="ws-connected">{connected ? 'connected' : 'disconnected'}</div>
      </div>
    );
  };
};

export const createCacheManagementComponent = () => {
  return () => {
    const [cacheSize, setCacheSize] = React.useState(100);
    
    const handleClearCache = () => {
      setCacheSize(0);
    };
    
    return (
      <div>
        <div data-testid="cache-size">{cacheSize}</div>
        <button onClick={handleClearCache}>Clear Cache</button>
      </div>
    );
  };
};

export const createTaskRetryComponent = () => {
  return () => {
    const [retryCount, setRetryCount] = React.useState(0);
    const [status, setStatus] = React.useState('idle');
    
    const retryTask = async () => {
      setStatus('retrying');
      for (let i = 0; i < 3; i++) {
        await new Promise(resolve => setTimeout(resolve, Math.pow(2, i) * 100));
        setRetryCount(i + 1);
      }
      setStatus('completed');
    };
    
    React.useEffect(() => {
      retryTask();
    }, []);
    
    return (
      <div>
        <div data-testid="retry-count">{retryCount}</div>
        <div data-testid="status">{status}</div>
      </div>
    );
  };
};