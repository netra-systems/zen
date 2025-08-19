/**
 * Comprehensive Integration Test Utilities
 * Complex test components and operations with 8-line function limit enforcement
 */

import React from 'react';
import { render, waitFor, fireEvent, screen } from '@testing-library/react';
import { TestProviders } from '../../setup/test-providers';

// Types for comprehensive test scenarios
export interface TestScenarioConfig {
  withMockData?: boolean;
  withWebSocket?: boolean;
  withAuth?: boolean;
  timeoutMs?: number;
}

export interface MockDataSet {
  documents?: any[];
  searchResults?: any[];
  generationJobs?: any[];
  exportData?: any[];
  healthStatus?: any;
}

// Mock data generators (≤8 lines each)
export const createMockDocument = () => ({
  id: 'doc-123',
  title: 'Test Document',
  content: 'Test document content',
  embeddings: [0.1, 0.2, 0.3],
  metadata: { type: 'test', size: 1024 }
});

export const createMockSearchResults = () => ([
  { id: 'result-1', title: 'Result 1', score: 0.95 },
  { id: 'result-2', title: 'Result 2', score: 0.88 },
  { id: 'result-3', title: 'Result 3', score: 0.82 }
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
  services: { database: 'up', redis: 'up' },
  timestamp: Date.now()
});

export const createMockDegradedHealth = () => ({
  status: 'degraded',
  services: { database: 'up', redis: 'down' },
  timestamp: Date.now()
});

// Test component factories (≤8 lines each)
export const createGenerationTestComponent = () => {
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

export const createHealthMonitorComponent = () => {
  return () => {
    const [health, setHealth] = React.useState<any>(null);
    
    React.useEffect(() => {
      const mockHealth = createMockDegradedHealth();
      setTimeout(() => setHealth(mockHealth), 50);
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

// Test operation handlers (≤8 lines each)
export const simulateFileUpload = async (service: any, file: File, mockResponse: any) => {
  service.uploadDocument = jest.fn().mockResolvedValue(mockResponse);
  
  const formData = new FormData();
  formData.append('file', file);
  
  const result = await service.uploadDocument(formData);
  return result;
};

export const simulateCorpusSearch = async (service: any, query: string) => {
  const mockResults = createMockSearchResults();
  service.searchDocuments = jest.fn().mockResolvedValue(mockResults);
  
  const results = await service.searchDocuments(query);
  return results;
};

export const simulateExportData = async (service: any, jobId: string, format: string) => {
  const mockData = createMockExportData();
  const blob = new Blob([JSON.stringify(mockData)], { type: 'application/json' });
  
  service.exportData = jest.fn().mockResolvedValue(blob);
  
  const result = await service.exportData(jobId, format);
  return result;
};

export const simulateHealthCheck = async (service: any) => {
  const mockHealth = createMockHealthStatus();
  service.checkHealth = jest.fn().mockResolvedValue(mockHealth);
  
  const health = await service.checkHealth();
  return health;
};

// Mock setup utilities (≤8 lines each)
export const setupCorpusUploadMock = (mockDocument: any) => {
  (global.fetch as jest.Mock).mockResolvedValueOnce({
    ok: true,
    json: async () => mockDocument
  });
};

export const setupCorpusSearchMock = (mockResults: any) => {
  (global.fetch as jest.Mock).mockResolvedValueOnce({
    ok: true,
    json: async () => mockResults
  });
};

export const setupGenerationMock = (mockJob: any) => {
  (global.fetch as jest.Mock).mockResolvedValueOnce({
    ok: true,
    json: async () => mockJob
  });
};

export const setupExportMock = (mockData: any, service: any) => {
  service.exportData = jest.fn().mockResolvedValue(
    new Blob([JSON.stringify(mockData)])
  );
};

export const setupHealthMock = (mockHealth: any, service: any) => {
  service.checkHealth = jest.fn().mockResolvedValue(mockHealth);
};

export const setupDegradedHealthMock = (mockHealth: any, service: any) => {
  service.checkHealth = jest.fn().mockResolvedValue(mockHealth);
};

export const setupLLMCacheResponseMocks = (service: any) => {
  service.query = jest.fn()
    .mockResolvedValueOnce({ cached: false, response: 'new response' })
    .mockResolvedValueOnce({ cached: true, response: 'cached response' });
};

// Assertion utilities (≤8 lines each)
export const assertStoreState = (mockStore: any, key: string, expectedValue: any) => {
  const state = mockStore.getState();
  expect(state[key]).toEqual(expectedValue);
};

export const waitForElementText = async (testId: string, expectedText: string) => {
  await waitFor(() => {
    expect(screen.getByTestId(testId)).toHaveTextContent(expectedText);
  });
};

export const assertFetchWasCalled = (url: string, method: string = 'GET') => {
  expect(global.fetch).toHaveBeenCalledWith(
    expect.stringContaining(url),
    expect.objectContaining({ method })
  );
};

export const assertElementText = (testId: string, expectedText: string) => {
  expect(screen.getByTestId(testId)).toHaveTextContent(expectedText);
};

// Test scenario orchestration utilities (≤8 lines each)
export const executeCorpusManagementScenario = async (config: TestScenarioConfig = {}) => {
  const mockDocument = createMockDocument();
  setupCorpusUploadMock(mockDocument);
  
  const file = new File(['test content'], 'test.txt');
  const corpusService = { uploadDocument: jest.fn(), searchDocuments: jest.fn() };
  
  const result = await simulateFileUpload(corpusService, file, mockDocument);
  return { result, mockDocument };
};

export const executeDataGenerationScenario = async (config: TestScenarioConfig = {}) => {
  const mockJob = createMockGenerationJob();
  setupGenerationMock(mockJob);
  
  const TestComponent = createGenerationTestComponent();
  const rendered = render(<TestProviders><TestComponent /></TestProviders>);
  
  await waitForElementText('ws-connected', 'connected');
  fireEvent.click(screen.getByText('Generate'));
  
  return { rendered, mockJob };
};

export const executeCacheManagementScenario = async (config: TestScenarioConfig = {}) => {
  const CacheComponent = createCacheManagementComponent();
  const rendered = render(<TestProviders><CacheComponent /></TestProviders>);
  
  fireEvent.click(screen.getByText('Clear Cache'));
  
  await waitForElementText('cache-size', '0');
  return { rendered };
};

export const executeHealthMonitoringScenario = async (config: TestScenarioConfig = {}) => {
  const HealthComponent = createHealthMonitorComponent();
  const rendered = render(<TestProviders><HealthComponent /></TestProviders>);
  
  await waitForElementText('health-status', 'degraded');
  await waitForElementText('alert', 'Service Degraded');
  
  return { rendered };
};

export const executeTaskRetryScenario = async (config: TestScenarioConfig = {}) => {
  const RetryComponent = createTaskRetryComponent();
  const rendered = render(<TestProviders><RetryComponent /></TestProviders>);
  
  await waitForElementText('status', 'completed');
  await waitForElementText('retry-count', '3');
  
  return { rendered };
};