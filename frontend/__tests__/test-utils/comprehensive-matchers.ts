// ============================================================================
// COMPREHENSIVE JEST MATCHERS - UNIFIED ASSERTION EXTENSIONS
// ============================================================================
// This file provides complete custom Jest matchers for all testing scenarios
// to ensure consistent and comprehensive assertions across test suites.
// ============================================================================

import { expect } from '@testing-library/jest-dom';

declare global {
  namespace jest {
    interface Matchers<R> {
      // DOM matchers
      toHaveValidFormData(): R;
      toBeLoadingState(): R;
      toBeErrorState(): R;
      toHaveCorrectAccessibility(): R;
      
      // WebSocket matchers
      toHaveWebSocketConnection(): R;
      toHaveReceivedWebSocketMessage(message: any): R;
      
      // Authentication matchers
      toBeAuthenticated(): R;
      toHaveAuthToken(): R;
      toHaveUserPermissions(permissions: string[]): R;
      
      // API matchers
      toHaveCalledAPI(endpoint: string, method?: string): R;
      toHaveAPIResponse(response: any): R;
      toHaveAPIError(error: string): R;
      
      // State matchers
      toHaveStoreState(statePath: string, expectedValue: any): R;
      toHaveOptimisticMessage(messageId: string): R;
      toHaveReconciledMessage(messageId: string): R;
      
      // Performance matchers
      toRenderWithinTime(maxTime: number): R;
      toHaveMemoryLeaks(): R;
      
      // MCP matchers
      toHaveMCPServer(serverName: string): R;
      toHaveMCPTool(toolName: string): R;
      toHaveExecutedMCPTool(toolName: string): R;
    }
  }
}

// ============================================================================
// DOM AND UI MATCHERS
// ============================================================================
expect.extend({
  toHaveValidFormData(received: HTMLFormElement) {
    const inputs = received.querySelectorAll('input, textarea, select');
    const invalidInputs: HTMLElement[] = [];
    
    inputs.forEach((input: HTMLElement) => {
      if (!(input as HTMLInputElement).validity?.valid) {
        invalidInputs.push(input);
      }
    });

    const pass = invalidInputs.length === 0;
    
    return {
      pass,
      message: () => 
        pass 
          ? `Expected form to have invalid data, but all inputs are valid`
          : `Expected form to have valid data, but found ${invalidInputs.length} invalid inputs: ${invalidInputs.map(i => i.name || i.id).join(', ')}`
    };
  },

  toBeLoadingState(received: HTMLElement) {
    const hasLoadingIndicator = received.querySelector('[data-testid*="loading"], .loading, [aria-busy="true"]') !== null;
    const hasSpinner = received.querySelector('.spinner, .loading-spinner') !== null;
    const hasLoadingText = /loading|wait/i.test(received.textContent || '');
    
    const pass = hasLoadingIndicator || hasSpinner || hasLoadingText;
    
    return {
      pass,
      message: () => 
        pass 
          ? `Expected element not to be in loading state`
          : `Expected element to be in loading state (should have loading indicator, spinner, or loading text)`
    };
  },

  toBeErrorState(received: HTMLElement) {
    const hasErrorIndicator = received.querySelector('[data-testid*="error"], .error, [role="alert"]') !== null;
    const hasErrorText = /error|failed|problem/i.test(received.textContent || '');
    
    const pass = hasErrorIndicator || hasErrorText;
    
    return {
      pass,
      message: () => 
        pass 
          ? `Expected element not to be in error state`
          : `Expected element to be in error state (should have error indicator or error text)`
    };
  },

  toHaveCorrectAccessibility(received: HTMLElement) {
    const issues: string[] = [];
    
    // Check for ARIA attributes
    const interactiveElements = received.querySelectorAll('button, input, select, textarea, a[href], [role="button"], [role="link"]');
    interactiveElements.forEach((element: HTMLElement) => {
      if (!element.getAttribute('aria-label') && !element.textContent?.trim()) {
        issues.push(`Interactive element without accessible name: ${element.tagName}`);
      }
    });
    
    // Check for form labels
    const inputs = received.querySelectorAll('input, textarea, select');
    inputs.forEach((input: HTMLElement) => {
      const id = input.id;
      if (!id || !received.querySelector(`label[for="${id}"]`)) {
        issues.push(`Form input without associated label: ${input.getAttribute('name') || 'unnamed'}`);
      }
    });
    
    // Check for alt text on images
    const images = received.querySelectorAll('img');
    images.forEach((img: HTMLElement) => {
      if (!img.getAttribute('alt')) {
        issues.push(`Image without alt text: ${img.getAttribute('src') || 'no src'}`);
      }
    });
    
    const pass = issues.length === 0;
    
    return {
      pass,
      message: () => 
        pass 
          ? `Expected element to have accessibility issues`
          : `Found accessibility issues:\n${issues.join('\n')}`
    };
  }
});

// ============================================================================
// WEBSOCKET MATCHERS
// ============================================================================
expect.extend({
  toHaveWebSocketConnection(received: any) {
    const hasConnection = received && (
      received.readyState === 1 || 
      received.status === 'OPEN' ||
      received.connectionState === 'connected'
    );
    
    return {
      pass: hasConnection,
      message: () => 
        hasConnection 
          ? `Expected not to have WebSocket connection`
          : `Expected to have active WebSocket connection, but connection state is: ${received?.readyState || received?.status || 'undefined'}`
    };
  },

  toHaveReceivedWebSocketMessage(received: any, expectedMessage: any) {
    const messages = received?.messages || [];
    const hasMessage = messages.some((msg: any) => 
      JSON.stringify(msg) === JSON.stringify(expectedMessage)
    );
    
    return {
      pass: hasMessage,
      message: () => 
        hasMessage 
          ? `Expected not to have received WebSocket message: ${JSON.stringify(expectedMessage)}`
          : `Expected to have received WebSocket message: ${JSON.stringify(expectedMessage)}, but received: ${JSON.stringify(messages)}`
    };
  }
});

// ============================================================================
// AUTHENTICATION MATCHERS
// ============================================================================
expect.extend({
  toBeAuthenticated(received: any) {
    const isAuthenticated = received?.isAuthenticated === true || 
                           received?.user !== null ||
                           received?.token !== null;
    
    return {
      pass: isAuthenticated,
      message: () => 
        isAuthenticated 
          ? `Expected not to be authenticated`
          : `Expected to be authenticated, but authentication state is: ${JSON.stringify({ isAuthenticated: received?.isAuthenticated, hasUser: !!received?.user, hasToken: !!received?.token })}`
    };
  },

  toHaveAuthToken(received: any) {
    const hasToken = received?.token && typeof received.token === 'string' && received.token.length > 0;
    
    return {
      pass: hasToken,
      message: () => 
        hasToken 
          ? `Expected not to have authentication token`
          : `Expected to have authentication token, but token is: ${received?.token}`
    };
  },

  toHaveUserPermissions(received: any, expectedPermissions: string[]) {
    const userPermissions = received?.user?.permissions || [];
    const hasAllPermissions = expectedPermissions.every(permission => 
      userPermissions.includes(permission)
    );
    
    return {
      pass: hasAllPermissions,
      message: () => 
        hasAllPermissions 
          ? `Expected not to have permissions: ${expectedPermissions.join(', ')}`
          : `Expected to have permissions: ${expectedPermissions.join(', ')}, but user has: ${userPermissions.join(', ')}`
    };
  }
});

// ============================================================================
// API MATCHERS
// ============================================================================
expect.extend({
  toHaveCalledAPI(received: jest.Mock, endpoint: string, method: string = 'GET') {
    const calls = received.mock.calls;
    const matchingCall = calls.find(call => {
      const [url, options] = call;
      const urlMatches = typeof url === 'string' && url.includes(endpoint);
      const methodMatches = !options || !options.method || options.method.toUpperCase() === method.toUpperCase();
      return urlMatches && methodMatches;
    });
    
    const pass = !!matchingCall;
    
    return {
      pass,
      message: () => 
        pass 
          ? `Expected not to call API endpoint: ${method} ${endpoint}`
          : `Expected to call API endpoint: ${method} ${endpoint}, but called: ${calls.map(call => `${call[1]?.method || 'GET'} ${call[0]}`).join(', ')}`
    };
  },

  toHaveAPIResponse(received: any, expectedResponse: any) {
    const hasExpectedResponse = JSON.stringify(received?.data) === JSON.stringify(expectedResponse);
    
    return {
      pass: hasExpectedResponse,
      message: () => 
        hasExpectedResponse 
          ? `Expected not to have API response: ${JSON.stringify(expectedResponse)}`
          : `Expected API response: ${JSON.stringify(expectedResponse)}, but received: ${JSON.stringify(received?.data)}`
    };
  },

  toHaveAPIError(received: any, expectedError: string) {
    const errorMessage = received?.message || received?.error || received?.response?.data?.error;
    const hasExpectedError = errorMessage && errorMessage.includes(expectedError);
    
    return {
      pass: hasExpectedError,
      message: () => 
        hasExpectedError 
          ? `Expected not to have API error: ${expectedError}`
          : `Expected API error containing: ${expectedError}, but received error: ${errorMessage}`
    };
  }
});

// ============================================================================
// STATE MATCHERS
// ============================================================================
expect.extend({
  toHaveStoreState(received: any, statePath: string, expectedValue: any) {
    const pathParts = statePath.split('.');
    let currentValue = received;
    
    for (const part of pathParts) {
      if (currentValue && typeof currentValue === 'object') {
        currentValue = currentValue[part];
      } else {
        currentValue = undefined;
        break;
      }
    }
    
    const pass = JSON.stringify(currentValue) === JSON.stringify(expectedValue);
    
    return {
      pass,
      message: () => 
        pass 
          ? `Expected store state at ${statePath} not to be: ${JSON.stringify(expectedValue)}`
          : `Expected store state at ${statePath} to be: ${JSON.stringify(expectedValue)}, but received: ${JSON.stringify(currentValue)}`
    };
  },

  toHaveOptimisticMessage(received: any, messageId: string) {
    const messages = received?.messages || [];
    const optimisticMessage = messages.find((msg: any) => 
      msg.id === messageId && msg.reconciliationStatus === 'pending'
    );
    
    return {
      pass: !!optimisticMessage,
      message: () => 
        optimisticMessage 
          ? `Expected not to have optimistic message with ID: ${messageId}`
          : `Expected to have optimistic message with ID: ${messageId}, but found messages: ${messages.map((m: any) => `${m.id}:${m.reconciliationStatus}`).join(', ')}`
    };
  },

  toHaveReconciledMessage(received: any, messageId: string) {
    const messages = received?.messages || [];
    const reconciledMessage = messages.find((msg: any) => 
      msg.id === messageId && msg.reconciliationStatus === 'confirmed'
    );
    
    return {
      pass: !!reconciledMessage,
      message: () => 
        reconciledMessage 
          ? `Expected not to have reconciled message with ID: ${messageId}`
          : `Expected to have reconciled message with ID: ${messageId}, but found messages: ${messages.map((m: any) => `${m.id}:${m.reconciliationStatus}`).join(', ')}`
    };
  }
});

// ============================================================================
// PERFORMANCE MATCHERS
// ============================================================================
expect.extend({
  toRenderWithinTime(received: () => void, maxTime: number) {
    const startTime = performance.now();
    received();
    const endTime = performance.now();
    const renderTime = endTime - startTime;
    
    const pass = renderTime <= maxTime;
    
    return {
      pass,
      message: () => 
        pass 
          ? `Expected render time to exceed ${maxTime}ms, but rendered in ${renderTime.toFixed(2)}ms`
          : `Expected render time to be within ${maxTime}ms, but took ${renderTime.toFixed(2)}ms`
    };
  },

  toHaveMemoryLeaks(received: any) {
    // This is a simplified memory leak detection
    // In a real scenario, you'd use more sophisticated memory profiling
    const hasLeaks = received && (
      received.listeners?.length > 100 ||
      received.eventListeners?.length > 100 ||
      received.subscriptions?.length > 100
    );
    
    return {
      pass: hasLeaks,
      message: () => 
        hasLeaks 
          ? `Expected not to have memory leaks`
          : `Expected to have memory leaks, but component appears clean`
    };
  }
});

// ============================================================================
// MCP MATCHERS
// ============================================================================
expect.extend({
  toHaveMCPServer(received: any, serverName: string) {
    const servers = received?.servers || [];
    const hasServer = servers.some((server: any) => server.name === serverName);
    
    return {
      pass: hasServer,
      message: () => 
        hasServer 
          ? `Expected not to have MCP server: ${serverName}`
          : `Expected to have MCP server: ${serverName}, but found servers: ${servers.map((s: any) => s.name).join(', ')}`
    };
  },

  toHaveMCPTool(received: any, toolName: string) {
    const tools = received?.tools || [];
    const hasTool = tools.some((tool: any) => tool.name === toolName);
    
    return {
      pass: hasTool,
      message: () => 
        hasTool 
          ? `Expected not to have MCP tool: ${toolName}`
          : `Expected to have MCP tool: ${toolName}, but found tools: ${tools.map((t: any) => t.name).join(', ')}`
    };
  },

  toHaveExecutedMCPTool(received: any, toolName: string) {
    const executions = received?.executions || [];
    const hasExecution = executions.some((execution: any) => execution.tool_name === toolName);
    
    return {
      pass: hasExecution,
      message: () => 
        hasExecution 
          ? `Expected not to have executed MCP tool: ${toolName}`
          : `Expected to have executed MCP tool: ${toolName}, but found executions: ${executions.map((e: any) => e.tool_name).join(', ')}`
    };
  }
});

export {}; // Make this a module