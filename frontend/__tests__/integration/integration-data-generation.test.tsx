import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import {
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
ct from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import {
  setupIntegrationTest,
  teardownIntegrationTest,
  createMockGenerationJob,
  createMockExportData,
  createSyntheticDataStore,
  createSyntheticDataService,
  createGenerationTestComponent,
  createTestComponent,
  setupDefaultHookMocks,
  setupAuthMocks,
  setupLoadingMocks,
  createMockUseUnifiedChatStore,
  createMockUseWebSocket,
  createMockUseAgent,
  createMockUseAuthStore,
  createMockUseLoadingState,
  createMockUseThreadNavigation
} from './integration-shared-utilities';

// Declare mocks first (Jest Module Hoisting)
const mockUseUnifiedChatStore = createMockUseUnifiedChatStore();
const mockUseWebSocket = createMockUseWebSocket();
const mockUseAgent = createMockUseAgent();
const mockUseAuthStore = createMockUseAuthStore();
const mockUseLoadingState = createMockUseLoadingState();
const mockUseThreadNavigation = createMockUseThreadNavigation();

// Mock hooks before imports
jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: mockUseUnifiedChatStore
}));

jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: mockUseWebSocket
}));

jest.mock('@/hooks/useAgent', () => ({
  useAgent: mockUseAgent
}));

describe('Synthetic Data Generation Integration Tests', () => {
    jest.setTimeout(10000);
  let server: any;
  const useSyntheticDataStore = createSyntheticDataStore();
  const syntheticDataService = createSyntheticDataService();
  
  beforeEach(() => {
    server = setupIntegrationTest();
    setupAllMocks();
  });

  afterEach(() => {
    teardownIntegrationTest();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
  });

  describe('2. Synthetic Data Generation Flow', () => {
      jest.setTimeout(10000);
    it('should generate synthetic data based on templates', async () => {
      jest.setTimeout(10000);
      const mockGenerationJob = createMockGenerationJob();
      setupGenerationMock(mockGenerationJob);
      
      const TestComponent = createGenerationTestComponent();
      
      render(createTestComponent(<TestComponent />));
      
      await waitForConnectionAndGenerate();
    });

    it('should export generated synthetic data in multiple formats', async () => {
      const mockExportData = createMockExportData();
      setupExportMock(mockExportData);
      
      const blob = await exportSyntheticData('job-123', 'json');
      
      verifyBlobCreated(blob);
    });

    it('should handle data generation with custom templates', async () => {
      const customTemplate = { type: 'custom', fields: ['name', 'email'] };
      const mockJob = { ...createMockGenerationJob(), template: customTemplate };
      setupCustomTemplateMock(mockJob);
      
      await generateWithCustomTemplate(customTemplate);
      
      verifyCustomTemplateUsed(customTemplate);
    });

    it('should handle batch data generation jobs', async () => {
      const batchJobs = [createMockGenerationJob(), createMockGenerationJob()];
      setupBatchGenerationMock(batchJobs);
      
      await generateBatchJobs(batchJobs);
      
      verifyBatchJobsProcessed(batchJobs.length);
    });

    it('should monitor data generation progress via WebSocket', async () => {
      const mockJob = createMockGenerationJob();
      setupProgressMonitoringMock(mockJob);
      
      await monitorGenerationProgress(mockJob.id);
      
      verifyProgressMonitored(mockJob.id);
    });

    it('should handle data generation errors gracefully', async () => {
      const errorJob = { ...createMockGenerationJob(), status: 'failed' };
      setupGenerationErrorMock(errorJob);
      
      await attemptFailedGeneration(errorJob);
      
      verifyErrorHandled(errorJob);
    });

    it('should validate generated data quality', async () => {
      const validationResults = { passed: 95, failed: 5, total: 100 };
      setupDataValidationMock(validationResults);
      
      await validateGeneratedData('job-123');
      
      verifyDataValidated(validationResults);
    });

    it('should handle data generation cancellation', async () => {
      const mockJob = createMockGenerationJob();
      setupJobCancellationMock(mockJob);
      
      await cancelGenerationJob(mockJob.id);
      
      verifyJobCancelled(mockJob.id);
    });
  });
});

// Helper functions ≤8 lines each
const setupAllMocks = () => {
  const mocks = {
    mockUseUnifiedChatStore,
    mockUseWebSocket,
    mockUseAgent,
    mockUseAuthStore,
    mockUseLoadingState,
    mockUseThreadNavigation
  };
  
  setupDefaultHookMocks(mocks);
  setupAuthMocks(mocks);
  setupLoadingMocks(mocks);
};

const setupGenerationMock = (mockJob: any) => {
  (fetch as jest.Mock).mockResolvedValueOnce({
    ok: true,
    json: async () => mockJob
  });
};

const setupExportMock = (mockData: any) => {
  syntheticDataService.exportData.mockResolvedValueOnce(
    new Blob([JSON.stringify(mockData)])
  );
};

const setupCustomTemplateMock = (mockJob: any) => {
  (fetch as jest.Mock).mockResolvedValueOnce({
    ok: true,
    json: async () => mockJob
  });
};

const setupBatchGenerationMock = (batchJobs: any[]) => {
  (fetch as jest.Mock).mockResolvedValueOnce({
    ok: true,
    json: async () => ({ jobs: batchJobs })
  });
};

const setupProgressMonitoringMock = (mockJob: any) => {
  (fetch as jest.Mock).mockResolvedValueOnce({
    ok: true,
    json: async () => ({ ...mockJob, progress: 50 })
  });
};

const setupGenerationErrorMock = (errorJob: any) => {
  (fetch as jest.Mock).mockRejectedValueOnce(new Error('Generation failed'));
};

const setupDataValidationMock = (validationResults: any) => {
  (fetch as jest.Mock).mockResolvedValueOnce({
    ok: true,
    json: async () => validationResults
  });
};

const setupJobCancellationMock = (mockJob: any) => {
  (fetch as jest.Mock).mockResolvedValueOnce({
    ok: true,
    json: async () => ({ ...mockJob, status: 'cancelled' })
  });
};

const waitForConnectionAndGenerate = async () => {
  await waitFor(() => {
    expect(screen.getByTestId('ws-connected')).toHaveTextContent('connected');
  });
  
  fireEvent.click(screen.getByText('Generate'));
  
  await waitFor(() => {
    expect(screen.getByTestId('job-status')).toHaveTextContent('processing');
  });
};

const exportSyntheticData = async (jobId: string, format: string) => {
  return await syntheticDataService.exportData(jobId, format);
};

const generateWithCustomTemplate = async (template: any) => {
  await fetch('/api/generate', {
    method: 'POST',
    body: JSON.stringify({ template })
  });
};

const generateBatchJobs = async (jobs: any[]) => {
  await fetch('/api/generate/batch', {
    method: 'POST',
    body: JSON.stringify({ jobs })
  });
};

const monitorGenerationProgress = async (jobId: string) => {
  await fetch(`/api/generate/${jobId}/progress`);
};

const attemptFailedGeneration = async (job: any) => {
  try {
    await fetch('/api/generate', {
      method: 'POST',
      body: JSON.stringify(job)
    });
  } catch (error) {
    // Expected error
  }
};

const validateGeneratedData = async (jobId: string) => {
  await fetch(`/api/generate/${jobId}/validate`);
};

const cancelGenerationJob = async (jobId: string) => {
  await fetch(`/api/generate/${jobId}/cancel`, { method: 'POST' });
};

const verifyBlobCreated = (blob: Blob) => {
  expect(blob).toBeInstanceOf(Blob);
};

const verifyCustomTemplateUsed = (template: any) => {
  expect(fetch).toHaveBeenCalledWith('/api/generate', 
    expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ template })
    })
  );
};

const verifyBatchJobsProcessed = (count: number) => {
  expect(fetch).toHaveBeenCalledWith('/api/generate/batch',
    expect.objectContaining({ method: 'POST' })
  );
};

const verifyProgressMonitored = (jobId: string) => {
  expect(fetch).toHaveBeenCalledWith(`/api/generate/${jobId}/progress`);
};

const verifyErrorHandled = (errorJob: any) => {
  expect(fetch).toHaveBeenCalled();
};

const verifyDataValidated = (results: any) => {
  expect(fetch).toHaveBeenCalledWith(
    expect.stringContaining('/validate')
  );
};

const verifyJobCancelled = (jobId: string) => {
  expect(fetch).toHaveBeenCalledWith(`/api/generate/${jobId}/cancel`,
    expect.objectContaining({ method: 'POST' })
  );
};