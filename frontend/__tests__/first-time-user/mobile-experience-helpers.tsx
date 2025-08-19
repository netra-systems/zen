/**
 * Mobile Experience Test Helpers - Business Critical Utilities
 * 
 * BUSINESS VALUE JUSTIFICATION:
 * - Segment: Free → Early (Mobile testing infrastructure)
 * - Business Goal: Reliable mobile test utilities for conversion optimization
 * - Value Impact: Enables accurate measurement of mobile bottlenecks
 * - Revenue Impact: Testing infrastructure supports 60% mobile traffic
 * 
 * ARCHITECTURAL COMPLIANCE: ≤300 lines, functions ≤8 lines
 * Coverage: Mobile interaction utilities, viewport management, gesture simulation
 */

import { fireEvent } from '@testing-library/react';

// Mobile viewport simulation utilities (≤8 lines each)
export const setMobileViewport = (width: number, height: number): void => {
  Object.defineProperty(window, 'innerWidth', { value: width, writable: true });
  Object.defineProperty(window, 'innerHeight', { value: height, writable: true });
  window.dispatchEvent(new Event('resize'));
};

export const simulateTouchEvent = (element: Element, type: string, coords = { x: 100, y: 100 }): void => {
  fireEvent[type](element, {
    touches: [{ clientX: coords.x, clientY: coords.y, identifier: 0 }]
  });
};

export const simulateSwipe = (element: Element, startX: number, endX: number): void => {
  simulateTouchEvent(element, 'touchStart', { x: startX, y: 100 });
  simulateTouchEvent(element, 'touchMove', { x: endX, y: 100 });
  simulateTouchEvent(element, 'touchEnd', { x: endX, y: 100 });
};

export const simulatePinch = (element: Element): void => {
  fireEvent.touchStart(element, {
    touches: [
      { clientX: 100, clientY: 100, identifier: 0 },
      { clientX: 200, clientY: 200, identifier: 1 }
    ]
  });
};

// Mock setup utilities (≤8 lines each)
export const createMockUser = () => ({
  id: 'test-user',
  email: 'test@example.com',
  name: 'Test User',
  role: 'free' as const
});

export const setupMockVibration = (): jest.Mock => {
  const mockVibrate = jest.fn();
  Object.defineProperty(navigator, 'vibrate', { value: mockVibrate });
  return mockVibrate;
};

export const setupMockMatchMedia = (matches: boolean = true): void => {
  Object.defineProperty(window, 'matchMedia', {
    value: jest.fn(() => ({ matches }))
  });
};

// Performance tracking utilities (≤8 lines each)
export const measureInteractionTime = (operation: () => void): number => {
  const startTime = performance.now();
  operation();
  return performance.now() - startTime;
};

export const expectPerformantInteraction = (duration: number, maxMs: number = 100): void => {
  expect(duration).toBeLessThan(maxMs);
};

// Gesture simulation utilities (≤8 lines each)
export const simulateLongPress = async (element: Element, duration: number = 500): Promise<void> => {
  simulateTouchEvent(element, 'touchStart');
  await new Promise(resolve => setTimeout(resolve, duration));
  simulateTouchEvent(element, 'touchEnd');
};

export const simulateRapidTouches = (element: Element, count: number = 5): void => {
  for (let i = 0; i < count; i++) {
    simulateTouchEvent(element, 'touchStart');
  }
};

// Device simulation utilities (≤8 lines each)
export const simulateHighDensityDisplay = (ratio: number = 3): void => {
  Object.defineProperty(window, 'devicePixelRatio', { value: ratio });
};

export const simulatePortraitOrientation = (): void => {
  setMobileViewport(375, 667);
};

export const simulateLandscapeOrientation = (): void => {
  setMobileViewport(667, 375);
};

export const simulateSmallScreen = (): void => {
  setMobileViewport(320, 568); // iPhone 5
};

// Test verification utilities (≤8 lines each)
export const expectTouchTargetSize = (element: Element, minSize: number = 44): void => {
  const rect = element.getBoundingClientRect();
  expect(Math.max(rect.width, rect.height)).toBeGreaterThanOrEqual(minSize);
};

export const expectAccessibleContent = (element: Element): void => {
  expect(element).toHaveAttribute('aria-label');
};

export const expectResponsiveClasses = (element: Element): void => {
  const classes = element.className;
  const hasResponsive = /\b(sm:|md:|lg:|xl:)/.test(classes);
  expect(hasResponsive || classes.includes('w-full')).toBe(true);
};

// Common mobile breakpoints
export const MOBILE_BREAKPOINTS = {
  IPHONE_SE: { width: 375, height: 667 },
  IPHONE_12: { width: 390, height: 844 },
  IPAD: { width: 768, height: 1024 },
  ANDROID_SMALL: { width: 360, height: 640 },
  ANDROID_LARGE: { width: 412, height: 892 }
};

// Touch interaction patterns
export const TOUCH_PATTERNS = {
  TAP: { duration: 100 },
  LONG_PRESS: { duration: 500 },
  DOUBLE_TAP: { duration: 50, interval: 200 },
  SWIPE: { distance: 100, duration: 200 }
};