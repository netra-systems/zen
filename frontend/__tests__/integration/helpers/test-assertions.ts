/**
 * Test Assertion Helpers
 * Reusable assertion functions for integration tests
 */

import { waitFor } from '@testing-library/react';

export const assertTextContent = async (element: HTMLElement, expectedText: string) => {
  await waitFor(() => {
    expect(element).toHaveTextContent(expectedText);
  });
};

export const assertElementExists = (element: HTMLElement | null) => {
  expect(element).toBeInTheDocument();
};

export const assertStoreState = (store: any, property: string, expectedValue: any) => {
  expect(store.getState()[property]).toBe(expectedValue);
};

export const assertAuthState = (isAuthenticated: boolean, token: string | null = null) => {
  const authStore = require('@/store/authStore').useAuthStore;
  expect(authStore.getState().isAuthenticated).toBe(isAuthenticated);
  if (token !== null) expect(authStore.getState().token).toBe(token);
};

export const assertMessageCount = (expectedCount: number) => {
  const chatStore = require('@/store/chatStore').useChatStore;
  expect(chatStore.getState().messages).toHaveLength(expectedCount);
};

export const assertThreadCount = (expectedCount: number) => {
  const threadStore = require('@/store/threadStore').useThreadStore;
  expect(threadStore.getState().threads).toHaveLength(expectedCount);
};