// ============================================================================
// COMPREHENSIVE TEST UTILS - UNIFIED EXPORTS
// ============================================================================
// This file provides a single import point for all test utilities to ensure
// consistent usage across all test files.
// ============================================================================

// Import and setup custom matchers
import './comprehensive-matchers';

// Export all factories
export * from './comprehensive-test-factories';

// Export all helpers
export * from './comprehensive-test-helpers';

// Re-export commonly used testing library functions
export {
  render,
  screen,
  fireEvent,
  waitFor,
  waitForElementToBeRemoved,
  within,
  getByRole,
  getByText,
  getByTestId,
  getByLabelText,
  queryByRole,
  queryByText,
  queryByTestId,
  queryByLabelText,
  findByRole,
  findByText,
  findByTestId,
  findByLabelText,
  act,
} from '@testing-library/react';

export { default as userEvent } from '@testing-library/user-event';

// Export Jest globals for convenience
export { 
  expect,
  describe,
  it,
  test,
  beforeAll,
  beforeEach,
  afterAll,
  afterEach,
  jest
} from '@jest/globals';

// ============================================================================
// QUICK SETUP FUNCTIONS
// ============================================================================
import { 
  renderWithProviders, 
  renderAuthenticatedComponent, 
  renderUnauthenticatedComponent,
  renderWithLoading,
  renderWithError,
  createUserEvent,
  setupTestEnvironment,
  cleanupTestEnvironment,
  createMockUser,
  createMockThread,
  createMockMessage,
  createCompleteTestScenario,
  createErrorTestScenario
} from './comprehensive-test-helpers';

import {
  createMockAuthState,
  createMockChatState,
  createMockMCPState
} from './comprehensive-test-factories';

// Quick setup function for common test scenarios
export const quickSetup = {
  // Basic rendering
  render: renderWithProviders,
  renderAuth: renderAuthenticatedComponent,
  renderNoAuth: renderUnauthenticatedComponent,
  renderLoading: renderWithLoading,
  renderError: renderWithError,
  
  // User interactions
  user: createUserEvent,
  
  // Test data
  mockUser: createMockUser,
  mockThread: createMockThread,
  mockMessage: createMockMessage,
  completeScenario: createCompleteTestScenario,
  errorScenario: createErrorTestScenario,
  
  // State
  authState: createMockAuthState,
  chatState: createMockChatState,
  mcpState: createMockMCPState,
  
  // Environment
  setup: setupTestEnvironment,
  cleanup: cleanupTestEnvironment,
};

// ============================================================================
// COMMON TEST PATTERNS
// ============================================================================
export const testPatterns = {
  // Authentication flow test
  authFlow: (component: React.ReactElement) => ({
    unauthenticated: () => renderUnauthenticatedComponent(component),
    authenticated: () => renderAuthenticatedComponent(component),
    loading: () => renderWithLoading(component),
    error: (error: string) => renderWithError(component, error)
  }),
  
  // CRUD operations test
  crudOperations: {
    create: (data: any) => ({ type: 'create', data }),
    read: (id: string) => ({ type: 'read', id }),
    update: (id: string, data: any) => ({ type: 'update', id, data }),
    delete: (id: string) => ({ type: 'delete', id })
  },
  
  // Error handling test
  errorHandling: {
    networkError: () => ({ error: 'Network Error', code: 'NETWORK_ERROR' }),
    authError: () => ({ error: 'Authentication Failed', code: 'AUTH_ERROR' }),
    validationError: (field: string) => ({ error: `Validation Error: ${field}`, code: 'VALIDATION_ERROR' }),
    serverError: () => ({ error: 'Internal Server Error', code: 'SERVER_ERROR' })
  },
  
  // WebSocket test patterns
  websocket: {
    connected: () => ({ status: 'OPEN', readyState: 1 }),
    connecting: () => ({ status: 'CONNECTING', readyState: 0 }),
    disconnected: () => ({ status: 'CLOSED', readyState: 3 }),
    error: (error: string) => ({ status: 'CLOSED', error, readyState: 3 })
  }
};

// ============================================================================
// COMMON ASSERTIONS
// ============================================================================
export const commonAssertions = {
  // DOM assertions
  isVisible: (element: HTMLElement | null) => expect(element).toBeVisible(),
  hasText: (element: HTMLElement | null, text: string) => expect(element).toHaveTextContent(text),
  hasClass: (element: HTMLElement | null, className: string) => expect(element).toHaveClass(className),
  isEnabled: (element: HTMLElement | null) => expect(element).toBeEnabled(),
  isDisabled: (element: HTMLElement | null) => expect(element).toBeDisabled(),
  
  // Form assertions
  isValidForm: (form: HTMLElement) => expect(form).toHaveValidFormData(),
  hasValue: (input: HTMLElement, value: string) => expect(input).toHaveValue(value),
  isChecked: (checkbox: HTMLElement) => expect(checkbox).toBeChecked(),
  
  // State assertions
  isAuthenticated: (state: any) => expect(state).toBeAuthenticated(),
  hasAuthToken: (state: any) => expect(state).toHaveAuthToken(),
  isLoading: (element: HTMLElement) => expect(element).toBeLoadingState(),
  isError: (element: HTMLElement) => expect(element).toBeErrorState(),
  
  // API assertions
  calledAPI: (mockFn: jest.Mock, endpoint: string, method?: string) => 
    expect(mockFn).toHaveCalledAPI(endpoint, method),
  hasAPIResponse: (response: any, expected: any) => expect(response).toHaveAPIResponse(expected),
  hasAPIError: (error: any, message: string) => expect(error).toHaveAPIError(message),
  
  // WebSocket assertions
  hasWSConnection: (ws: any) => expect(ws).toHaveWebSocketConnection(),
  receivedWSMessage: (ws: any, message: any) => expect(ws).toHaveReceivedWebSocketMessage(message),
  
  // MCP assertions
  hasMCPServer: (state: any, serverName: string) => expect(state).toHaveMCPServer(serverName),
  hasMCPTool: (state: any, toolName: string) => expect(state).toHaveMCPTool(toolName),
  executedMCPTool: (state: any, toolName: string) => expect(state).toHaveExecutedMCPTool(toolName)
};

// ============================================================================
// DEFAULT EXPORTS FOR EASY IMPORTING
// ============================================================================
export default {
  ...quickSetup,
  patterns: testPatterns,
  assertions: commonAssertions
};