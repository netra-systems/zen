/**
 * Test Assertion Helpers - Reusable assertion patterns
 * Keeps test functions ≤8 lines by extracting common assertions
 */

import { screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { useAuthStore } from '@/store/authStore';

export const assertElementText = (testId: string, expectedText: string) => {
  expect(screen.getByTestId(testId)).toHaveTextContent(expectedText);
};

export const assertElementExists = (testId: string) => {
  expect(screen.getByTestId(testId)).toBeInTheDocument();
};

export const assertElementNotExists = (testId: string) => {
  expect(screen.queryByTestId(testId)).not.toBeInTheDocument();
};

export const assertWebSocketStatus = (status: 'Connected' | 'Disconnected') => {
  assertElementText('ws-status', status);
};

export const assertConnectionStatus = (status: 'Connected' | 'Disconnected') => {
  assertElementText('connection-status', status);
};

export const assertAuthStatus = (status: 'Authenticated' | 'Session Expired') => {
  assertElementText('auth-status', status);
};

export const assertUserIsAuthenticated = () => {
  expect(useAuthStore.getState().isAuthenticated).toBe(true);
};

export const assertUserIsNotAuthenticated = () => {
  expect(useAuthStore.getState().isAuthenticated).toBe(false);
};

export const waitForElementText = async (testId: string, expectedText: string) => {
  await waitFor(() => {
    assertElementText(testId, expectedText);
  });
};

export const waitForElementToExist = async (testId: string) => {
  await waitFor(() => {
    assertElementExists(testId);
  });
};

export const assertStoreState = (store: any, key: string, expectedValue: any) => {
  expect(store.getState()[key]).toEqual(expectedValue);
};

export const assertFetchWasCalled = (url: string, options?: any) => {
  expect(fetch).toHaveBeenCalledWith(url, options);
};

export const assertOptimizationResults = (testId: string, costReduction: string, latencyImprovement: string) => {
  const expectedText = `Cost reduced by ${costReduction}, Latency improved by ${latencyImprovement}`;
  assertElementText(testId, expectedText);
};