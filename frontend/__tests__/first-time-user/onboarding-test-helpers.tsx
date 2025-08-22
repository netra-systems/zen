/**
 * Onboarding Test Helpers
 * Shared utilities for testing first-time user onboarding flow
 * 
 * @compliance testing.xml - Test utility helpers for onboarding flow
 * @compliance conventions.xml - Under 300 lines, functions ≤8 lines
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { TestProviders } from '../setup/test-providers';

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================

export interface MockUser {
  id: string;
  email: string;
  full_name?: string | null;
  picture?: string | null;
  is_active?: boolean;
  is_superuser?: boolean;
}

export interface MockAuthService {
  user: MockUser | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: jest.Mock;
  logout: jest.Mock;
}

// ============================================================================
// MOCK DATA
// ============================================================================

export const newUserData = {
  email: 'newuser@example.com',
  name: 'New User'
};

// ============================================================================
// MOCK SERVICES
// ============================================================================

export const mockAuthService: MockAuthService = {
  user: null,
  loading: false,
  isAuthenticated: false,
  login: jest.fn(),
  logout: jest.fn()
};

// ============================================================================
// SETUP FUNCTIONS
// ============================================================================

/**
 * Setup clean state for onboarding tests
 */
export function setupCleanState(): void {
  // Reset auth service
  mockAuthService.user = null;
  mockAuthService.loading = false;
  mockAuthService.isAuthenticated = false;
  
  // Clear all mocks
  jest.clearAllMocks();
  
  // Setup console mocks
  global.console.warn = jest.fn();
  global.console.error = jest.fn();
}

/**
 * Reset all mocks
 */
export function resetAllMocks(): void {
  jest.clearAllMocks();
  mockAuthService.login.mockClear();
  mockAuthService.logout.mockClear();
}

/**
 * Setup simple WebSocket mock
 */
export function setupSimpleWebSocketMock(): void {
  global.WebSocket = jest.fn(() => ({
    send: jest.fn(),
    close: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    readyState: WebSocket.OPEN
  })) as any;
}

/**
 * Clear auth state
 */
export function clearAuthState(): void {
  mockAuthService.user = null;
  mockAuthService.isAuthenticated = false;
  mockAuthService.loading = false;
}

/**
 * Setup Next.js mocks
 */
export function setupNextJSMocks(): void {
  // Mock Next.js router
  jest.mock('next/navigation', () => ({
    useRouter: () => ({
      push: jest.fn(),
      replace: jest.fn(),
      prefetch: jest.fn(),
      back: jest.fn()
    }),
    useSearchParams: () => new URLSearchParams(),
    usePathname: () => '/test'
  }));
  
  // Mock Next.js Image component
  jest.mock('next/image', () => ({
    __esModule: true,
    default: ({ src, alt, ...props }: any) => 
      React.createElement('img', { src, alt, ...props })
  }));
}

/**
 * Setup auth mocks
 */
export function setupAuthMocks(): void {
  jest.mock('@/auth/service', () => ({
    authService: mockAuthService
  }));
  
  jest.mock('@/store/authStore', () => ({
    useAuthStore: jest.fn(() => ({
      user: mockAuthService.user,
      isAuthenticated: mockAuthService.isAuthenticated,
      loading: mockAuthService.loading
    }))
  }));
}

// ============================================================================
// EXPECTATION HELPERS
// ============================================================================

/**
 * Expect value proposition to be displayed
 */
export function expectValueProposition(): void {
  const content = document.body.textContent || '';
  const hasValueProp = content.toLowerCase().includes('netra') ||
                      content.toLowerCase().includes('ai') ||
                      content.toLowerCase().includes('optimization');
  expect(hasValueProp).toBe(true);
}

/**
 * Expect call to action to be present
 */
export function expectCallToAction(): void {
  const loginButton = screen.queryByRole('button') ||
                     screen.queryByText(/login|sign in|get started/i);
  expect(loginButton).toBeTruthy();
}

/**
 * Expect error message to be displayed
 */
export function expectErrorMessage(errorText?: string): void {
  if (errorText) {
    const errorElement = screen.queryByText(new RegExp(errorText, 'i'));
    expect(errorElement).toBeTruthy();
  } else {
    const genericError = screen.queryByText(/error|failed|problem/i);
    expect(genericError).toBeTruthy();
  }
}

/**
 * Expect retry button to be present
 */
export function expectRetryButton(): void {
  const retryButton = screen.queryByRole('button', { name: /retry|try again|refresh/i }) ||
                     screen.queryByText(/retry|try again|refresh/i);
  expect(retryButton).toBeTruthy();
}

/**
 * Expect network error handling to be in place
 */
export function expectNetworkErrorHandling(): void {
  const networkError = screen.queryByText(/network|connection|offline|connectivity/i);
  const retryButton = screen.queryByRole('button', { name: /retry|try again/i });
  
  // Should have either network error message or retry capability
  expect(networkError || retryButton).toBeTruthy();
}

// ============================================================================
// RENDER UTILITIES
// ============================================================================

/**
 * Render with test setup
 */
export async function renderWithTestSetup(component: React.ReactElement): Promise<void> {
  render(component);
  
  // Wait for initial render
  await new Promise(resolve => setTimeout(resolve, 0));
}

/**
 * Create mock user with defaults
 */
export function createMockUser(overrides: Partial<MockUser> = {}): MockUser {
  return {
    id: 'test-user-123',
    email: 'test@example.com',
    full_name: 'Test User',
    picture: null,
    is_active: true,
    is_superuser: false,
    ...overrides
  };
}

// ============================================================================
// WEBSOCKET HELPERS
// ============================================================================

/**
 * Setup WebSocket with connection success
 */
export function setupWebSocketSuccess(): void {
  const mockWebSocket = {
    send: jest.fn(),
    close: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    readyState: WebSocket.OPEN,
    onopen: null,
    onclose: null,
    onerror: null,
    onmessage: null
  };
  
  global.WebSocket = jest.fn(() => mockWebSocket) as any;
}

/**
 * Setup WebSocket with connection failure
 */
export function setupWebSocketFailure(): void {
  global.WebSocket = jest.fn(() => {
    throw new Error('WebSocket connection failed');
  }) as any;
}

// ============================================================================
// UI STATE HELPERS
// ============================================================================

/**
 * Check if loading state is displayed
 */
export function isLoadingDisplayed(): boolean {
  const loadingText = screen.queryByText(/loading|connecting|initializing/i);
  const spinner = document.querySelector('[data-testid*="loading"]') ||
                 document.querySelector('.animate-spin');
  
  return !!(loadingText || spinner);
}

/**
 * Check if error state is displayed
 */
export function isErrorDisplayed(): boolean {
  const errorText = screen.queryByText(/error|failed|retry/i);
  const errorElement = document.querySelector('[data-testid*="error"]');
  
  return !!(errorText || errorElement);
}

/**
 * Check if authenticated content is displayed
 */
export function isAuthenticatedContentDisplayed(): boolean {
  const chatInput = screen.queryByRole('textbox');
  const messageList = screen.queryByRole('list');
  
  return !!(chatInput || messageList);
}

// ============================================================================
// PERFORMANCE HELPERS
// ============================================================================

/**
 * Measure component load time
 */
export function measureLoadTime(startTime: number): number {
  return performance.now() - startTime;
}

/**
 * Verify performance is within acceptable limits
 */
export function verifyPerformance(loadTime: number, maxTime: number = 2000): void {
  expect(loadTime).toBeLessThan(maxTime);
}

// ============================================================================
// CLEANUP HELPERS
// ============================================================================

/**
 * Cleanup test environment
 */
export function cleanupTestEnvironment(): void {
  clearAuthState();
  resetAllMocks();
  
  // Clear any timers
  jest.clearAllTimers();
  
  // Restore console
  if (jest.isMockFunction(global.console.warn)) {
    (global.console.warn as jest.Mock).mockRestore();
  }
  if (jest.isMockFunction(global.console.error)) {
    (global.console.error as jest.Mock).mockRestore();
  }
}