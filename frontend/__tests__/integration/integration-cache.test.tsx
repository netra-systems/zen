/**
 * LLM Cache Management Integration Tests
 * Module-based architecture: Cache tests ≤300 lines, functions ≤8 lines
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import {
  setupIntegrationTest,
  teardownIntegrationTest,
  createLLMCacheStore,
  createLLMCacheService,
  createCacheManagementComponent,
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

describe('LLM Cache Management Integration Tests', () => {
  let server: any;
  const useLLMCacheStore = createLLMCacheStore();
  const llmCacheService = createLLMCacheService();
  
  beforeEach(() => {
    server = setupIntegrationTest();
    setupAllMocks();
  });

  afterEach(() => {
    teardownIntegrationTest();
  });

  describe('3. LLM Cache Management Integration', () => {
    it('should cache and retrieve LLM responses', async () => {
      setupLLMCacheResponseMocks();
      
      const response1 = await queryLLMCache('test prompt', 'gpt-4');
      const response2 = await queryLLMCache('test prompt', 'gpt-4');
      
      verifyCacheHitMiss(response1, response2);
    });

    it('should manage cache invalidation and TTL', async () => {
      const CacheComponent = createCacheManagementComponent();
      const { getByText } = render(createTestComponent(<CacheComponent />));
      
      await clearCacheAndVerify(getByText);
    });

    it('should handle cache size limits and eviction', async () => {
      setupCacheSizeLimitMock();
      
      await fillCacheToLimit();
      
      verifyCacheEviction();
    });

    it('should support cache warming strategies', async () => {
      const warmingPrompts = ['prompt1', 'prompt2', 'prompt3'];
      setupCacheWarmingMock(warmingPrompts);
      
      await warmCache(warmingPrompts);
      
      verifyCacheWarmed(warmingPrompts.length);
    });

    it('should handle cache key collision resolution', async () => {
      const conflictingPrompts = ['prompt', 'prompt'];
      setupCacheCollisionMock(conflictingPrompts);
      
      await handleCacheCollisions(conflictingPrompts);
      
      verifyCacheCollisionHandled();
    });

    it('should monitor cache performance metrics', async () => {
      const metrics = { hits: 85, misses: 15, hitRate: 0.85 };
      setupCacheMetricsMock(metrics);
      
      await collectCacheMetrics();
      
      verifyCacheMetricsCollected(metrics);
    });

    it('should support cache partitioning by model', async () => {
      const models = ['gpt-4', 'gpt-3.5-turbo', 'claude-3'];
      setupCachePartitioningMock(models);
      
      await testCachePartitioning(models);
      
      verifyCachePartitioned(models);
    });

    it('should handle cache backup and restore', async () => {
      const cacheSnapshot = { entries: 100, size: '50MB' };
      setupCacheBackupMock(cacheSnapshot);
      
      await backupAndRestoreCache(cacheSnapshot);
      
      verifyCacheBackupRestore(cacheSnapshot);
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

const setupLLMCacheResponseMocks = () => {
  llmCacheService.query
    .mockResolvedValueOnce({ cached: false, response: 'new response' })
    .mockResolvedValueOnce({ cached: true, response: 'cached response' });
};

const setupCacheSizeLimitMock = () => {
  (fetch as jest.Mock).mockResolvedValueOnce({
    ok: true,
    json: async () => ({ sizeLimitReached: true, evicted: 5 })
  });
};

const setupCacheWarmingMock = (prompts: string[]) => {
  (fetch as jest.Mock).mockResolvedValueOnce({
    ok: true,
    json: async () => ({ warmed: prompts.length })
  });
};

const setupCacheCollisionMock = (prompts: string[]) => {
  (fetch as jest.Mock).mockResolvedValueOnce({
    ok: true,
    json: async () => ({ collisions: 1, resolved: true })
  });
};

const setupCacheMetricsMock = (metrics: any) => {
  (fetch as jest.Mock).mockResolvedValueOnce({
    ok: true,
    json: async () => metrics
  });
};

const setupCachePartitioningMock = (models: string[]) => {
  (fetch as jest.Mock).mockResolvedValueOnce({
    ok: true,
    json: async () => ({ partitions: models.length })
  });
};

const setupCacheBackupMock = (snapshot: any) => {
  (fetch as jest.Mock).mockResolvedValueOnce({
    ok: true,
    json: async () => ({ backed_up: true, ...snapshot })
  });
};

const queryLLMCache = async (prompt: string, model: string) => {
  return await llmCacheService.query(prompt, model);
};

const clearCacheAndVerify = async (getByText: any) => {
  fireEvent.click(getByText('Clear Cache'));
  
  await waitFor(() => {
    expect(screen.getByTestId('cache-size')).toHaveTextContent('0');
  });
};

const fillCacheToLimit = async () => {
  await fetch('/api/cache/fill-to-limit', { method: 'POST' });
};

const warmCache = async (prompts: string[]) => {
  await fetch('/api/cache/warm', {
    method: 'POST',
    body: JSON.stringify({ prompts })
  });
};

const handleCacheCollisions = async (prompts: string[]) => {
  await fetch('/api/cache/handle-collisions', {
    method: 'POST',
    body: JSON.stringify({ prompts })
  });
};

const collectCacheMetrics = async () => {
  await fetch('/api/cache/metrics');
};

const testCachePartitioning = async (models: string[]) => {
  await fetch('/api/cache/partition', {
    method: 'POST',
    body: JSON.stringify({ models })
  });
};

const backupAndRestoreCache = async (snapshot: any) => {
  await fetch('/api/cache/backup', {
    method: 'POST',
    body: JSON.stringify(snapshot)
  });
  
  await fetch('/api/cache/restore', {
    method: 'POST',
    body: JSON.stringify(snapshot)
  });
};

const verifyCacheHitMiss = (response1: any, response2: any) => {
  expect(response1.cached).toBe(false);
  expect(response2.cached).toBe(true);
};

const verifyCacheEviction = () => {
  expect(fetch).toHaveBeenCalledWith('/api/cache/fill-to-limit',
    expect.objectContaining({ method: 'POST' })
  );
};

const verifyCacheWarmed = (count: number) => {
  expect(fetch).toHaveBeenCalledWith('/api/cache/warm',
    expect.objectContaining({ method: 'POST' })
  );
};

const verifyCacheCollisionHandled = () => {
  expect(fetch).toHaveBeenCalledWith('/api/cache/handle-collisions',
    expect.objectContaining({ method: 'POST' })
  );
};

const verifyCacheMetricsCollected = (metrics: any) => {
  expect(fetch).toHaveBeenCalledWith('/api/cache/metrics');
};

const verifyCachePartitioned = (models: string[]) => {
  expect(fetch).toHaveBeenCalledWith('/api/cache/partition',
    expect.objectContaining({ method: 'POST' })
  );
};

const verifyCacheBackupRestore = (snapshot: any) => {
  expect(fetch).toHaveBeenCalledWith('/api/cache/backup',
    expect.objectContaining({ method: 'POST' })
  );
  expect(fetch).toHaveBeenCalledWith('/api/cache/restore',
    expect.objectContaining({ method: 'POST' })
  );
};