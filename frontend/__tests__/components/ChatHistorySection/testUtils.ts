/**
 * Test utilities for ChatHistorySection tests
 * Provides reusable utility functions for test scenarios
 */

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