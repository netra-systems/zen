/**
 * Authentication Flow Integration Tests - REFACTORED
 * All functions ≤8 lines as per architecture requirements
 * Tests core authentication functionality with comprehensive utilities
 */

// Declare mocks first (Jest Module Hoisting)
const mockUseAuthStore = jest.fn();
const mockUseUnifiedChatStore = jest.fn();
const mockUseWebSocket = jest.fn();
const mockUseLoadingState = jest.fn();
const mockUseThreadNavigation = jest.fn();

// Mock hooks before imports
jest.mock('@/store/authStore', () => ({
  useAuthStore: mockUseAuthStore
}));

jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: mockUseUnifiedChatStore
}));

jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: mockUseWebSocket
}));

jest.mock('@/hooks/useLoadingState', () => ({
  useLoadingState: mockUseLoadingState
}));

jest.mock('@/hooks/useThreadNavigation', () => ({
  useThreadNavigation: mockUseThreadNavigation
}));

jest.mock('@/components/auth/AuthGate', () => {
  return function MockAuthGate({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
  };
});

jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    refresh: jest.fn(),
    pathname: '/',
    query: {},
    asPath: '/'
  }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams()
}));

// Now imports
import React from 'react';
import { render, waitFor, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

import { useAuthStore } from '@/store/authStore';
import { TestProviders } from '@/__tests__/setup/test-providers';
import {
  setupTestEnvironment,
  createWebSocketServer,
  resetTestState,
  mockUser,
  mockAuthToken,
  expectAuthenticatedState,
  expectUnauthenticatedState,
  performFullCleanup,
  mockNextRouter
} from '../test-utils/integration-test-setup';
import {
  createLoginComponent,
  createLogoutComponent,
  performLoginAction,
  performLogoutAction,
  verifyInitialUnauthenticatedState,
  verifyInitialAuthenticatedState,
  verifySuccessfulLogin,
  verifySuccessfulLogout,
  setupAuthenticatedState,
  performLoginFlow,
  verifyStatePersistence,
  performPageRefresh,
  verifyStateRestoration,
  performOnboardingLogin,
  verifyOnboardingAuthState,
  simulateFirstThreadCreation,
  expectOnboardingFlowComplete,
  simulateSessionTimeout,
  verifySessionTimeoutHandling,
  performReauthentication,
  expectContinuedOnboarding,
  createMockAuthStore,
  setupReactiveAuthStore
} from './utils/auth-flow-utils';

// Mock localStorage (≤8 lines)
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: jest.fn((key: string) => store[key] || null),
    setItem: jest.fn((key: string, value: string) => { store[key] = value; }),
    removeItem: jest.fn((key: string) => { delete store[key]; }),
    clear: jest.fn(() => { store = {}; })
  };
})();
global.localStorage = localStorageMock as any;

describe('Authentication Flow Integration', () => {
  let server: any;
  let mockAuthStore: any;

  beforeEach(() => {
    setupTestEnvironment();
    server = createWebSocketServer();
    resetTestState();
    setupLocalStorageMocks();
    mockAuthStore = createMockAuthStore();
    setupReactiveAuthStore(mockAuthStore);
    setupHookMocks();
  });

  afterEach(() => {
    performFullCleanup(server);
  });

  it('should handle login and authentication', async () => {
    await performLoginTest();
  });

  it('should handle logout and cleanup', async () => {
    await performLogoutTest();
  });

  it('should persist authentication state', async () => {
    await performStatePersistenceTest();
  });

  it('should support onboarding flow authentication', async () => {
    await performOnboardingFlowTest();
  });

  it('should handle session timeout during onboarding', async () => {
    await performSessionTimeoutTest();
  });
});

// Test implementation functions (≤8 lines each)
const setupLocalStorageMocks = () => {
  localStorageMock.clear();
  localStorageMock.getItem.mockClear();
  localStorageMock.setItem.mockClear();
  localStorageMock.removeItem.mockClear();
};

const setupHookMocks = () => {
  mockUseUnifiedChatStore.mockReturnValue({
    messages: [],
    threads: [],
    addMessage: jest.fn()
  });
  
  mockUseWebSocket.mockReturnValue({
    sendMessage: jest.fn(),
    isConnected: true
  });
  
  mockUseLoadingState.mockReturnValue({
    isLoading: false,
    setLoading: jest.fn()
  });
  
  mockUseThreadNavigation.mockReturnValue({
    currentThreadId: null,
    navigateToThread: jest.fn()
  });
};

const performLoginTest = async () => {
  const LoginComponent = createLoginComponent(mockUseAuthStore, mockUser, mockAuthToken);
  const { getByText, getByTestId } = render(<TestProviders><LoginComponent /></TestProviders>);
  
  verifyInitialUnauthenticatedState(getByTestId);
  performLoginAction(getByText);
  
  await verifySuccessfulLogin(getByTestId);
  expectAuthenticatedState();
};

const performLogoutTest = async () => {
  setupAuthenticatedState(mockUseAuthStore, mockUser, mockAuthToken);
  
  const LogoutComponent = createLogoutComponent(mockUseAuthStore);
  const { getByText, getByTestId } = render(<TestProviders><LogoutComponent /></TestProviders>);
  
  verifyInitialAuthenticatedState(getByTestId);
  performLogoutAction(getByText);
  
  await verifySuccessfulLogout(getByTestId);
  expectUnauthenticatedState();
};

const performStatePersistenceTest = async () => {
  performLoginFlow(mockUseAuthStore, mockUser, mockAuthToken);
  verifyStatePersistence(mockAuthToken, mockUser);
  performPageRefresh(mockUseAuthStore);
  await verifyStateRestoration(mockUseAuthStore, mockUser, mockAuthToken);
};

const performOnboardingFlowTest = async () => {
  await performOnboardingLogin(mockUseAuthStore);
  await verifyOnboardingAuthState(mockUseAuthStore);
  await simulateFirstThreadCreation(mockUseUnifiedChatStore);
  expectOnboardingFlowComplete(mockUseAuthStore);
};

const performSessionTimeoutTest = async () => {
  setupAuthenticatedState(mockUseAuthStore, mockUser, mockAuthToken);
  await simulateSessionTimeout(mockUseAuthStore);
  await verifySessionTimeoutHandling(mockUseAuthStore);
  await performReauthentication(mockUseAuthStore, mockUser);
  expectContinuedOnboarding(mockUseAuthStore);
};