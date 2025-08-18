/**
 * Shared Test Utilities and Fixtures
 * Common operations, mocks, and utilities for frontend component tests
 */

import React from 'react';
import { render, RenderOptions } from '@testing-library/react';
import '@testing-library/jest-dom';
import WS from 'jest-websocket-mock';

// Mock Next.js navigation utilities
export const createMockRouter = () => ({
  push: jest.fn(),
  replace: jest.fn(),
  refresh: jest.fn(),
  back: jest.fn(),
  forward: jest.fn(),
  pathname: '/',
  query: {},
  asPath: '/',
});

export const setupNextjsMocks = () => {
  jest.mock('next/navigation', () => ({
    useRouter: () => createMockRouter(),
    usePathname: () => '/',
    useSearchParams: () => new URLSearchParams(),
  }));
};

// WebSocket test utilities - DEPRECATED: Use WebSocketTestManager instead
export class WebSocketTestHelper {
  public server?: WS;

  constructor(private url: string = 'ws://localhost:8000/ws') {}

  setup() {
    this.cleanup(); // Ensure clean state first
    this.server = new WS(this.url);
    return this.server;
  }

  cleanup() {
    try {
      if (this.server) {
        this.server = undefined;
      }
      WS.clean();
    } catch (error) {
      // Ignore cleanup errors for non-existent servers
    }
  }

  async waitForConnection() {
    if (this.server) {
      await this.server.connected;
    }
  }

  sendMessage(message: any) {
    if (this.server) {
      this.server.send(JSON.stringify(message));
    }
  }

  close() {
    if (this.server) {
      this.server.close();
    }
  }
}

// Common test data factories
export const createMockThread = (overrides: any = {}) => ({
  id: `thread-${Math.random().toString(36).substr(2, 9)}`,
  title: 'Mock Thread',
  created_at: Math.floor(Date.now() / 1000),
  updated_at: Math.floor(Date.now() / 1000),
  user_id: 'user-1',
  message_count: 1,
  status: 'active' as const,
  lastMessage: 'Mock message',
  lastActivity: new Date().toISOString(),
  isActive: false,
  ...overrides,
});

export const createMockUser = (overrides: any = {}) => ({
  id: 'user-1',
  email: 'test@example.com',
  name: 'Test User',
  role: 'user',
  ...overrides,
});

export const createMockMessage = (overrides: any = {}) => ({
  id: `msg-${Math.random().toString(36).substr(2, 9)}`,
  content: 'Mock message content',
  role: 'user' as const,
  timestamp: Date.now(),
  threadId: 'thread-1',
  ...overrides,
});

// Form test utilities
export const fillForm = async (formData: Record<string, string>, userEvent: any) => {
  for (const [fieldName, value] of Object.entries(formData)) {
    const field = document.querySelector(`[name="${fieldName}"]`) as HTMLInputElement;
    if (field) {
      await userEvent.clear(field);
      await userEvent.type(field, value);
    }
  }
};

export const submitForm = (formSelector: string = 'form') => {
  const form = document.querySelector(formSelector) as HTMLFormElement;
  if (form) {
    form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
  }
};

// File test utilities
export const createMockFile = (
  name: string = 'test.txt',
  content: string = 'test content',
  type: string = 'text/plain'
): File => {
  return new File([content], name, { type });
};

export const createMockFileList = (files: File[]): FileList => {
  const fileList = {
    ...files,
    length: files.length,
    item: (index: number) => files[index] || null,
    [Symbol.iterator]: function* () {
      yield* files;
    },
  };
  return fileList as FileList;
};

// Event simulation utilities
export const simulateFileUpload = (input: HTMLInputElement, files: File[]) => {
  Object.defineProperty(input, 'files', {
    value: createMockFileList(files),
    writable: false,
  });
  input.dispatchEvent(new Event('change', { bubbles: true }));
};

export const simulateDragAndDrop = (
  source: HTMLElement,
  target: HTMLElement,
  files?: File[]
) => {
  const dataTransfer = {
    files: files ? createMockFileList(files) : [],
    items: [],
    types: files ? ['Files'] : [],
  };

  source.dispatchEvent(new DragEvent('dragstart', { bubbles: true, dataTransfer }));
  target.dispatchEvent(new DragEvent('dragover', { bubbles: true, dataTransfer }));
  target.dispatchEvent(new DragEvent('drop', { bubbles: true, dataTransfer }));
};

// Animation and timing utilities
export const waitForAnimation = (duration: number = 100) => {
  return new Promise(resolve => setTimeout(resolve, duration));
};

export const mockAnimationFrame = () => {
  let id = 0;
  const callbacks = new Map<number, () => void>();

  global.requestAnimationFrame = jest.fn((callback) => {
    const currentId = ++id;
    callbacks.set(currentId, callback);
    return currentId;
  });

  global.cancelAnimationFrame = jest.fn((id: number) => {
    callbacks.delete(id);
  });

  const flushAnimationFrames = () => {
    callbacks.forEach(callback => callback());
    callbacks.clear();
  };

  return { flushAnimationFrames };
};

// Performance testing utilities
export const measureRenderTime = (renderFunction: () => any) => {
  const startTime = performance.now();
  const result = renderFunction();
  const endTime = performance.now();
  return { result, renderTime: endTime - startTime };
};

export const createLargeDataset = <T,>(
  factory: (index: number) => T,
  size: number = 1000
): T[] => {
  return Array.from({ length: size }, (_, index) => factory(index));
};

// Accessibility test utilities
export const checkAriaAttributes = (element: HTMLElement, expectedAttributes: Record<string, string>) => {
  Object.entries(expectedAttributes).forEach(([attr, value]) => {
    expect(element).toHaveAttribute(attr, value);
  });
};

export const checkKeyboardNavigation = (elements: HTMLElement[]) => {
  elements.forEach(element => {
    expect(element).toHaveAttribute('tabindex');
  });
};

// Error boundary utilities
export const createErrorBoundary = () => {
  return class ErrorBoundary extends React.Component<
    { children: React.ReactNode },
    { hasError: boolean }
  > {
    constructor(props: any) {
      super(props);
      this.state = { hasError: false };
    }

    static getDerivedStateFromError() {
      return { hasError: true };
    }

    componentDidCatch(error: Error, errorInfo: any) {
      // test debug removed: console.log('Error boundary caught error:', error, errorInfo);
    }

    render() {
      if (this.state.hasError) {
        return <div data-testid="error-fallback">Something went wrong</div>;
      }
      return this.props.children;
    }
  };
};

// Mock API responses
export const mockFetch = (response: any, ok: boolean = true, delay: number = 0) => {
  global.fetch = jest.fn().mockImplementation(
    () => new Promise(resolve => 
      setTimeout(() => resolve({
        ok,
        status: ok ? 200 : 500,
        json: () => Promise.resolve(response),
        text: () => Promise.resolve(JSON.stringify(response)),
      }), delay)
    )
  );
};

export const mockFetchError = (error: string = 'Network error') => {
  global.fetch = jest.fn().mockRejectedValue(new Error(error));
};

// Console utilities for suppressing expected errors in tests
export const suppressConsoleError = (testFunction: () => void | Promise<void>) => {
  const originalError = console.error;
  console.error = jest.fn();
  
  const runTest = async () => {
    try {
      await testFunction();
    } finally {
      console.error = originalError;
    }
  };

  return runTest();
};

export const suppressConsoleWarn = (testFunction: () => void | Promise<void>) => {
  const originalWarn = console.warn;
  console.warn = jest.fn();
  
  const runTest = async () => {
    try {
      await testFunction();
    } finally {
      console.warn = originalWarn;
    }
  };

  return runTest();
};

// Environment mocking utilities
export const mockEnvironment = (env: Record<string, string>) => {
  const originalEnv = process.env;
  process.env = { ...originalEnv, ...env };
  
  return () => {
    process.env = originalEnv;
  };
};

export const mockWindowSize = (width: number, height: number) => {
  Object.defineProperty(window, 'innerWidth', { 
    value: width, 
    writable: true, 
    configurable: true 
  });
  Object.defineProperty(window, 'innerHeight', { 
    value: height, 
    writable: true, 
    configurable: true 
  });
  
  window.dispatchEvent(new Event('resize'));
};

// Local storage utilities
export const mockLocalStorage = () => {
  const store: Record<string, string> = {};
  
  Object.defineProperty(window, 'localStorage', {
    value: {
      getItem: (key: string) => store[key] || null,
      setItem: (key: string, value: string) => { store[key] = value; },
      removeItem: (key: string) => { delete store[key]; },
      clear: () => { Object.keys(store).forEach(key => delete store[key]); },
    },
    writable: true,
  });

  return store;
};

// Date utilities
export const mockDate = (date: string | Date) => {
  const mockDate = new Date(date);
  const originalDate = Date;
  
  global.Date = jest.fn(() => mockDate) as any;
  global.Date.now = jest.fn(() => mockDate.getTime());
  
  return () => {
    global.Date = originalDate;
  };
};

// Export everything for easy importing
export const testUtils = {
  createMockRouter,
  setupNextjsMocks,
  WebSocketTestHelper,
  createMockThread,
  createMockUser,
  createMockMessage,
  createMockFile,
  createMockFileList,
  fillForm,
  submitForm,
  simulateFileUpload,
  simulateDragAndDrop,
  waitForAnimation,
  mockAnimationFrame,
  measureRenderTime,
  createLargeDataset,
  checkAriaAttributes,
  checkKeyboardNavigation,
  createErrorBoundary,
  mockFetch,
  mockFetchError,
  suppressConsoleError,
  suppressConsoleWarn,
  mockEnvironment,
  mockWindowSize,
  mockLocalStorage,
  mockDate,
};

export default testUtils;