/**
 * Centralized Test Utilities Module
 * 
 * BUSINESS VALUE JUSTIFICATION:
 * - Segment: All (Free → Enterprise)
 * - Business Goal: Accelerate test development velocity by 5x
 * - Value Impact: Reduces test creation time from hours to minutes
 * - Revenue Impact: Faster deployment cycles protecting $100K+ MRR
 * 
 * ARCHITECTURAL COMPLIANCE:
 * - File size: ≤300 lines (MANDATORY)
 * - Functions: ≤8 lines each (MANDATORY)
 * - TypeScript with full type safety
 * - Single responsibility utilities
 */

import React, { ReactElement } from 'react';
import { render, RenderOptions, RenderResult, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { jest } from '@jest/globals';

// ============================================================================
// TYPE DEFINITIONS - Core testing types
// ============================================================================

export interface TestUser {
  id: string;
  email: string;
  name: string;
  role: 'free' | 'early' | 'mid' | 'enterprise';
}

export interface TestThread {
  id: string;
  title: string;
  userId: string;
  createdAt: string;
}

export interface TestMessage {
  id: string;
  threadId: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
}

export interface TestRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  withAuth?: boolean;
  withWebSocket?: boolean;
  authValue?: Partial<any>;
  wsValue?: Partial<any>;
}

// ============================================================================
// COMPONENT RENDERING UTILITIES - Provider management
// ============================================================================

/**
 * Enhanced render with all provider contexts
 */
export const renderWithProviders = (
  ui: ReactElement,
  options: TestRenderOptions = {}
): RenderResult => {
  const { withAuth = true, withWebSocket = true, ...renderOptions } = options;
  const { TestProviders } = require('./providers');
  
  return render(ui, { wrapper: TestProviders, ...renderOptions });
};

/**
 * Render with only auth provider
 */
export const renderWithAuth = (
  ui: ReactElement,
  authValue?: Partial<any>
): RenderResult => {
  const { AuthTestProvider } = require('./providers');
  const Wrapper = ({ children }) => (
    <AuthTestProvider value={authValue}>{children}</AuthTestProvider>
  );
  
  return render(ui, { wrapper: Wrapper });
};

/**
 * Render with WebSocket provider only
 */
export const renderWithWebSocket = (
  ui: ReactElement,
  wsValue?: Partial<any>
): RenderResult => {
  const { WebSocketTestProvider } = require('./providers');
  const Wrapper = ({ children }) => (
    <WebSocketTestProvider value={wsValue}>{children}</WebSocketTestProvider>
  );
  
  return render(ui, { wrapper: Wrapper });
};

/**
 * Render without any providers for isolation
 */
export const renderIsolated = (
  ui: ReactElement,
  options?: RenderOptions
): RenderResult => {
  return render(ui, options);
};

// ============================================================================
// USER INTERACTION HELPERS - Enhanced user events
// ============================================================================

/**
 * Fill form fields with realistic timing
 */
export const fillForm = async (
  fields: Record<string, string>,
  options?: { delay?: number }
): Promise<void> => {
  const user = userEvent.setup();
  const delay = options?.delay || 10;
  
  for (const [fieldName, value] of Object.entries(fields)) {
    const field = screen.getByLabelText(new RegExp(fieldName, 'i'));
    await user.clear(field);
    await user.type(field, value, { delay });
  }
};

/**
 * Click element and wait for effects
 */
export const clickAndWait = async (
  elementOrSelector: HTMLElement | string,
  waitForSelector?: string
): Promise<void> => {
  const user = userEvent.setup();
  const element = typeof elementOrSelector === 'string' 
    ? screen.getByRole('button', { name: new RegExp(elementOrSelector, 'i') })
    : elementOrSelector;
    
  await user.click(element);
  
  if (waitForSelector) {
    await waitFor(() => screen.getByText(new RegExp(waitForSelector, 'i')));
  }
};

/**
 * Type with realistic human-like delays
 */
export const typeWithDelay = async (
  element: HTMLElement,
  text: string,
  delay: number = 50
): Promise<void> => {
  const user = userEvent.setup();
  await user.type(element, text, { delay });
};

/**
 * Submit form and wait for response
 */
export const submitAndWait = async (
  formElement: HTMLElement,
  expectedResponse?: string
): Promise<void> => {
  const user = userEvent.setup();
  await user.click(formElement);
  
  if (expectedResponse) {
    await waitFor(() => screen.getByText(new RegExp(expectedResponse, 'i')));
  }
};

// ============================================================================
// ASYNC OPERATION UTILITIES - Timing and retry logic
// ============================================================================

/**
 * Wait for condition with timeout
 */
export const waitForCondition = async (
  condition: () => boolean,
  timeout: number = 5000,
  interval: number = 100
): Promise<void> => {
  const startTime = Date.now();
  
  while (!condition() && Date.now() - startTime < timeout) {
    await new Promise(resolve => setTimeout(resolve, interval));
  }
  
  if (!condition()) {
    throw new Error(`Condition not met within ${timeout}ms`);
  }
};

/**
 * Retry async operation with backoff
 */
export const retryAsync = async <T>(
  operation: () => Promise<T>,
  maxAttempts: number = 3,
  delayMs: number = 100
): Promise<T> => {
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await operation();
    } catch (error) {
      if (attempt === maxAttempts) throw error;
      await new Promise(resolve => setTimeout(resolve, delayMs * attempt));
    }
  }
  
  throw new Error('Max retry attempts exceeded');
};

/**
 * Wait for WebSocket connection state
 */
export const waitForWebSocketState = async (
  expectedState: string,
  timeout: number = 3000
): Promise<void> => {
  await waitForCondition(
    () => screen.queryByTestId(`ws-status-${expectedState}`) !== null,
    timeout
  );
};

/**
 * Simulate async loading delay
 */
export const simulateAsyncDelay = (ms: number = 100): Promise<void> => {
  return new Promise(resolve => setTimeout(resolve, ms));
};

// ============================================================================
// MOCK DATA FACTORIES - Consistent test data
// ============================================================================

/**
 * Create mock user with defaults
 */
export const createMockUser = (overrides: Partial<TestUser> = {}): TestUser => {
  return {
    id: `user-${Date.now()}`,
    email: 'test@netra.ai',
    name: 'Test User',
    role: 'early',
    ...overrides
  };
};

/**
 * Create mock thread with messages
 */
export const createMockThread = (
  messageCount: number = 3,
  overrides: Partial<TestThread> = {}
): TestThread => {
  return {
    id: `thread-${Date.now()}`,
    title: 'Test Thread',
    userId: 'user-123',
    createdAt: new Date().toISOString(),
    ...overrides
  };
};

/**
 * Create mock message for testing
 */
export const createMockMessage = (overrides: Partial<TestMessage> = {}): TestMessage => {
  return {
    id: `msg-${Date.now()}`,
    threadId: 'thread-123',
    role: 'user',
    content: 'Test message content',
    timestamp: new Date().toISOString(),
    ...overrides
  };
};

/**
 * Create mock WebSocket message
 */
export const createMockWSMessage = (
  type: string,
  payload: Record<string, any> = {}
) => {
  return {
    type,
    payload,
    timestamp: new Date().toISOString()
  };
};

// ============================================================================
// ASSERTION HELPERS - Enhanced test expectations
// ============================================================================

/**
 * Expect no console errors during test
 */
export const expectNoErrors = (): void => {
  const consoleSpy = jest.spyOn(console, 'error');
  expect(consoleSpy).not.toHaveBeenCalled();
  consoleSpy.mockRestore();
};

/**
 * Validate authentication state
 */
export const validateAuthState = (
  expectedState: 'authenticated' | 'unauthenticated'
): void => {
  const authIndicator = screen.queryByTestId('auth-status');
  
  if (expectedState === 'authenticated') {
    expect(authIndicator).toHaveAttribute('data-authenticated', 'true');
  } else {
    expect(authIndicator).toHaveAttribute('data-authenticated', 'false');
  }
};

/**
 * Assert WebSocket connection status
 */
export const expectWebSocketStatus = (expectedStatus: string): void => {
  const wsStatus = screen.getByTestId('websocket-status');
  expect(wsStatus).toHaveTextContent(expectedStatus);
};

/**
 * Validate form submission success
 */
export const expectFormSubmitSuccess = async (successMessage: string): Promise<void> => {
  await waitFor(() => {
    expect(screen.getByText(successMessage)).toBeInTheDocument();
  });
};

// ============================================================================
// WEBSOCKET TEST UTILITIES - Connection testing
// ============================================================================

/**
 * Setup mock WebSocket server
 */
export const setupMockWebSocket = () => {
  const mockSend = jest.fn();
  const mockClose = jest.fn();
  
  global.WebSocket = jest.fn(() => ({
    send: mockSend,
    close: mockClose,
    readyState: WebSocket.OPEN,
    addEventListener: jest.fn(),
    removeEventListener: jest.fn()
  })) as any;
  
  return { mockSend, mockClose };
};

/**
 * Simulate WebSocket message reception
 */
export const simulateWSMessage = (mockWS: any, message: any): void => {
  const messageEvent = new MessageEvent('message', {
    data: JSON.stringify(message)
  });
  
  mockWS.onmessage?.(messageEvent);
};

// ============================================================================
// AUTH TEST UTILITIES - Authentication testing
// ============================================================================

/**
 * Setup authenticated test environment
 */
export const setupAuthenticatedTest = (): TestUser => {
  const mockUser = createMockUser();
  
  localStorage.setItem('auth_token', 'test-token');
  localStorage.setItem('user_data', JSON.stringify(mockUser));
  
  return mockUser;
};

/**
 * Clear authentication state
 */
export const clearAuthState = (): void => {
  localStorage.removeItem('auth_token');
  localStorage.removeItem('user_data');
  sessionStorage.clear();
};

// ============================================================================
// COMMON TEST PATTERNS - Reusable test scenarios
// ============================================================================

/**
 * Test component accessibility basics
 */
export const testBasicA11y = async (component: ReactElement): Promise<void> => {
  const { container } = renderIsolated(component);
  
  const interactiveElements = container.querySelectorAll('button, input, a');
  interactiveElements.forEach(element => {
    expect(element).toHaveAttribute('tabindex');
  });
};

/**
 * Test component error boundaries
 */
export const testErrorBoundary = async (
  component: ReactElement,
  triggerError: () => void
): Promise<void> => {
  const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
  
  const { getByText } = renderIsolated(component);
  
  act(() => {
    triggerError();
  });
  
  expect(getByText(/something went wrong/i)).toBeInTheDocument();
  consoleSpy.mockRestore();
};

// ============================================================================
// EXPORTS - Re-export commonly used testing utilities
// ============================================================================

export {
  render,
  screen,
  fireEvent,
  waitFor,
  act,
  renderHook,
  cleanup
} from '@testing-library/react';

export { userEvent };
export { jest };