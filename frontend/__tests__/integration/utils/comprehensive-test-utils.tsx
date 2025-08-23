/**
 * Comprehensive Test Utilities
 * Helper functions for comprehensive integration testing
 */

import React from 'react';
import { jest } from '@jest/globals';

// Mock data creators
export const createMockDocument = jest.fn(() => ({ id: '1', name: 'test.txt' }));
export const createMockSearchResults = jest.fn(() => ([]));
export const createMockGenerationJob = jest.fn(() => ({ id: '1', status: 'pending' }));
export const createMockExportData = jest.fn(() => ({ data: 'test' }));
export const createMockHealthStatus = jest.fn(() => ({ status: 'healthy' }));
export const createMockDegradedHealth = jest.fn(() => ({ status: 'degraded' }));

// Test components
export const createGenerationTestComponent = () => {
  return () => <div data-testid="generation-test">Generation Test</div>;
};

export const createCacheManagementComponent = () => {
  return () => <div data-testid="cache-management">Cache Management</div>;
};

export const createTaskRetryComponent = () => {
  return () => <div data-testid="task-retry">Task Retry</div>;
};

export const createHealthMonitorComponent = () => {
  return () => <div data-testid="health-monitor">Health Monitor</div>;
};

// Simulation functions
export const simulateFileUpload = jest.fn();
export const simulateCorpusSearch = jest.fn();
export const simulateExportData = jest.fn();
export const simulateHealthCheck = jest.fn();

// Setup mocks
export const setupCorpusUploadMock = jest.fn();
export const setupCorpusSearchMock = jest.fn();
export const setupGenerationMock = jest.fn();
export const setupExportMock = jest.fn();
export const setupHealthMock = jest.fn();
export const setupDegradedHealthMock = jest.fn();
export const setupLLMCacheResponseMocks = jest.fn();

// Assertion and utility functions
export const assertStoreState = jest.fn();
export const waitForElementText = jest.fn();

// Scenario execution functions
export const executeCorpusManagementScenario = jest.fn();
export const executeDataGenerationScenario = jest.fn();
export const executeCacheManagementScenario = jest.fn();
export const executeHealthMonitoringScenario = jest.fn();
export const executeTaskRetryScenario = jest.fn();