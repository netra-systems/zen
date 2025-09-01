/**
 * WebSocket Test Utilities for React Components
 * 
 * Provides React-specific utilities for testing components that use WebSocket connections.
 * Works with the comprehensive WebSocket mocks defined in jest.setup.js.
 */

import React from 'react';
import { render, RenderOptions, RenderResult } from '@testing-library/react';
import { webSocketTestHelper, WebSocketTestHelper } from '../helpers/websocket-test-helpers';

// Mock providers that might be needed for WebSocket testing
const MockWebSocketProvider: React.FC<{ children: React.ReactNode; value?: any }> = ({ children, value }) => {
  const mockContextValue = {
    status: 'OPEN',
    messages: [],
    sendMessage: jest.fn(),
    sendOptimisticMessage: jest.fn(() => ({
      id: 'mock-optimistic-id',
      content: 'mock-content',
      type: 'user',
      role: 'user',
      timestamp: Date.now(),
      tempId: 'mock-temp-id',
      optimisticTimestamp: Date.now(),
      contentHash: 'mock-hash',
      reconciliationStatus: 'pending',
      sequenceNumber: 1,
      retryCount: 0
    })),
    reconciliationStats: {
      totalOptimistic: 0,
      totalConfirmed: 0,
      totalFailed: 0,
      totalTimeout: 0,
      averageReconciliationTime: 0,
      currentPendingCount: 0
    },
    ...value
  };

  return <div data-testid="mock-websocket-provider">{children}</div>;
};

interface WebSocketTestRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  websocketConfig?: {
    connected?: boolean;
    messages?: any[];
    status?: 'CONNECTING' | 'OPEN' | 'CLOSING' | 'CLOSED';
    autoConnect?: boolean;
    enableMocking?: boolean;
  };
}

/**
 * Enhanced render function that sets up WebSocket mocking for component tests
 */
export function renderWithWebSocket(
  ui: React.ReactElement,
  options: WebSocketTestRenderOptions = {}
): RenderResult & { websocketHelper: WebSocketTestHelper } {
  const {
    websocketConfig = {},
    ...renderOptions
  } = options;

  const {
    connected = true,
    messages = [],
    status = 'OPEN',
    autoConnect = true,
    enableMocking = true
  } = websocketConfig;

  // Set up WebSocket mock state if mocking is enabled
  if (enableMocking && global.WebSocket) {
    // The global WebSocket mock is already set up in jest.setup.js
    // Here we just ensure it behaves as expected for this test
  }

  // Create wrapper component if needed
  const AllTheProviders: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    return (
      <MockWebSocketProvider value={{ status, messages }}>
        {children}
      </MockWebSocketProvider>
    );
  };

  const result = render(ui, { wrapper: AllTheProviders, ...renderOptions });

  return {
    ...result,
    websocketHelper: webSocketTestHelper
  };
}

/**
 * WebSocket test setup utilities
 */
export class WebSocketTestSetup {
  private static mockInstances: any[] = [];

  /**
   * Set up WebSocket mock for a test
   */
  static setup(config: { 
    autoConnect?: boolean; 
    initialState?: 'CONNECTING' | 'OPEN' | 'CLOSED';
    url?: string;
  } = {}): any {
    const {
      autoConnect = true,
      initialState = 'OPEN',
      url = 'ws://localhost:8000/ws'
    } = config;

    const mockWs = webSocketTestHelper.createMockWebSocket(url);
    this.mockInstances.push(mockWs);

    if (autoConnect && initialState === 'OPEN') {
      setTimeout(() => webSocketTestHelper.simulateOpen(mockWs), 0);
    }

    return mockWs;
  }

  /**
   * Clean up all WebSocket mocks created in this test
   */
  static cleanup(): void {
    this.mockInstances.forEach(ws => {
      if (ws && ws.cleanup && typeof ws.cleanup === 'function') {
        ws.cleanup();
      }
    });
    this.mockInstances = [];
  }

  /**
   * Wait for all pending WebSocket operations
   */
  static async waitForOperations(timeout = 100): Promise<void> {
    return new Promise(resolve => {
      setTimeout(resolve, timeout);
    });
  }
}

/**
 * WebSocket test scenarios - common test patterns
 */
export class WebSocketTestScenarios {
  /**
   * Simulate successful connection flow
   */
  static async simulateSuccessfulConnection(ws?: any): Promise<void> {
    const target = ws || webSocketTestHelper.createMockWebSocket();
    webSocketTestHelper.simulateOpen(target);
    await WebSocketTestSetup.waitForOperations(10);
    return target;
  }

  /**
   * Simulate connection failure
   */
  static async simulateConnectionFailure(ws?: any, error = 'Connection failed'): Promise<void> {
    const target = ws || webSocketTestHelper.createMockWebSocket();
    webSocketTestHelper.simulateError(error, target);
    await WebSocketTestSetup.waitForOperations(10);
    return target;
  }

  /**
   * Simulate message exchange
   */
  static async simulateMessageExchange(
    messages: { send?: any; receive?: any }[],
    ws?: any
  ): Promise<void> {
    const target = ws || webSocketTestHelper.createMockWebSocket();
    
    // Ensure connection is open first
    if (webSocketTestHelper.getReadyState(target) !== 1) {
      webSocketTestHelper.simulateOpen(target);
      await WebSocketTestSetup.waitForOperations(10);
    }

    for (const message of messages) {
      if (message.send) {
        target.send(message.send);
      }
      if (message.receive) {
        webSocketTestHelper.simulateMessage(message.receive, target);
      }
      await WebSocketTestSetup.waitForOperations(10);
    }

    return target;
  }

  /**
   * Simulate connection loss and reconnection
   */
  static async simulateConnectionLossAndReconnect(ws?: any): Promise<void> {
    const target = ws || webSocketTestHelper.createMockWebSocket();
    
    // Start connected
    webSocketTestHelper.simulateOpen(target);
    await WebSocketTestSetup.waitForOperations(10);
    
    // Lose connection
    webSocketTestHelper.simulateClose({ code: 1006, reason: 'Connection lost' }, target);
    await WebSocketTestSetup.waitForOperations(50);
    
    // Reconnect
    webSocketTestHelper.simulateOpen(target);
    await WebSocketTestSetup.waitForOperations(10);
    
    return target;
  }
}

/**
 * Hook for using WebSocket test utilities in test components
 */
export function useWebSocketTestUtils() {
  return {
    helper: webSocketTestHelper,
    setup: WebSocketTestSetup,
    scenarios: WebSocketTestScenarios
  };
}

/**
 * Test data factories for WebSocket messages
 */
export const WebSocketTestData = {
  /**
   * Create a mock chat message
   */
  createChatMessage(overrides: any = {}) {
    return {
      type: 'message',
      data: {
        id: 'msg-123',
        content: 'Hello, this is a test message',
        role: 'user',
        timestamp: Date.now(),
        ...overrides
      }
    };
  },

  /**
   * Create a mock agent response
   */
  createAgentResponse(overrides: any = {}) {
    return {
      type: 'agent_response',
      data: {
        id: 'response-123',
        content: 'This is an agent response',
        role: 'assistant',
        timestamp: Date.now(),
        ...overrides
      }
    };
  },

  /**
   * Create a mock system status message
   */
  createSystemMessage(overrides: any = {}) {
    return {
      type: 'system',
      data: {
        status: 'connected',
        message: 'System is operational',
        timestamp: Date.now(),
        ...overrides
      }
    };
  },

  /**
   * Create a mock error message
   */
  createErrorMessage(overrides: any = {}) {
    return {
      type: 'error',
      data: {
        code: 'GENERIC_ERROR',
        message: 'An error occurred',
        timestamp: Date.now(),
        ...overrides
      }
    };
  }
};

// Export commonly used utilities
export { webSocketTestHelper, WebSocketTestHelper } from '../helpers/websocket-test-helpers';