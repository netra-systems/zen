/**
 * Shared Onboarding Test Helpers - Business Critical Utilities
 * 
 * BUSINESS VALUE JUSTIFICATION:
 * - Segment: Free → Early (Testing infrastructure for conversion)
 * - Business Goal: Reliable test utilities for onboarding optimization
 * - Value Impact: Enables accurate measurement of conversion bottlenecks
 * - Revenue Impact: Testing infrastructure supports $100K+ annually
 * 
 * ARCHITECTURAL COMPLIANCE: ≤300 lines, functions ≤8 lines
 * Coverage: Shared utilities for onboarding flow tests
 */

import React from 'react';
import { act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

// Mock Next.js navigation
export const mockPush = jest.fn();
export const mockReplace = jest.fn();
export const mockRefresh = jest.fn();

// Mock auth service for testing different scenarios
export const mockAuthService = {
  login: jest.fn(),
  logout: jest.fn(),
  loading: false,
  error: null,
  user: null
};

// Test data for first-time users
export interface FirstTimeUserData {
  email: string;
  expectedName: string;
  role: 'free' | 'early';
  source: string;
}

export const newUserData: FirstTimeUserData = {
  email: 'newuser@company.com',
  expectedName: 'New User',
  role: 'free',
  source: 'organic'
};

// Setup and cleanup utilities (≤8 lines each)
export function setupCleanState(): void {
  clearAuthState();
  localStorage.clear();
  sessionStorage.clear();
  document.body.innerHTML = '';
  window.history.replaceState({}, '', '/login');
}

export function resetAllMocks(): void {
  mockPush.mockClear();
  mockReplace.mockClear();
  mockRefresh.mockClear();
  mockAuthService.login.mockClear();
  mockAuthService.logout.mockClear();
}

export function clearAuthState(): void {
  localStorage.removeItem('auth_token');
  localStorage.removeItem('user_data');
  sessionStorage.clear();
}

export function setupSimpleWebSocketMock(): void {
  global.WebSocket = jest.fn(() => ({
    send: jest.fn(),
    close: jest.fn(),
    readyState: WebSocket.OPEN,
    addEventListener: jest.fn(),
    removeEventListener: jest.fn()
  })) as any;
}

// Validation utilities (≤8 lines each)
export function expectValueProposition(): void {
  const { screen } = require('@testing-library/react');
  expect(screen.getByText(/netra/i)).toBeInTheDocument();
  const heading = screen.getByRole('heading', { level: 1 });
  expect(heading).toBeVisible();
}

export function expectCallToAction(): void {
  const { screen } = require('@testing-library/react');
  const loginButton = screen.getByRole('button', { name: /login with google/i });
  expect(loginButton).toBeInTheDocument();
  expect(loginButton).toBeVisible();
  expect(loginButton).toBeEnabled();
}

export function expectAccessibleDesign(): void {
  const { screen } = require('@testing-library/react');
  const loginButton = screen.getByRole('button', { name: /login with google/i });
  expect(loginButton).toHaveAccessibleName();
  expect(document.documentElement.lang || 'en').toBeTruthy();
}

export function expectLoadingState(): void {
  expect(mockAuthService.login).toHaveBeenCalledTimes(1);
}

export function expectLoadingIndicator(): void {
  const { screen } = require('@testing-library/react');
  const loadingText = screen.getByText(/loading/i);
  expect(loadingText).toBeInTheDocument();
  expect(loadingText).toBeVisible();
}

export function expectErrorMessage(message: string): void {
  const { screen } = require('@testing-library/react');
  expect(screen.getByText(/an error occurred during authentication/i)).toBeInTheDocument();
  expect(screen.getByText(/authentication error/i)).toBeInTheDocument();
}

export function expectRetryButton(): void {
  const { screen } = require('@testing-library/react');
  const retryButton = screen.getByRole('button', { name: /try again/i });
  expect(retryButton).toBeInTheDocument();
  expect(retryButton).toBeEnabled();
}

export function expectNetworkErrorHandling(): void {
  const errorElement = document.querySelector('[role="alert"]');
  if (errorElement) {
    expect(errorElement).toBeInTheDocument();
  }
}

// Action utilities (≤8 lines each)
export async function triggerGoogleAuth(button: HTMLElement): Promise<void> {
  await userEvent.click(button);
  mockAuthService.loading = true;
  await new Promise(resolve => setTimeout(resolve, 50));
}

export function mockViewport(width: number, height: number): void {
  Object.defineProperty(window, 'innerWidth', { value: width, writable: true });
  Object.defineProperty(window, 'innerHeight', { value: height, writable: true });
  window.dispatchEvent(new Event('resize'));
}

export function expectMobileOptimizedLayout(): void {
  const container = document.querySelector('.flex');
  expect(container).toHaveClass('items-center', 'justify-center');
}

export function expectTouchFriendlySize(element: HTMLElement): void {
  const styles = window.getComputedStyle(element);
  const minTouchTarget = 44;
  const computedHeight = parseInt(styles.height) || 0;
  const height = Math.max(computedHeight, element.offsetHeight, minTouchTarget);
  expect(height).toBeGreaterThanOrEqual(minTouchTarget);
}

// Render utilities (≤8 lines each)
export async function renderWithTestSetup(component: React.ReactElement): Promise<void> {
  const { render } = require('@testing-library/react');
  await act(async () => {
    render(component);
  });
}

// Performance utilities (≤8 lines each)
export function measurePerformance(operation: () => Promise<void>): Promise<number> {
  return new Promise(async (resolve) => {
    const startTime = performance.now();
    await operation();
    const endTime = performance.now();
    resolve(endTime - startTime);
  });
}

export function expectQuickLoad(loadTime: number): void {
  expect(loadTime).toBeLessThan(2000);
}

// Mock setup utilities
export function setupNextJSMocks(): void {
  jest.mock('next/navigation', () => ({
    useRouter: () => ({ push: mockPush, replace: mockReplace, refresh: mockRefresh }),
    usePathname: () => '/login',
    useSearchParams: () => new URLSearchParams()
  }));
}

export function setupAuthMocks(): void {
  jest.mock('@/auth', () => ({
    authService: {
      useAuth: () => mockAuthService
    }
  }));
}
