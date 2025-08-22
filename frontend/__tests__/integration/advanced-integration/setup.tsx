/**
 * Advanced Integration Test Setup and Utilities
 * Shared setup, mocks, and utilities for advanced integration tests
 */

import React from 'react';
import { render } from '@testing-library/react';
import '@testing-library/jest-dom';
import WS from 'jest-websocket-mock';
import { safeWebSocketCleanup } from '../../helpers/websocket-test-manager';

import { useAuthStore } from '@/store/authStore';
import { useChatStore } from '@/store/chatStore';
import { useThreadStore } from '@/store/threadStore';

import { TestProviders } from '@/__tests__/setup/test-providers';

// Mock Next.js navigation
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

export interface TestSetupOptions {
  enableWebSocket?: boolean;
  mockUser?: boolean;
  environment?: Record<string, string>;
}

export class TestSetup {
  public server?: WS;
  
  constructor(private options: TestSetupOptions = {}) {}

  beforeEach() {
    // Set up environment
    const env = {
      NEXT_PUBLIC_API_URL: 'http://localhost:8000',
      NEXT_PUBLIC_WS_URL: 'ws://localhost:8000',
      ...this.options.environment
    };
    
    Object.entries(env).forEach(([key, value]) => {
      process.env[key] = value;
    });

    // Set up WebSocket if enabled
    if (this.options.enableWebSocket) {
      this.server = new WS('ws://localhost:8000/ws');
    }

    jest.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
    
    // Reset stores to initial state
    useAuthStore.setState({ 
      user: this.options.mockUser ? { id: '1', email: 'test@example.com' } : null, 
      token: null, 
      isAuthenticated: this.options.mockUser || false 
    });
    useChatStore.setState({ messages: [], currentThread: null });
    useThreadStore.setState({ threads: [], activeThread: null });
    
    // Mock fetch
    global.fetch = jest.fn();
  }

  afterEach() {
    if (this.server) {
      safeWebSocketCleanup();
    }
    jest.restoreAllMocks();
  }

  async waitForWebSocketConnection() {
    if (this.server) {
      await this.server.connected;
    }
  }

  sendWebSocketMessage(message: any) {
    if (this.server) {
      this.server.send(JSON.stringify(message));
    }
  }

  closeWebSocketConnection() {
    if (this.server) {
      this.server.close();
    }
  }
}

export const createTestSetup = (options?: TestSetupOptions) => new TestSetup(options);

// Mock navigation router for components that need it
export const createMockRouter = () => require('next/navigation').useRouter();

// Shared test utilities
export const mockFetch = (response: any, ok = true) => {
  (global.fetch as jest.Mock).mockResolvedValue({
    ok,
    json: async () => response
  });
};

export const expectToHaveTextContent = (element: HTMLElement, text: string) => {
  expect(element).toHaveTextContent(text);
};

export const createMockFile = (name: string, content: string = 'test content', type: string = 'text/plain'): File => {
  return new File([content], name, { type });
};

// Animation utilities
export const waitForAnimation = (duration: number = 100) => {
  return new Promise(resolve => setTimeout(resolve, duration));
};

// Form test utilities
export const createFormData = (fields: Record<string, any>) => {
  return fields;
};

// WebSocket message builders
export const createWebSocketMessage = (type: string, data: any = {}) => {
  return {
    type,
    timestamp: Date.now(),
    ...data
  };
};

// Theme context provider for theme tests
export const createThemeProvider = (initialTheme: string = 'light') => {
  const ThemeContext = React.createContext({
    theme: initialTheme,
    setTheme: (theme: string) => {}
  });
  
  const ThemeProvider = ({ children }: { children: React.ReactNode }) => {
    const [theme, setTheme] = React.useState(initialTheme);
    
    React.useEffect(() => {
      const savedTheme = localStorage.getItem('theme');
      if (savedTheme) setTheme(savedTheme);
    }, []);
    
    const updateTheme = (newTheme: string) => {
      setTheme(newTheme);
      localStorage.setItem('theme', newTheme);
      document.documentElement.setAttribute('data-theme', newTheme);
    };
    
    return (
      <ThemeContext.Provider value={{ theme, setTheme: updateTheme }}>
        {children}
      </ThemeContext.Provider>
    );
  };
  
  return { ThemeContext, ThemeProvider };
};

// Error boundary for testing error handling
export class TestErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean; errorInfo: any }
> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: any) {
    this.setState({ errorInfo });
  }

  retry = () => {
    this.setState({ hasError: false, errorInfo: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div>
          <div data-testid="error-message">Something went wrong</div>
          <button onClick={this.retry}>Retry</button>
        </div>
      );
    }

    return this.props.children;
  }
}

// Console error suppression for tests that expect errors
export const suppressConsoleError = (testFunction: () => void) => {
  const originalError = console.error;
  console.error = jest.fn();
  
  try {
    testFunction();
  } finally {
    console.error = originalError;
  }
};