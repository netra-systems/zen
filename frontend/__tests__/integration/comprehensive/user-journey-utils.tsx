/**
 * Shared Test Utilities for User Journey Tests
 * ULTRA DEEP THINK: Module-based architecture - Test utilities extracted for 450-line compliance
 */

import React from 'react';
import {
  render, waitFor, screen, fireEvent, act,
  setupTestEnvironment, cleanupTestEnvironment,
  createMockWebSocketServer, createWebSocketMessage,
  simulateNetworkDelay, createMockApiResponse,
  TEST_TIMEOUTS, WS
} from './test-utils';

// Apply Next.js navigation mock
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    refresh: jest.fn(),
    back: jest.fn(),
    forward: jest.fn(),
    pathname: '/',
    query: {},
    asPath: '/',
  }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
}));

// File validation utilities
export const validateFileSize = (file: File) => {
  if (file.size > 10 * 1024 * 1024) {
    throw new Error('File size must be less than 10MB');
  }
};

export const validateFileType = (file: File) => {
  if (!file.name.endsWith('.json')) {
    throw new Error('Only JSON files are supported');
  }
};

// Workload data utilities
export const createWorkloadData = (file: File, content: any) => {
  return {
    name: file.name,
    size: file.size,
    content,
    uploadedAt: new Date().toISOString()
  };
};

export const parseFileContent = (file: File, setWorkloadData: Function, setStep: Function, setErrors: Function) => {
  return new Promise<void>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const content = JSON.parse(e.target?.result as string);
        setWorkloadData(createWorkloadData(file, content));
        setStep('analyze');
        resolve();
      } catch (parseError) {
        setErrors(['Invalid JSON format in uploaded file']);
        reject(parseError);
      }
    };
    reader.readAsText(file);
  });
};

// Mock optimizations creation
export const createMockOptimizations = () => {
  return [
    {
      id: '1',
      type: 'model',
      title: 'Model Optimization',
      recommendation: 'Switch to GPT-3.5 for 40% cost reduction',
      impact: { cost: -40, latency: 0, accuracy: -2 },
      priority: 'high'
    },
    {
      id: '2',
      type: 'caching',
      title: 'Response Caching',
      recommendation: 'Enable response caching for repeated queries',
      impact: { cost: -25, latency: -50, accuracy: 0 },
      priority: 'medium'
    },
    {
      id: '3',
      type: 'batching',
      title: 'Request Batching',
      recommendation: 'Batch similar requests together',
      impact: { cost: -15, latency: -30, accuracy: 0 },
      priority: 'low'
    }
  ];
};

// Analysis simulation utilities
export const simulateAnalysisPhases = async (setProgress: Function) => {
  const phases = ['Parsing workload', 'Analyzing patterns', 'Identifying bottlenecks', 'Computing optimizations'];
  for (let i = 0; i < phases.length; i++) {
    await simulateNetworkDelay(200);
    setProgress(((i + 1) / phases.length) * 100);
  }
};

// Impact calculation utilities
export const calculateTotalImpact = (selectedOptimizations: any[]) => {
  return selectedOptimizations.reduce(
    (acc, opt) => ({
      cost: acc.cost + opt.impact.cost,
      latency: acc.latency + opt.impact.latency,
      accuracy: acc.accuracy + opt.impact.accuracy
    }),
    { cost: 0, latency: 0, accuracy: 0 }
  );
};

export const createResults = (selectedOptimizations: any[], optimizations: any[], totalImpact: any) => {
  return {
    appliedOptimizations: selectedOptimizations.length,
    totalOptimizations: optimizations.length,
    costReduction: Math.abs(totalImpact.cost),
    latencyImprovement: Math.abs(totalImpact.latency),
    accuracyChange: totalImpact.accuracy,
    estimatedMonthlySavings: Math.abs(totalImpact.cost) * 100,
    completedAt: new Date().toISOString()
  };
};

// Optimization application simulation
export const simulateOptimizationApplication = async (selectedOptimizations: any[], setProgress: Function) => {
  for (let i = 0; i < selectedOptimizations.length; i++) {
    await simulateNetworkDelay(300);
    setProgress(((i + 1) / selectedOptimizations.length) * 100);
  }
};

// WebSocket message handlers
export const handleUserJoined = (message: any, setUsers: Function) => {
  setUsers((prev: Map<string, any>) => new Map(prev.set(message.userId, message.userData)));
};

export const handleVoteCast = (message: any, setSharedState: Function) => {
  setSharedState((prev: any) => ({
    ...prev,
    votes: new Map(prev.votes.set(message.userId, message.vote))
  }));
};

export const handleStepChange = (message: any, setSharedState: Function) => {
  setSharedState((prev: any) => ({
    ...prev,
    currentStep: message.step,
    decisions: [...prev.decisions, message.decision]
  }));
};

// Mock file creation utilities
export const createValidJsonFile = (content: any = { valid: true }) => {
  return new File([JSON.stringify(content)], 'test.json', { type: 'application/json' });
};

export const createWorkloadConfigFile = () => {
  const workloadConfig = {
    model: 'gpt-4',
    requests_per_day: 1000,
    average_tokens: 500,
    use_cases: ['chat', 'completion']
  };
  
  return new File(
    [JSON.stringify(workloadConfig)], 
    'workload.json', 
    { type: 'application/json' }
  );
};

// Test setup and teardown utilities
export const setupUserJourneyTest = () => {
  const server = createMockWebSocketServer();
  setupTestEnvironment(server);
  return server;
};

export const teardownUserJourneyTest = () => {
  cleanupTestEnvironment();
};

// Shared test expectations
export const expectSuccessfulUpload = (getByTestId: Function) => {
  expect(getByTestId('current-step')).toHaveTextContent('analyze');
};

export const expectSuccessfulAnalysis = (getByTestId: Function) => {
  expect(getByTestId('current-step')).toHaveTextContent('review');
  expect(getByTestId('processing')).toHaveTextContent('false');
};

export const expectCompletedWorkflow = (getByTestId: Function) => {
  expect(getByTestId('current-step')).toHaveTextContent('complete');
  expect(getByTestId('processing')).toHaveTextContent('false');
};

export { 
  React, render, waitFor, screen, fireEvent, act,
  setupTestEnvironment, cleanupTestEnvironment,
  createMockWebSocketServer, createWebSocketMessage,
  simulateNetworkDelay, createMockApiResponse,
  TEST_TIMEOUTS, WS
};