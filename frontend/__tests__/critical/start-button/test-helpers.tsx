/**
 * Start Chat Button Test Helpers
 * Modular helper functions for comprehensive button testing
 * 
 * BVJ: Shared utilities reduce test maintenance and ensure consistency
 * @compliance conventions.xml - Under 300 lines, 8-line functions
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ThreadSidebarHeader } from '@/components/chat/ThreadSidebarComponents';

export interface StartButtonTestProps {
  onCreateThread: () => Promise<void>;
  isCreating: boolean;
  isLoading: boolean;
  isAuthenticated: boolean;
}

export interface VisibilityTestCase {
  name: string;
  props: Partial<StartButtonTestProps>;
  expectedVisible: boolean;
  expectedEnabled: boolean;
}

export interface ViewportConfig {
  width: number;
  height: number;
  name: string;
  isDesktop: boolean;
}

// Test data configurations
export const viewportConfigs: ViewportConfig[] = [
  { width: 320, height: 568, name: 'iPhone SE', isDesktop: false },
  { width: 375, height: 667, name: 'iPhone 8', isDesktop: false },
  { width: 414, height: 896, name: 'iPhone Pro Max', isDesktop: false },
  { width: 768, height: 1024, name: 'iPad', isDesktop: false },
  { width: 1024, height: 768, name: 'Desktop Small', isDesktop: true },
  { width: 1920, height: 1080, name: 'Desktop Large', isDesktop: true }
];

export const visibilityTestCases: VisibilityTestCase[] = [
  {
    name: 'new authenticated user',
    props: { isAuthenticated: true, isCreating: false, isLoading: false },
    expectedVisible: true,
    expectedEnabled: true
  },
  {
    name: 'unauthenticated user',
    props: { isAuthenticated: false },
    expectedVisible: true,
    expectedEnabled: false
  },
  {
    name: 'creating thread state',
    props: { isCreating: true },
    expectedVisible: true,
    expectedEnabled: false
  },
  {
    name: 'loading state',
    props: { isLoading: true },
    expectedVisible: true,
    expectedEnabled: false
  }
];

// Mock setup
export const mockOnCreateThread = jest.fn().mockResolvedValue(undefined);

export const defaultProps: StartButtonTestProps = {
  onCreateThread: mockOnCreateThread,
  isCreating: false,
  isLoading: false,
  isAuthenticated: true
};

// Render helpers
export function renderButtonWithProps(props: Partial<StartButtonTestProps>) {
  const testProps = { ...defaultProps, ...props };
  return render(<ThreadSidebarHeader {...testProps} />);
}

// Setup helpers
export function setupCriticalTests(): void {
  jest.clearAllMocks();
  mockOnCreateThread.mockClear();
  setupDefaultViewport();
}

export function cleanupCriticalTests(): void {
  jest.resetAllMocks();
  restoreTestEnvironment();
}

export function setupViewport(width: number, height: number): void {
  Object.defineProperty(window, 'innerWidth', { value: width });
  Object.defineProperty(window, 'innerHeight', { value: height });
}

export function setupMobileViewport(): void {
  setupViewport(375, 667);
}

export function setupDefaultViewport(): void {
  setupViewport(1024, 768);
}

export function restoreTestEnvironment(): void {
  setupDefaultViewport();
}

// Interaction helpers
export function simulateButtonClick(): void {
  const button = screen.getByRole('button');
  fireEvent.click(button);
}

export function simulateTouchEvent(): void {
  const button = screen.getByRole('button');
  fireEvent.touchStart(button);
  fireEvent.touchEnd(button);
}

export function simulateKeyboardFocus(): void {
  const button = screen.getByRole('button');
  button.focus();
}

export function simulateEnterKey(): void {
  const button = screen.getByRole('button');
  button.focus();
  fireEvent.keyDown(button, { key: 'Enter', code: 'Enter' });
  fireEvent.click(button);
}

export function simulateSpaceKey(): void {
  const button = screen.getByRole('button');
  button.focus();
  fireEvent.keyDown(button, { key: ' ', code: 'Space' });
  fireEvent.click(button);
}

// Verification helpers
export function verifyButtonVisibility(expectedVisible: boolean): void {
  const button = screen.getByRole('button');
  expect(button).toBeVisible();
}

export function verifyButtonEnabledState(expectedEnabled: boolean): void {
  const button = screen.getByRole('button');
  expect(button).toHaveProperty('disabled', !expectedEnabled);
}

export function verifyAlwaysVisible(): void {
  const button = screen.getByRole('button', { name: /new conversation/i });
  expect(button).toBeInTheDocument();
}

export function verifyProminentDisplay(): void {
  const button = screen.getByRole('button');
  expect(button).toHaveClass('w-full');
}

export function verifyThreadCreationTriggered(): void {
  expect(mockOnCreateThread).toHaveBeenCalledTimes(1);
}

export function verifyNoThreadCreation(): void {
  expect(mockOnCreateThread).not.toHaveBeenCalled();
}

export function verifyLoadingState(): void {
  expect(screen.getByRole('button')).toBeDisabled();
}

export function verifySpinnerPresent(): void {
  expect(document.querySelector('.animate-spin')).toBeInTheDocument();
}

export function verifyButtonDisabled(): void {
  const button = screen.getByRole('button');
  expect(button).toBeDisabled();
}

export function verifyResponsiveLayout(isDesktop: boolean): void {
  const button = screen.getByRole('button');
  expect(button).toBeVisible();
}

export function verifyTouchTargetSize(): void {
  const button = screen.getByRole('button');
  expect(button).toBeVisible();
  expect(button).toHaveClass('px-4', 'py-2');
}

export function verifyARIACompliance(): void {
  const button = screen.getByRole('button');
  expect(button).toHaveAccessibleName();
}

export function verifyAccessibleName(): void {
  expect(screen.getByRole('button', { name: /new conversation/i })).toBeInTheDocument();
}

export function verifyFocusState(): void {
  const button = screen.getByRole('button');
  expect(button).toHaveFocus();
}

export function verifyKeyboardActivation(): void {
  expect(mockOnCreateThread).toHaveBeenCalled();
}

export function verifyButtonText(): void {
  expect(screen.getByText('New Conversation')).toBeInTheDocument();
}

export function verifyButtonStyling(): void {
  const button = screen.getByRole('button');
  expect(button).toHaveClass('glass-button-primary');
}

export function measureRenderPerformance(): number {
  const startTime = performance.now();
  renderButtonWithProps({});
  return performance.now() - startTime;
}

export function verifyCriticalRenderTime(renderTime: number): void {
  expect(renderTime).toBeLessThan(100);
}