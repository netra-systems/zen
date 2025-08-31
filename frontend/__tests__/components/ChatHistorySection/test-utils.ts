/**
 * Test utilities for ChatHistorySection tests
 * Exports all utility functions needed by the test suites
 */

// Re-export all utilities from testUtils.tsx
export * from './testUtils';

// Additional missing utilities that tests expect
export const findChatHistoryContainer = (screen: any) => {
  return screen.getByTestId('chat-history') || screen.getByRole('navigation');
};

export const findThreadContainer = (screen: any, title?: string) => {
  if (title) {
    return screen.getByText(title).closest('[data-testid*="thread"]');
  }
  return screen.getByTestId('thread-container') || screen.getAllByRole('button')[0];
};

export const validateSemanticStructure = (screen: any) => {
  expect(screen.getByRole('navigation')).toBeInTheDocument();
};

export const expectLoadingState = (screen: any) => {
  expect(screen.getByText(/loading/i) || screen.getByTestId('loading')).toBeInTheDocument();
};

export const mockConsoleError = () => {
  const originalError = console.error;
  const mockError = jest.fn();
  console.error = mockError;
  return { mockError, restore: () => { console.error = originalError; } };
};

export const mockWindowConfirm = (returnValue: boolean = true) => {
  const originalConfirm = window.confirm;
  window.confirm = jest.fn(() => returnValue);
  return { restore: () => { window.confirm = originalConfirm; } };
};

export const findSearchInput = (screen: any) => {
  return screen.getByPlaceholderText(/search/i) || screen.getByTestId('search-input');
};

export const createLargeThreadSet = (size: number = 50) => {
  return Array.from({ length: size }, (_, i) => ({
    id: `thread-${i}`,
    title: `Thread ${i + 1}`,
    messages: [],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString()
  }));
};

export const createThreadWithSpecialChars = () => ({
  id: 'special-thread',
  title: 'Thread with émojis 🚀 and spëciál chärs',
  messages: [],
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString()
});

export const createMalformedThread = () => ({
  id: null,
  title: undefined,
  messages: null,
  createdAt: 'invalid-date',
  updatedAt: ''
});

export const createThreadWithTimestamp = (timestamp: number) => ({
  id: `timestamp-thread-${timestamp}`,
  title: `Thread ${timestamp}`,
  messages: [],
  createdAt: new Date(timestamp).toISOString(),
  updatedAt: new Date(timestamp).toISOString()
});

export const findMessageIcons = (screen: any) => {
  return screen.getAllByTestId('message-icon');
};

export const simulateClick = (element: HTMLElement) => {
  element.click();
};