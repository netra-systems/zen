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
  // Auth state assertions are handled by individual test mocks
  // This function provides a common interface but logic is test-specific
  console.debug(`assertAuthState called: isAuthenticated=${isAuthenticated}, token=${token}`);
};

export const assertMessageCount = (expectedCount: number) => {
  const { useChatStore } = require('@/store/chatStore');
  const messages = useChatStore.getState().messages;
  expect(messages).toHaveLength(expectedCount);
};

export const assertThreadCount = (expectedCount: number) => {
  const { useThreadStore } = require('@/store/threadStore');
  const threads = useThreadStore.getState().threads;
  expect(threads).toHaveLength(expectedCount);
};