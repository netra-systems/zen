/**
 * Test utilities for ChatHistorySection tests
 * Provides reusable utility functions for test scenarios
 */

import React from 'react';

// Utility for finding thread elements in DOM
export const findThreadElement = (container: HTMLElement, title: string) => {
  const threadElement = Array.from(container.querySelectorAll('[data-testid*="thread"]')).find(
    el => el.textContent?.includes(title)
  );
  return threadElement as HTMLElement;
};

// Utility for mocking user interactions
export const mockUserEvent = {
  click: (element: HTMLElement) => {
    element.click();
  },
  
  hover: (element: HTMLElement) => {
    element.classList.add('hover');
  }
};

// Utility for date formatting tests
export const getExpectedDateFormat = (timestamp: number) => {
  const date = new Date(timestamp * 1000);
  const now = new Date();
  const diffInMs = now.getTime() - date.getTime();
  const diffInHours = diffInMs / (1000 * 60 * 60);

  if (diffInHours < 24) {
    return 'Today';
  } else if (diffInHours < 48) {
    return 'Yesterday';
  } else {
    return date.toLocaleDateString();
  }
};

// Utility to wait for authentication state
export const waitForAuthState = async (isAuthenticated: boolean = true) => {
  // Allow time for auth state to propagate
  await new Promise(resolve => setTimeout(resolve, 0));
  return isAuthenticated;
};

// Utility to find elements by role with custom text matching
export const findElementByRoleAndText = (
  container: HTMLElement, 
  role: string, 
  textMatch: string | RegExp
) => {
  const elements = Array.from(container.querySelectorAll(`[role="${role}"]`));
  return elements.find(el => {
    const text = el.textContent || '';
    if (typeof textMatch === 'string') {
      return text.includes(textMatch);
    }
    return textMatch.test(text);
  }) as HTMLElement;
};

// Utility to simulate delete confirmation
export const simulateDeleteConfirmation = () => {
  // Mock window.confirm to return true
  const originalConfirm = window.confirm;
  window.confirm = jest.fn(() => true);
  return () => {
    window.confirm = originalConfirm;
  };
};

// Utility to simulate delete cancellation
export const simulateDeleteCancellation = () => {
  const originalConfirm = window.confirm;
  window.confirm = jest.fn(() => false);
  return () => {
    window.confirm = originalConfirm;
  };
};

// Setup helpers for common test scenarios
export const setupStoreForEmptyState = (testSetup: any) => {
  testSetup.configureStoreMocks({ 
    threads: [], 
    currentThreadId: null 
  });
};

export const setupStoreForCurrentThread = (testSetup: any, threadId: string) => {
  testSetup.configureStoreMocks({ 
    currentThreadId: threadId 
  });
};

export const setupStoreWithCustomThreads = (testSetup: any, threads: any[]) => {
  testSetup.configureStoreMocks({ 
    threads, 
    currentThreadId: threads[0]?.id || null 
  });
};

// Action helpers for common interactions
export const renderWithTestSetup = (Component: React.ComponentType, testSetup: any) => {
  const { render } = require('@testing-library/react');
  return render(React.createElement(Component));
};

export const expectBasicStructure = (screen: any) => {
  expect(screen.getByText('Chat History')).toBeInTheDocument();
};

export const expectThreadsRendered = (screen: any, threadTitles: string[]) => {
  threadTitles.forEach(title => {
    expect(screen.getByText(title)).toBeInTheDocument();
  });
};

export const expectEmptyState = (screen: any) => {
  expect(screen.getByText('No conversations yet')).toBeInTheDocument();
};

export const expectActiveThread = (screen: any, threadTitle: string) => {
  const activeThread = screen.getByText(threadTitle).closest('div[class*="group"]');
  expect(activeThread).toHaveClass('bg-accent');
};

export const createThreadWithTitle = (baseThread: any, title: string | null) => {
  return { ...baseThread, title };
};

export const expectUntitledThread = (screen: any) => {
  expect(screen.getByText('Untitled')).toBeInTheDocument();
};

export const expectSpecificThreadTitle = (screen: any, title: string) => {
  expect(screen.getByText(title)).toBeInTheDocument();
};

export const expectMultipleThreadTitles = (screen: any, titles: string[]) => {
  titles.forEach(title => {
    expect(screen.getByText(title)).toBeInTheDocument();
  });
};

export const expectThreadStructure = (screen: any) => {
  const container = screen.getByText('Chat History').closest('.flex-col');
  expect(container).toBeInTheDocument();
};