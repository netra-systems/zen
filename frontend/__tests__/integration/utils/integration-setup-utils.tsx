/**
 * Integration Test Setup Utilities
 * Multi-component setup for integration tests with 25-line function limit enforcement
 */

import { render, RenderResult } from '@testing-library/react';
import React from 'react';
import WS from 'jest-websocket-mock';
import { TestProviders } from '../../setup/test-providers';

// Types for test configuration
export interface IntegrationTestConfig {
  withWebSocket?: boolean;
  withAuth?: boolean;
  withAgent?: boolean;
  mockResponseDelay?: number;
}

export interface TestComponentSetup {
  component: React.ComponentType;
  props?: Record<string, any>;
  config?: IntegrationTestConfig;
}

export interface IntegrationTestContext {
  server?: WS;
  rendered?: RenderResult;
  cleanup: () => void;
}

// Create integration test context with all necessary providers
export const createIntegrationContext = (config: IntegrationTestConfig = {}): IntegrationTestContext => {
  const server = config.withWebSocket ? new WS('ws://localhost:8000/ws') : undefined;
  
  const cleanup = () => {
    if (server) {
      WS.clean();
    }
  };
  
  return { server, cleanup };
};

// Setup test environment with providers and mocks
export const setupIntegrationTest = (setup: TestComponentSetup): IntegrationTestContext => {
  const context = createIntegrationContext(setup.config);
  
  const rendered = render(
    <TestProviders>
      <setup.component {...(setup.props || {})} />
    </TestProviders>
  );
  
  return { ...context, rendered };
};

// Create mock store collection for integration tests
export const createMockStoreCollection = () => ({
  authStore: createAuthStoreMock(),
  chatStore: createChatStoreMock(),
  webSocketStore: createWebSocketStoreMock(),
  agentStore: createAgentStoreMock()
});

// Individual store mock factories (≤8 lines each)
const createAuthStoreMock = () => ({
  isAuthenticated: true,
  user: { id: '1', email: 'test@example.com' },
  token: 'mock-token',
  login: jest.fn(),
  logout: jest.fn()
});

const createChatStoreMock = () => ({
  messages: [],
  threads: [],
  addMessage: jest.fn(),
  updateThread: jest.fn(),
  fastLayerData: null
});

const createWebSocketStoreMock = () => ({
  sendMessage: jest.fn(),
  isConnected: true,
  connectionState: 'connected',
  lastMessage: null
});

const createAgentStoreMock = () => ({
  isProcessing: false,
  sendMessage: jest.fn(),
  activeAgent: null,
  processingQueue: []
});

// Global test state management
export const resetIntegrationTestState = () => {
  jest.clearAllMocks();
  localStorage.clear();
  sessionStorage.clear();
};

// Mock fetch for integration tests
export const setupIntegrationFetch = (responses: Record<string, any> = {}) => {
  const defaultResponse = { ok: true, json: async () => ({}) };
  
  global.fetch = jest.fn().mockImplementation((url: string) => {
    return Promise.resolve(responses[url] || defaultResponse);
  });
};

// Setup integration test timing controls
export const createTestTimingControls = () => ({
  fastTimeout: 100,
  normalTimeout: 1000,
  slowTimeout: 5000,
  cleanup: () => jest.useRealTimers()
});

// Integration test assertion helpers
export const createIntegrationAssertions = (rendered: RenderResult) => ({
  expectElementWithText: (testId: string, text: string) => {
    expect(rendered.getByTestId(testId)).toHaveTextContent(text);
  },
  expectElementExists: (testId: string) => {
    expect(rendered.getByTestId(testId)).toBeInTheDocument();
  }
});