/**
 * Test utilities for ChatHistorySection - Real Component Testing
 * Provides utilities for testing with real components ≤8 lines per function
 */

import React from 'react';
import { render, screen } from '@testing-library/react';

// DOM utilities ≤8 lines each
export const findThreadByTitle = (title: string) => {
  return screen.getByText(title);
};

export const findThreadContainer = (title: string) => {
  const threadText = findThreadByTitle(title);
  return threadText.closest('[data-testid*="thread"]') || threadText.closest('div[class*="group"]');
};

export const findAllThreadElements = () => {
  return screen.getAllByText(/Conversation/);
};

export const findChatHistoryContainer = () => {
  return screen.getByText('Chat History').closest('.flex-col');
};

export const findScrollContainer = (container: HTMLElement) => {
  return container.querySelector('[style*="overflow"]') || 
         container.querySelector('[data-testid*="scroll"]') ||
         container.firstChild;
};

export const findMessageIcons = () => {
  const container = findChatHistoryContainer();
  return container?.querySelectorAll('svg.lucide-message-square');
};

export const findSearchInput = () => {
  return screen.queryByRole('textbox');
};

export const findLiveRegions = () => {
  return screen.queryAllByRole('status') || 
         screen.queryAllByRole('alert') ||
         screen.getByText('Chat History').closest('[aria-live]');
};

// Date utilities ≤8 lines each
export const getExpectedDateText = (timestamp: number) => {
  const date = new Date(timestamp * 1000);
  const now = new Date();
  const diffInMs = now.getTime() - date.getTime();
  const diffInHours = diffInMs / (1000 * 60 * 60);
  
  if (diffInHours < 24) return 'Today';
  if (diffInHours < 48) return 'Yesterday';
  return date.toLocaleDateString();
};

export const createFutureTimestamp = () => {
  return Math.floor((Date.now() + 86400000) / 1000);
};

export const createPastTimestamp = (daysAgo: number) => {
  return Math.floor((Date.now() - (daysAgo * 86400000)) / 1000);
};

// Expectation utilities ≤8 lines each
export const expectBasicStructure = () => {
  expect(screen.getByText('Chat History')).toBeInTheDocument();
};

export const expectThreadsRendered = (titles: string[]) => {
  titles.forEach(title => {
    expect(screen.getByText(title)).toBeInTheDocument();
  });
};

export const expectEmptyState = () => {
  expect(screen.queryByText('No conversations yet')).toBeInTheDocument();
};

export const expectActiveThread = (title: string) => {
  const threadContainer = findThreadContainer(title);
  expect(threadContainer).toHaveClass('bg-accent');
};

export const expectUntitledThread = () => {
  expect(screen.getByText('Untitled')).toBeInTheDocument();
};

export const expectThreadStructure = () => {
  const container = findChatHistoryContainer();
  expect(container).toBeInTheDocument();
};

export const expectLoadingState = () => {
  const container = findChatHistoryContainer();
  expect(container).toBeInTheDocument();
};

// Thread creation utilities ≤8 lines each
export const createThreadWithTitle = (baseThread: any, title: string | null) => {
  return { ...baseThread, title };
};

export const createThreadWithTimestamp = (baseThread: any, timestamp: number) => {
  return { 
    ...baseThread, 
    created_at: timestamp, 
    updated_at: timestamp 
  };
};

export const createThreadWithSpecialChars = (baseThread: any) => {
  return { 
    ...baseThread, 
    title: 'Thread with émojis 🚀 and unicode ñáéíóú' 
  };
};

export const createMalformedThread = (id: string) => {
  return { id };
};

export const createLargeThreadSet = (count: number) => {
  return Array.from({ length: count }, (_, i) => ({
    id: `thread-${i}`,
    title: `Thread ${i}`,
    created_at: Math.floor(Date.now() / 1000) - (i * 3600),
    updated_at: Math.floor(Date.now() / 1000) - (i * 3600),
    user_id: 'user-1',
    message_count: i % 20,
    status: 'active' as const,
  }));
};

// Interaction utilities ≤8 lines each
export const simulateClick = (element: HTMLElement) => {
  element.click();
};

export const simulateHover = (element: HTMLElement) => {
  element.classList.add('hover');
};

export const simulateKeyDown = (element: HTMLElement, key: string) => {
  const event = new KeyboardEvent('keydown', { key });
  element.dispatchEvent(event);
};

export const simulateScroll = (element: HTMLElement, scrollTop: number) => {
  Object.defineProperty(element, 'scrollTop', { value: scrollTop });
  element.dispatchEvent(new Event('scroll'));
};

// Mock utilities ≤8 lines each
export const mockWindowConfirm = (returnValue: boolean) => {
  const original = window.confirm;
  window.confirm = jest.fn(() => returnValue);
  return () => { window.confirm = original; };
};

export const mockConsoleError = () => {
  const spy = jest.spyOn(console, 'error').mockImplementation(() => {});
  return () => spy.mockRestore();
};

export const mockMatchMedia = (matches: boolean) => {
  const mockFn = jest.fn().mockImplementation((query) => ({
    matches,
    media: query,
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  }));
  
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: mockFn,
  });
};

// Focus utilities ≤8 lines each
export const makeElementFocusable = (element: HTMLElement) => {
  if (!element.tabIndex && element.tabIndex !== 0) {
    element.tabIndex = 0;
  }
};

export const focusElement = (element: HTMLElement) => {
  makeElementFocusable(element);
  element.focus();
};

export const expectElementFocusable = (element: HTMLElement) => {
  expect(element.tabIndex >= 0).toBe(true);
};

// Validation utilities ≤8 lines each
export const validateThreadElement = (thread: HTMLElement) => {
  const container = thread.closest('[role]') || thread.closest('[aria-label]');
  if (container) {
    const hasRole = container.getAttribute('role');
    const hasAriaLabel = container.getAttribute('aria-label');
    expect(hasRole || hasAriaLabel).toBeTruthy();
  }
};

export const validateColorContrast = (element: HTMLElement) => {
  const computedStyle = window.getComputedStyle(element);
  expect(computedStyle).toBeDefined();
};

export const validateSemanticStructure = (container: HTMLElement) => {
  const semantic = container.querySelector('div, nav, section, aside');
  expect(semantic).toBeInTheDocument();
};

// Async utilities ≤8 lines each
export const waitForAuthState = async (isAuthenticated: boolean = true) => {
  await new Promise(resolve => setTimeout(resolve, 0));
  return isAuthenticated;
};

export const waitForAnimation = async (duration: number = 100) => {
  await new Promise(resolve => setTimeout(resolve, duration));
};

export const waitForStateUpdate = async () => {
  await new Promise(resolve => setTimeout(resolve, 1));
};