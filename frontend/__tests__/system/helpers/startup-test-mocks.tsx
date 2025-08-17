/**
 * Shared Mock Definitions for Frontend System Startup Tests
 * Centralizes all Jest mocks used across startup test modules
 */

import React from 'react';

// Mock webSocketService
export const mockWebSocketService = () => {
  jest.mock('@/services/webSocketService');
};

// Mock AuthContext
export const mockAuthContext = () => {
  jest.mock('@/auth/context', () => ({
    AuthContext: require('react').createContext({
      token: 'test-token',
      user: null,
      login: jest.fn(),
      logout: jest.fn(),
      loading: false,
      authConfig: null
    }),
    useAuthContext: () => ({
      token: 'test-token',
      user: null,
      login: jest.fn(),
      logout: jest.fn(),
      loading: false,
      authConfig: null
    }),
    AuthProvider: ({ children }: { children: any }) => children
  }));
};

// Mock Logger
export const mockLogger = () => {
  jest.mock('@/lib/logger', () => ({
    logger: {
      debug: jest.fn(),
      info: jest.fn(),
      warn: jest.fn(),
      error: jest.fn(),
    }
  }));
};

// Mock Config
export const mockConfig = () => {
  jest.mock('@/config', () => ({
    config: {
      apiUrl: 'http://localhost:8000',
      wsUrl: 'ws://localhost:8000/ws',
    }
  }));
};

// Mock Next.js Router
export const mockNextRouter = () => {
  jest.mock('next/navigation', () => ({
    useRouter: () => ({
      push: jest.fn(),
      replace: jest.fn(),
      pathname: '/',
      query: {},
      asPath: '/',
    }),
    usePathname: () => '/',
    useSearchParams: () => new URLSearchParams(),
  }));
};

// Mock Zustand Stores
export const mockZustandStores = () => {
  // Mock auth store
  jest.doMock('@/store/authStore', () => ({
    useAuthStore: {
      getState: () => ({
        user: null,
        token: null,
        isAuthenticated: false,
        login: jest.fn(),
        logout: jest.fn(),
      }),
    },
  }));

  // Mock chat store
  jest.doMock('@/store/chatStore', () => ({
    useChatStore: {
      getState: () => ({
        messages: [],
        isLoading: false,
        addMessage: jest.fn(),
        clearMessages: jest.fn(),
      }),
    },
  }));
};

// Initialize All Common Mocks
export const initializeAllMocks = () => {
  mockWebSocketService();
  mockAuthContext();
  mockLogger();
  mockConfig();
  mockNextRouter();
  mockZustandStores();
};

// Mock Production Environment
export const mockProductionEnvironment = () => {
  const originalEnv = process.env.NODE_ENV;
  process.env.NODE_ENV = 'production';
  return { restore: () => { process.env.NODE_ENV = originalEnv; } };
};

// Mock Development Environment
export const mockDevelopmentEnvironment = () => {
  const originalEnv = process.env.NODE_ENV;
  process.env.NODE_ENV = 'development';
  return { restore: () => { process.env.NODE_ENV = originalEnv; } };
};

// Create Error Boundary Component for Testing
export const createErrorBoundary = () => {
  return class ErrorBoundary extends React.Component<
    { children: React.ReactNode },
    { hasError: boolean }
  > {
    constructor(props: { children: React.ReactNode }) {
      super(props);
      this.state = { hasError: false };
    }
    
    static getDerivedStateFromError() {
      return { hasError: true };
    }
    
    componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
      console.log('Error caught:', error, errorInfo);
    }
    
    render() {
      if (this.state.hasError) {
        return <div>Error occurred during startup</div>;
      }
      return this.props.children;
    }
  };
};

// Create Error Throwing Component for Testing
export const createThrowErrorComponent = () => {
  return () => {
    throw new Error('Startup error');
  };
};

// Mock Performance API for Testing
export const mockPerformanceAPI = () => {
  const originalNow = performance.now;
  let currentTime = 0;
  
  performance.now = jest.fn(() => {
    currentTime += 10;
    return currentTime;
  });
  
  return {
    restore: () => { performance.now = originalNow; }
  };
};

// Mock Fetch Global
export const mockFetchGlobal = () => {
  const originalFetch = global.fetch;
  global.fetch = jest.fn();
  return {
    restore: () => { global.fetch = originalFetch; }
  };
};