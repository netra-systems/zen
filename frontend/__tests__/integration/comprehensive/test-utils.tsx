/**
 * Shared Test Utilities for Comprehensive Integration Tests
 * 
 * Contains common imports, mocks, and setup functions used across all 
 * comprehensive test modules to avoid duplication and maintain consistency.
 */

import React from 'react';
import { render, waitFor, screen, fireEvent, act } from '@testing-library/react';
import { renderHook } from '@testing-library/react';
import '@testing-library/jest-dom';
import WS from 'jest-websocket-mock';

// Import providers and hooks
import { AgentProvider } from '@/providers/AgentProvider';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useAgent } from '@/hooks/useAgent';
import { useChatWebSocket } from '@/hooks/useChatWebSocket';
import { useAuthStore } from '@/store/authStore';
import { useChatStore } from '@/store/chatStore';
import { useThreadStore } from '@/store/threadStore';
import apiClient from '@/services/apiClient';

import { TestProviders } from '../test-utils/providers';

/**
 * Common mock for Next.js navigation
 */
export const mockNextNavigation = () => {
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
};

/**
 * Setup function for test environment
 * Should be called in beforeEach of each test suite
 */
export const setupTestEnvironment = (server: WS) => {
  process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000';
  process.env.NEXT_PUBLIC_WS_URL = 'ws://localhost:8000';
  jest.clearAllMocks();
  localStorage.clear();
  sessionStorage.clear();
  
  // Reset stores to initial state
  useAuthStore.setState({ 
    user: null, 
    token: null, 
    isAuthenticated: false 
  });
  useChatStore.setState({ 
    messages: [], 
    currentThread: null 
  });
  useThreadStore.setState({ 
    threads: [], 
    activeThread: null 
  });
  
  global.fetch = jest.fn();
};

/**
 * Cleanup function for test environment
 * Should be called in afterEach of each test suite
 */
export const cleanupTestEnvironment = () => {
  WS.clean();
  jest.restoreAllMocks();
};

/**
 * Create a WebSocket mock server
 */
export const createMockWebSocketServer = (url: string = 'ws://localhost:8000/ws'): WS => {
  return new WS(url);
};

/**
 * Common theme context for testing theme-related functionality
 */
export const createThemeContext = () => {
  return React.createContext({
    theme: 'light',
    setTheme: (theme: string) => {}
  });
};

/**
 * Theme provider component for testing
 */
export const createThemeProvider = (ThemeContext: React.Context<any>) => {
  return ({ children }: { children: React.ReactNode }) => {
    const [theme, setTheme] = React.useState('light');
    
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
};

/**
 * Mock user preferences for testing
 */
export const mockUserPreferences = {
  notifications: true,
  autoSave: false,
  language: 'en',
  fontSize: 'medium'
};

/**
 * Helper to simulate user interaction delays
 */
export const waitForUserInteraction = (ms: number = 100) => {
  return new Promise(resolve => setTimeout(resolve, ms));
};

/**
 * Mock form data for multi-step forms
 */
export const mockFormData = {
  model: '',
  temperature: 0.7,
  maxTokens: 1000
};

/**
 * Validation helper for form testing
 */
export const validateFormStep = (step: number, formData: typeof mockFormData) => {
  const errors: Record<string, string> = {};
  
  if (step === 1 && !formData.model) {
    errors.model = 'Model is required';
  }
  
  if (step === 2) {
    if (formData.temperature < 0 || formData.temperature > 2) {
      errors.temperature = 'Temperature must be between 0 and 2';
    }
    if (formData.maxTokens < 1 || formData.maxTokens > 4000) {
      errors.maxTokens = 'Max tokens must be between 1 and 4000';
    }
  }
  
  return { errors, isValid: Object.keys(errors).length === 0 };
};

/**
 * Mock WebSocket message factory
 */
export const createWebSocketMessage = (type: string, data: any = {}) => {
  return JSON.stringify({ type, data, timestamp: Date.now() });
};

/**
 * Simulate network delay for testing async operations
 */
export const simulateNetworkDelay = (ms: number = 500) => {
  return new Promise(resolve => setTimeout(resolve, ms));
};

/**
 * Mock API response factory
 */
export const createMockApiResponse = (data: any, options?: { ok?: boolean; status?: number }) => {
  return {
    ok: options?.ok ?? true,
    status: options?.status ?? 200,
    json: async () => data,
    text: async () => JSON.stringify(data)
  };
};

/**
 * Helper to test component rendering with providers
 */
export const renderWithProviders = (component: React.ReactElement) => {
  return render(
    <TestProviders>
      {component}
    </TestProviders>
  );
};

/**
 * Helper to test hooks with providers
 */
export const renderHookWithProviders = (hook: () => any) => {
  return renderHook(hook, {
    wrapper: ({ children }) => <TestProviders>{children}</TestProviders>
  });
};

/**
 * Common test timeouts
 */
export const TEST_TIMEOUTS = {
  SHORT: 1000,
  MEDIUM: 3000,
  LONG: 5000,
  NETWORK: 10000
};

/**
 * Mock error for testing error boundaries
 */
export const createMockError = (message: string = 'Test error') => {
  return new Error(message);
};

/**
 * Helper to test async state changes
 */
export const waitForStateChange = async (
  getState: () => any, 
  expectedValue: any, 
  timeout: number = TEST_TIMEOUTS.MEDIUM
) => {
  await waitFor(() => {
    expect(getState()).toEqual(expectedValue);
  }, { timeout });
};

// Export all testing utilities
export {
  React,
  render,
  waitFor,
  screen,
  fireEvent,
  act,
  renderHook,
  WS,
  AgentProvider,
  useWebSocket,
  useAgent,
  useChatWebSocket,
  useAuthStore,
  useChatStore,
  useThreadStore,
  apiClient,
  TestProviders
};