// ============================================================================
// COMPREHENSIVE TEST HELPERS - UNIFIED TESTING UTILITIES
// ============================================================================
// This file provides complete helper functions for all test scenarios to
// ensure consistent test setup and execution patterns.
// ============================================================================

import React from 'react';
import { render, RenderOptions, RenderResult } from '@testing-library/react';
import { act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { 
  createMockUser, 
  createMockThread, 
  createMockMessage, 
  createMockAuthConfig,
  createMockAuthState,
  createMockChatState,
  createMockMCPState,
  MockUser,
  MockThread,
  MockMessage
} from './comprehensive-test-factories';

// ============================================================================
// PROVIDER WRAPPERS
// ============================================================================
interface MockProviderWrapperProps {
  children: React.ReactNode;
  authState?: any;
  chatState?: any;
  mcpState?: any;
  websocketState?: any;
}

export const MockProviderWrapper: React.FC<MockProviderWrapperProps> = ({
  children,
  authState = createMockAuthState(),
  chatState = createMockChatState(),
  mcpState = createMockMCPState(),
  websocketState = {}
}) => {
  // Create mock contexts
  const mockAuthContext = React.createContext(authState);
  const mockChatContext = React.createContext(chatState);
  const mockMCPContext = React.createContext(mcpState);
  const mockWebSocketContext = React.createContext({
    sendMessage: jest.fn(),
    addOptimisticMessage: jest.fn(),
    status: 'OPEN',
    messages: [],
    reconciliationStats: {
      totalOptimistic: 0,
      totalConfirmed: 0,
      totalFailed: 0,
      totalTimeout: 0,
      averageReconciliationTime: 0,
      currentPendingCount: 0
    },
    ...websocketState
  });

  return React.createElement(
    mockAuthContext.Provider,
    { value: authState },
    React.createElement(
      mockChatContext.Provider,
      { value: chatState },
      React.createElement(
        mockMCPContext.Provider,
        { value: mcpState },
        React.createElement(
          mockWebSocketContext.Provider,
          { value: { ...mockWebSocketContext.Provider.value, ...websocketState } },
          children
        )
      )
    )
  );
};

// ============================================================================
// RENDER UTILITIES
// ============================================================================
interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  authState?: any;
  chatState?: any;
  mcpState?: any;
  websocketState?: any;
  wrapperProps?: any;
}

export const renderWithProviders = (
  ui: React.ReactElement,
  {
    authState,
    chatState,
    mcpState,
    websocketState,
    wrapperProps = {},
    ...renderOptions
  }: CustomRenderOptions = {}
): RenderResult => {
  const Wrapper = ({ children }: { children?: React.ReactNode }) => (
    <MockProviderWrapper
      authState={authState}
      chatState={chatState}
      mcpState={mcpState}
      websocketState={websocketState}
      {...wrapperProps}
    >
      {children}
    </MockProviderWrapper>
  );

  return render(ui, { wrapper: Wrapper, ...renderOptions });
};

export const renderAuthenticatedComponent = (ui: React.ReactElement, options: CustomRenderOptions = {}) => {
  return renderWithProviders(ui, {
    authState: createMockAuthState({ isAuthenticated: true }),
    ...options
  });
};

export const renderUnauthenticatedComponent = (ui: React.ReactElement, options: CustomRenderOptions = {}) => {
  return renderWithProviders(ui, {
    authState: createMockAuthState({ isAuthenticated: false, user: null }),
    ...options
  });
};

export const renderWithLoading = (ui: React.ReactElement, options: CustomRenderOptions = {}) => {
  return renderWithProviders(ui, {
    authState: createMockAuthState({ loading: true }),
    chatState: createMockChatState({ isProcessing: true }),
    mcpState: createMockMCPState({ isLoading: true }),
    ...options
  });
};

export const renderWithError = (ui: React.ReactElement, error: string = 'Test error', options: CustomRenderOptions = {}) => {
  return renderWithProviders(ui, {
    authState: createMockAuthState({ error }),
    chatState: createMockChatState({ error }),
    mcpState: createMockMCPState({ error }),
    ...options
  });
};

// ============================================================================
// INTERACTION UTILITIES
// ============================================================================
export const createUserEvent = () => userEvent.setup();

export const typeInInput = async (input: HTMLElement, text: string) => {
  await act(async () => {
    const user = createUserEvent();
    await user.clear(input);
    await user.type(input, text);
  });
};

export const clickButton = async (button: HTMLElement) => {
  await act(async () => {
    const user = createUserEvent();
    await user.click(button);
  });
};

export const submitForm = async (form: HTMLElement) => {
  await act(async () => {
    const user = createUserEvent();
    await user.click(form.querySelector('button[type="submit"]') || form.querySelector('button') || form);
  });
};

export const selectOption = async (select: HTMLElement, option: string) => {
  await act(async () => {
    const user = createUserEvent();
    await user.selectOptions(select, option);
  });
};

export const pressKey = async (element: HTMLElement, key: string) => {
  await act(async () => {
    const user = createUserEvent();
    await user.type(element, `{${key}}`);
  });
};

export const pressEnter = async (element: HTMLElement) => {
  await pressKey(element, 'Enter');
};

export const pressEscape = async (element: HTMLElement) => {
  await pressKey(element, 'Escape');
};

// ============================================================================
// WAIT UTILITIES
// ============================================================================
export const waitForElement = async (callback: () => HTMLElement | null, timeout: number = 5000) => {
  const startTime = Date.now();
  
  while (Date.now() - startTime < timeout) {
    const element = callback();
    if (element) return element;
    await new Promise(resolve => setTimeout(resolve, 10));
  }
  
  throw new Error(`Element not found within ${timeout}ms`);
};

export const waitForCondition = async (condition: () => boolean, timeout: number = 5000) => {
  const startTime = Date.now();
  
  while (Date.now() - startTime < timeout) {
    if (condition()) return;
    await new Promise(resolve => setTimeout(resolve, 10));
  }
  
  throw new Error(`Condition not met within ${timeout}ms`);
};

export const waitForAsyncOperation = async (operation: () => Promise<any>, timeout: number = 5000) => {
  return new Promise(async (resolve, reject) => {
    const timeoutId = setTimeout(() => {
      reject(new Error(`Async operation timed out after ${timeout}ms`));
    }, timeout);

    try {
      const result = await operation();
      clearTimeout(timeoutId);
      resolve(result);
    } catch (error) {
      clearTimeout(timeoutId);
      reject(error);
    }
  });
};

// ============================================================================
// MOCK SETUP UTILITIES
// ============================================================================
export const setupMockFetch = (responses: Array<{ url?: string; response: any; status?: number }> = []) => {
  const mockFetch = jest.fn();
  
  responses.forEach(({ url, response, status = 200 }, index) => {
    const mockResponse = {
      ok: status >= 200 && status < 300,
      status,
      statusText: status === 200 ? 'OK' : 'Error',
      json: jest.fn().mockResolvedValue(response),
      text: jest.fn().mockResolvedValue(JSON.stringify(response)),
      headers: new Headers(),
    };

    if (url) {
      mockFetch.mockImplementation((fetchUrl: string) => {
        if (fetchUrl.includes(url)) {
          return Promise.resolve(mockResponse);
        }
        return Promise.reject(new Error(`Unexpected fetch to ${fetchUrl}`));
      });
    } else {
      if (index === 0) {
        mockFetch.mockResolvedValue(mockResponse);
      } else {
        mockFetch.mockResolvedValueOnce(mockResponse);
      }
    }
  });

  global.fetch = mockFetch;
  return mockFetch;
};

export const setupMockWebSocket = () => {
  const mockWebSocket = {
    send: jest.fn(),
    close: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    readyState: 1, // OPEN
    url: 'ws://localhost:8000',
    simulateMessage: function(data: any) {
      const event = new MessageEvent('message', { data: JSON.stringify(data) });
      this.onmessage?.(event);
    },
    simulateError: function(error: any) {
      const event = new ErrorEvent('error', { error });
      this.onerror?.(event);
    },
    simulateClose: function() {
      const event = new CloseEvent('close');
      this.onclose?.(event);
    }
  };

  global.WebSocket = jest.fn().mockImplementation(() => mockWebSocket);
  return mockWebSocket;
};

export const setupMockLocalStorage = () => {
  const store: { [key: string]: string } = {};
  
  const mockLocalStorage = {
    getItem: jest.fn((key: string) => store[key] || null),
    setItem: jest.fn((key: string, value: string) => { store[key] = value; }),
    removeItem: jest.fn((key: string) => { delete store[key]; }),
    clear: jest.fn(() => { Object.keys(store).forEach(key => delete store[key]); }),
    get length() { return Object.keys(store).length; },
    key: jest.fn((index: number) => Object.keys(store)[index] || null)
  };

  global.localStorage = mockLocalStorage;
  return mockLocalStorage;
};

// ============================================================================
// ASSERTION UTILITIES
// ============================================================================
export const expectElementToBeVisible = (element: HTMLElement | null) => {
  expect(element).toBeInTheDocument();
  expect(element).toBeVisible();
};

export const expectElementToHaveText = (element: HTMLElement | null, text: string) => {
  expect(element).toBeInTheDocument();
  expect(element).toHaveTextContent(text);
};

export const expectElementToHaveClass = (element: HTMLElement | null, className: string) => {
  expect(element).toBeInTheDocument();
  expect(element).toHaveClass(className);
};

export const expectFormToBeValid = (form: HTMLElement) => {
  expect(form).toBeInTheDocument();
  const inputs = form.querySelectorAll('input, textarea, select');
  inputs.forEach(input => {
    expect(input).toBeValid();
  });
};

export const expectApiCallToHaveBeenMade = (mockFetch: jest.Mock, url: string, method: string = 'GET') => {
  expect(mockFetch).toHaveBeenCalledWith(
    expect.stringContaining(url),
    expect.objectContaining({ method })
  );
};

// ============================================================================
// TEST DATA UTILITIES
// ============================================================================
export const generateTestUsers = (count: number = 3): MockUser[] => {
  return Array.from({ length: count }, (_, index) => 
    createMockUser({
      id: `test-user-${index + 1}`,
      email: `user${index + 1}@example.com`,
      full_name: `Test User ${index + 1}`
    })
  );
};

export const generateTestThreads = (count: number = 3, userId: string = 'test-user-1'): MockThread[] => {
  return Array.from({ length: count }, (_, index) => 
    createMockThread({
      id: `thread-${index + 1}`,
      title: `Test Thread ${index + 1}`,
      user_id: userId,
      messages: [createMockMessage({ id: `message-${index + 1}` })]
    })
  );
};

export const generateTestMessages = (count: number = 5, threadId: string = 'thread-1'): MockMessage[] => {
  return Array.from({ length: count }, (_, index) => 
    createMockMessage({
      id: `message-${index + 1}`,
      content: `Test message content ${index + 1}`,
      type: index % 2 === 0 ? 'user' : 'assistant',
      thread_id: threadId,
      timestamp: Date.now() + index * 1000 // Stagger timestamps
    })
  );
};

// ============================================================================
// CLEANUP UTILITIES
// ============================================================================
export const cleanupTestEnvironment = () => {
  jest.clearAllMocks();
  
  // Clear storage
  if (global.localStorage?.clear) global.localStorage.clear();
  if (global.sessionStorage?.clear) global.sessionStorage.clear();
  
  // Reset timers
  if (global.Date?.now) {
    global.Date.now = jest.fn(() => 1640995200000);
  }
  
  // Clear any pending timers
  jest.clearAllTimers();
  jest.useRealTimers();
};

export const setupTestEnvironment = () => {
  // Setup fake timers
  jest.useFakeTimers();
  
  // Setup stable Date.now
  global.Date.now = jest.fn(() => 1640995200000);
  
  // Setup default mocks
  setupMockLocalStorage();
  setupMockFetch([]);
  setupMockWebSocket();
  
  return {
    cleanup: cleanupTestEnvironment
  };
};

// ============================================================================
// ACT WRAPPER UTILITIES
// ============================================================================
export const actWrapper = async (fn: () => Promise<any> | any) => {
  let result;
  await act(async () => {
    result = await fn();
  });
  return result;
};

export const renderAndWait = async (ui: React.ReactElement, options: CustomRenderOptions = {}) => {
  let result: RenderResult;
  await act(async () => {
    result = renderWithProviders(ui, options);
  });
  return result!;
};

// ============================================================================
// ERROR BOUNDARY TESTING
// ============================================================================
export const TestErrorBoundary: React.FC<{ children: React.ReactNode; onError?: (error: Error) => void }> = ({ 
  children, 
  onError 
}) => {
  const [hasError, setHasError] = React.useState(false);

  React.useEffect(() => {
    const errorHandler = (event: ErrorEvent) => {
      setHasError(true);
      if (onError) onError(event.error);
    };

    window.addEventListener('error', errorHandler);
    return () => window.removeEventListener('error', errorHandler);
  }, [onError]);

  if (hasError) {
    return <div data-testid="error-boundary">Something went wrong</div>;
  }

  return <>{children}</>;
};

export const renderWithErrorBoundary = (
  ui: React.ReactElement, 
  options: CustomRenderOptions & { onError?: (error: Error) => void } = {}
) => {
  const { onError, ...renderOptions } = options;
  
  return renderWithProviders(
    <TestErrorBoundary onError={onError}>{ui}</TestErrorBoundary>,
    renderOptions
  );
};