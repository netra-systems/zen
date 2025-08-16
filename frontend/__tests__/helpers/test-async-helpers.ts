/**
 * Test Async Helpers - Reusable async operations
 * Keeps test functions ≤8 lines by extracting async patterns
 */

import { useAuthStore } from '@/store/authStore';
import { useCorpusStore } from '@/store/corpusStore';

export const simulateFileUpload = async (corpusService: any, file: File, mockDocument: any) => {
  const result = await corpusService.uploadDocument(file);
  useCorpusStore.getState().addDocument(mockDocument);
  return result;
};

export const simulateCorpusSearch = async (corpusService: any, query: string) => {
  const results = await corpusService.searchDocuments(query);
  return results;
};

export const simulateOAuthCallback = async (code: string) => {
  const response = await fetch('/api/auth/google/callback', {
    method: 'POST',
    body: JSON.stringify({ code })
  });
  const data = await response.json();
  useAuthStore.getState().login(data.user, data.access_token);
  return data;
};

export const simulateSessionRestore = () => {
  const savedToken = localStorage.getItem('auth_token');
  const savedUser = localStorage.getItem('user');
  
  if (savedToken && savedUser) {
    useAuthStore.getState().login(JSON.parse(savedUser), savedToken);
  }
};

export const retryWithBackoff = async (fn: () => Promise<any>, maxRetries = 3) => {
  let lastError;
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;
      await new Promise(resolve => setTimeout(resolve, Math.pow(2, i) * 100));
    }
  }
  throw lastError;
};

export const simulateGenerationProcess = async (setJobStatus: (status: string) => void) => {
  setJobStatus('processing');
  await new Promise(resolve => setTimeout(resolve, 100));
};

export const simulateHealthCheck = async (healthService: any) => {
  const status = await healthService.checkHealth();
  return status;
};

export const simulateExportData = async (syntheticDataService: any, jobId: string, format: string) => {
  const response = await syntheticDataService.exportData(jobId, format);
  return response;
};

export const queueTask = async (task: any) => {
  return { ...task, status: 'processing' };
};

export const simulateCacheQuery = async (llmCacheService: any, prompt: string, model: string) => {
  const response = await llmCacheService.query(prompt, model);
  return response;
};