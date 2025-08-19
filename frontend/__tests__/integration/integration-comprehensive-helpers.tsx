/**
 * Comprehensive Integration Test Helpers
 * Module-based architecture: Helper functions ≤300 lines, functions ≤8 lines
 */

import React from 'react';
import WS from 'jest-websocket-mock';
import { TestProviders } from '../test-utils/providers';

// Mock store setup helpers (≤8 lines each)
export const setupComprehensiveMocks = () => {
  const mockUseUnifiedChatStore = jest.fn();
  const mockUseWebSocket = jest.fn();
  const mockUseAgent = jest.fn();
  const mockUseAuthStore = jest.fn();
  const mockUseLoadingState = jest.fn();
  const mockUseThreadNavigation = jest.fn();
  
  return {
    mockUseUnifiedChatStore,
    mockUseWebSocket,
    mockUseAgent,
    mockUseAuthStore,
    mockUseLoadingState,
    mockUseThreadNavigation
  };
};

export const setupComprehensiveHookMocks = (mocks: any) => {
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

export const setupComprehensiveAuthMocks = (mocks: any) => {
  mocks.mockUseAgent.mockReturnValue({
    isProcessing: false,
    sendMessage: jest.fn()
  });
  
  mocks.mockUseAuthStore.mockReturnValue({
    isAuthenticated: true,
    user: { id: '1', email: 'test@example.com' }
  });
};

// Store creators for comprehensive tests (≤8 lines each)
export const createComprehensiveCorpusStore = () => Object.assign(
  jest.fn(() => ({ documents: [], addDocument: jest.fn() })),
  { getState: jest.fn(() => ({ documents: [], addDocument: jest.fn() })) }
);

export const createComprehensiveSyntheticStore = () => Object.assign(
  jest.fn(() => ({ jobs: [], generateData: jest.fn() })),
  { getState: jest.fn(() => ({ jobs: [], generateData: jest.fn() })) }
);

export const createComprehensiveLLMStore = () => Object.assign(
  jest.fn(() => ({ cacheSize: 0, clearCache: jest.fn(), setCacheTTL: jest.fn() })),
  { getState: jest.fn(() => ({ cacheSize: 0, clearCache: jest.fn(), setCacheTTL: jest.fn() })) }
);

// Mock service creators (≤8 lines each)
export const createComprehensiveCorpusService = () => ({ 
  uploadDocument: jest.fn().mockResolvedValue({}), 
  searchDocuments: jest.fn().mockResolvedValue([]) 
});

export const createComprehensiveSyntheticService = () => ({ 
  exportData: jest.fn().mockResolvedValue(new Blob(['data'])) 
});

export const createComprehensiveLLMService = () => ({ 
  query: jest.fn().mockResolvedValue({ cached: false, response: 'response' }) 
});

export const createComprehensiveHealthService = () => ({ 
  checkHealth: jest.fn().mockResolvedValue({ 
    status: 'healthy', 
    services: { database: 'up', redis: 'up' } 
  }) 
});

// Test environment setup (≤8 lines each)
export const setupComprehensiveTestEnvironment = () => {
  const server = new WS('ws://localhost:8000/ws');
  global.fetch = jest.fn();
  clearComprehensiveTestStorage();
  resetComprehensiveTestStores();
  setupComprehensiveMockFetch();
  return server;
};

export const cleanupComprehensiveTestEnvironment = () => {
  jest.clearAllMocks();
  jest.restoreAllMocks();
  localStorage.clear();
  sessionStorage.clear();
};

export const clearComprehensiveTestStorage = () => {
  localStorage.clear();
  sessionStorage.clear();
};

export const resetComprehensiveTestStores = () => {
  jest.clearAllMocks();
};

export const setupComprehensiveMockFetch = () => {
  global.fetch = jest.fn().mockResolvedValue({
    ok: true,
    json: jest.fn().mockResolvedValue({})
  });
};

// Mock data factories (≤8 lines each)
export const createComprehensiveMockDocument = () => ({
  id: 'doc-123',
  title: 'Test Document',
  content: 'Test content',
  embeddings: [0.1, 0.2, 0.3],
  created_at: Date.now()
});

export const createComprehensiveMockSearchResults = () => ([
  { id: 'result-1', title: 'Result 1', score: 0.95 },
  { id: 'result-2', title: 'Result 2', score: 0.87 }
]);

export const createComprehensiveMockGenerationJob = () => ({
  id: 'job-456',
  status: 'processing',
  template: 'customer_support',
  count: 100,
  progress: 0
});

export const createComprehensiveMockExportData = () => ({
  format: 'json',
  data: [{ id: 1, content: 'synthetic' }],
  size: 1024
});

export const createComprehensiveMockHealthStatus = () => ({
  status: 'healthy',
  services: { database: 'up', redis: 'up' }
});

export const createComprehensiveMockDegradedHealth = () => ({
  status: 'degraded',
  services: { database: 'up', redis: 'down' }
});

// Test component creators (≤8 lines each)
export const createComprehensiveGenerationTestComponent = () => {
  return () => {
    const [jobStatus, setJobStatus] = React.useState('idle');
    const [connected, setConnected] = React.useState(false);
    
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

export const createComprehensiveCacheManagementComponent = () => {
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

export const createComprehensiveTaskRetryComponent = () => {
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

export const createComprehensiveHealthMonitorComponent = () => {
  return () => {
    const [health, setHealth] = React.useState<any>(null);
    
    React.useEffect(() => {
      const mockHealthService = createComprehensiveHealthService();
      mockHealthService.checkHealth().then(setHealth);
    }, []);
    
    return (
      <div>
        <div data-testid="health-status">{health?.status || 'checking'}</div>
        {health?.status === 'degraded' && (
          <div data-testid="alert">Service Degraded</div>
        )}
      </div>
    );
  };
};

// Mock setup helpers ≤8 lines each
export const setupComprehensiveCorpusUploadMock = (mockDocument: any) => {
  (fetch as jest.Mock).mockResolvedValueOnce({
    ok: true,
    json: async () => mockDocument
  });
};

export const setupComprehensiveCorpusSearchMock = (mockResults: any) => {
  (fetch as jest.Mock).mockResolvedValueOnce({
    ok: true,
    json: async () => mockResults
  });
};

export const setupComprehensiveGenerationMock = (mockJob: any) => {
  (fetch as jest.Mock).mockResolvedValueOnce({
    ok: true,
    json: async () => mockJob
  });
};

export const setupComprehensiveExportMock = (mockData: any, syntheticService: any) => {
  syntheticService.exportData = jest.fn().mockResolvedValue(
    new Blob([JSON.stringify(mockData)])
  );
};

export const setupComprehensiveLLMCacheResponseMocks = (llmService: any) => {
  llmService.query
    .mockResolvedValueOnce({ cached: false, response: 'new response' })
    .mockResolvedValueOnce({ cached: true, response: 'cached response' });
};

export const setupComprehensiveHealthMock = (mockHealth: any, healthService: any) => {
  healthService.checkHealth = jest.fn().mockResolvedValue(mockHealth);
};

export const setupComprehensiveDegradedHealthMock = (mockHealth: any, healthService: any) => {
  healthService.checkHealth = jest.fn().mockResolvedValue(mockHealth);
};

// Task helpers (≤8 lines each)
export const createComprehensiveMockTask = () => ({
  id: 'task-123',
  type: 'data_processing',
  status: 'queued',
  created_at: Date.now()
});

export const queueComprehensiveTask = async (task: any) => {
  return { ...task, status: 'processing' };
};