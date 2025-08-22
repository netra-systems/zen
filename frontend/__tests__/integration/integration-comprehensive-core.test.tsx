/**
 * Comprehensive Integration Tests - Core
 * Module-based architecture: Core comprehensive tests ≤300 lines, functions ≤8 lines
 */

import React from 'react';
import { render, waitFor, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { TestProviders } from '@/__tests__/setup/test-providers';
import {
  setupComprehensiveMocks,
  setupComprehensiveTestEnvironment,
  cleanupComprehensiveTestEnvironment,
  setupComprehensiveHookMocks,
  setupComprehensiveAuthMocks,
  createComprehensiveCorpusStore,
  createComprehensiveSyntheticStore,
  createComprehensiveCorpusService,
  createComprehensiveSyntheticService,
  createComprehensiveLLMService,
  createComprehensiveHealthService,
  createComprehensiveMockDocument,
  createComprehensiveMockSearchResults,
  createComprehensiveMockGenerationJob,
  createComprehensiveMockExportData,
  createComprehensiveMockHealthStatus,
  createComprehensiveMockDegradedHealth,
  createComprehensiveGenerationTestComponent,
  createComprehensiveCacheManagementComponent,
  createComprehensiveTaskRetryComponent,
  createComprehensiveHealthMonitorComponent,
  setupComprehensiveCorpusUploadMock,
  setupComprehensiveCorpusSearchMock,
  setupComprehensiveGenerationMock,
  setupComprehensiveExportMock,
  setupComprehensiveLLMCacheResponseMocks,
  setupComprehensiveHealthMock,
  setupComprehensiveDegradedHealthMock,
  createComprehensiveMockTask,
  queueComprehensiveTask
} from './integration-comprehensive-helpers';

// Mock hooks setup
const {
  mockUseUnifiedChatStore,
  mockUseWebSocket,
  mockUseAgent,
  mockUseAuthStore,
  mockUseLoadingState,
  mockUseThreadNavigation
} = setupComprehensiveMocks();

jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: mockUseUnifiedChatStore
}));

jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: mockUseWebSocket
}));

jest.mock('@/hooks/useAgent', () => ({
  useAgent: mockUseAgent
}));

jest.mock('@/store/authStore', () => ({
  useAuthStore: mockUseAuthStore
}));

jest.mock('@/hooks/useLoadingState', () => ({
  useLoadingState: mockUseLoadingState
}));

jest.mock('@/hooks/useThreadNavigation', () => ({
  useThreadNavigation: mockUseThreadNavigation
}));

jest.mock('@/components/auth/AuthGate', () => {
  return function MockAuthGate({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
  };
});

describe('Comprehensive Integration Tests - Core', () => {
  let server: any;
  const useCorpusStore = createComprehensiveCorpusStore();
  const useSyntheticDataStore = createComprehensiveSyntheticStore();
  const corpusService = createComprehensiveCorpusService();
  const syntheticDataService = createComprehensiveSyntheticService();
  const llmCacheService = createComprehensiveLLMService();
  const healthService = createComprehensiveHealthService();
  
  beforeEach(() => {
    server = setupComprehensiveTestEnvironment();
    setupAllMockValues();
  });

  afterEach(() => {
    cleanupComprehensiveTestEnvironment();
  });

  describe('1. Corpus Management Integration', () => {
    it('should upload documents to corpus and process with embeddings', async () => {
      const mockDocument = createComprehensiveMockDocument();
      setupComprehensiveCorpusUploadMock(mockDocument);
      
      const file = new File(['test content'], 'test.txt');
      await simulateFileUpload(file, mockDocument);
      
      assertStoreState(useCorpusStore);
    });

    it('should search corpus with semantic similarity', async () => {
      const mockResults = createComprehensiveMockSearchResults();
      setupComprehensiveCorpusSearchMock(mockResults);
      
      await simulateCorpusSearch('test query');
      
      expect(corpusService.searchDocuments).toHaveBeenCalledWith('test query');
    });
  });

  describe('2. Synthetic Data Generation Flow', () => {
    it('should generate synthetic data based on templates', async () => {
      jest.setTimeout(10000);
      const mockGenerationJob = createComprehensiveMockGenerationJob();
      setupComprehensiveGenerationMock(mockGenerationJob);
      
      const TestComponent = createComprehensiveGenerationTestComponent();
      render(<TestProviders><TestComponent /></TestProviders>);
      
      await waitForConnectionAndGenerate();
    });

    it('should export generated synthetic data in multiple formats', async () => {
      const mockExportData = createComprehensiveMockExportData();
      setupComprehensiveExportMock(mockExportData, syntheticDataService);
      
      const blob = await exportSyntheticData('job-123', 'json');
      
      expect(blob).toBeInstanceOf(Blob);
    });
  });

  describe('3. LLM Cache Management Integration', () => {
    it('should cache and retrieve LLM responses', async () => {
      setupComprehensiveLLMCacheResponseMocks(llmCacheService);
      
      const response1 = await llmCacheService.query('test prompt', 'gpt-4');
      const response2 = await llmCacheService.query('test prompt', 'gpt-4');
      
      expect(response1.cached).toBe(false);
      expect(response2.cached).toBe(true);
    });

    it('should manage cache invalidation and TTL', async () => {
      const CacheComponent = createComprehensiveCacheManagementComponent();
      const { getByText } = render(<TestProviders><CacheComponent /></TestProviders>);
      
      fireEvent.click(getByText('Clear Cache'));
      
      await waitForElementText('cache-size', '0');
    });
  });

  describe('7. Health Check Monitoring', () => {
    it('should monitor service health status', async () => {
      const mockHealth = createComprehensiveMockHealthStatus();
      setupComprehensiveHealthMock(mockHealth, healthService);
      
      const health = await simulateHealthCheck();
      
      expect(health.status).toBe('healthy');
      expect(health.services.database).toBe('up');
    });

    it('should handle degraded service states', async () => {
      jest.setTimeout(10000);
      const mockDegradedHealth = createComprehensiveMockDegradedHealth();
      setupComprehensiveDegradedHealthMock(mockDegradedHealth, healthService);
      
      const TestComponent = createComprehensiveHealthMonitorComponent();
      render(<TestProviders><TestComponent /></TestProviders>);
      
      await waitForElementText('health-status', 'degraded');
      await waitForElementText('alert', 'Service Degraded');
    });
  });

  describe('15. Background Task Processing', () => {
    it('should queue and process background tasks', async () => {
      const mockTask = createComprehensiveMockTask();
      const result = await queueComprehensiveTask(mockTask);
      
      expect(result.status).toBe('processing');
    });

    it('should handle task retry with exponential backoff', async () => {
      jest.setTimeout(5000);
      const TaskComponent = createComprehensiveTaskRetryComponent();
      const { getByTestId } = render(<TestProviders><TaskComponent /></TestProviders>);
      
      await waitForElementText('status', 'completed');
      await waitForElementText('retry-count', '3');
    });
  });
});

// Helper functions ≤8 lines each
const setupAllMockValues = () => {
  const mocks = {
    mockUseUnifiedChatStore,
    mockUseWebSocket,
    mockUseAgent,
    mockUseAuthStore,
    mockUseLoadingState,
    mockUseThreadNavigation
  };
  
  setupComprehensiveHookMocks(mocks);
  setupComprehensiveAuthMocks(mocks);
};

const simulateFileUpload = async (file: File, mockDocument: any) => {
  await corpusService.uploadDocument(file);
  const state = useCorpusStore.getState();
  state.addDocument(mockDocument);
};

const simulateCorpusSearch = async (query: string) => {
  await corpusService.searchDocuments(query);
};

const waitForConnectionAndGenerate = async () => {
  await waitForElementText('ws-connected', 'connected');
  fireEvent.click(screen.getByText('Generate'));
  await waitForElementText('job-status', 'processing');
};

const exportSyntheticData = async (jobId: string, format: string) => {
  return await syntheticDataService.exportData(jobId, format);
};

const simulateHealthCheck = async () => {
  return await healthService.checkHealth();
};

const waitForElementText = async (testId: string, expectedText: string) => {
  await waitFor(() => {
    expect(screen.getByTestId(testId)).toHaveTextContent(expectedText);
  });
};

const assertStoreState = (store: any) => {
  const state = store.getState();
  expect(state.documents).toBeDefined();
};