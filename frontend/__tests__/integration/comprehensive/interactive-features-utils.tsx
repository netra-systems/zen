/**
 * Shared Test Utilities for Interactive Features Tests
 * ULTRA DEEP THINK: Module-based architecture - Interactive test utilities extracted for 450-line compliance
 */

import React from 'react';
import {
  render, waitFor, screen, fireEvent, act,
  setupTestEnvironment, cleanupTestEnvironment,
  createMockWebSocketServer, simulateNetworkDelay,
  waitForUserInteraction, TEST_TIMEOUTS, WS
} from './test-utils';

// Apply Next.js navigation mock
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    refresh: jest.fn(),
    back: jest.fn(),
    forward: jest.fn(),
    pathname: '/',
    query: {},
    asPath: '/',
  }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
}));

// Drag and Drop Utilities
export const createMockDataTransfer = (files: File[]) => ({
  files,
  items: [],
  types: ['Files']
});

export const createTestFile = (name: string = 'test.txt', type: string = 'text/plain') => {
  return new File(['content'], name, { type });
};

export const createImageFile = (name: string = 'test.jpg') => {
  return new File(['image content'], name, { type: 'image/jpeg' });
};

// File validation utilities
export const generateImagePreview = (file: File): Promise<string> => {
  if (!file.type.startsWith('image/')) {
    return Promise.resolve('');
  }
  return new Promise<string>((resolve) => {
    const reader = new FileReader();
    reader.onload = (e) => resolve(e.target?.result as string);
    reader.readAsDataURL(file);
  });
};

// Drag and drop simulation utilities
export const simulateDragOver = (element: HTMLElement, dataTransfer: any) => {
  fireEvent.dragOver(element, { dataTransfer });
};

export const simulateDragLeave = (element: HTMLElement) => {
  fireEvent.dragLeave(element);
};

export const simulateDrop = (element: HTMLElement, dataTransfer: any) => {
  fireEvent.drop(element, { dataTransfer });
};

// Reordering utilities
export const simulateDragStart = (element: HTMLElement) => {
  fireEvent.dragStart(element);
};

export const simulateDragEnd = (element: HTMLElement) => {
  fireEvent.dragEnd(element);
};

// Item reordering logic
export const reorderItems = (items: any[], draggedIndex: number, targetIndex: number) => {
  const newItems = [...items];
  const [removed] = newItems.splice(draggedIndex, 1);
  newItems.splice(targetIndex, 0, removed);
  return newItems;
};

// Scroll Utilities
export const createScrollContainer = (scrollTop: number, scrollHeight: number, clientHeight: number) => {
  return {
    scrollTop,
    scrollHeight,
    clientHeight
  };
};

export const simulateScroll = (element: HTMLElement, scrollProperties: any) => {
  Object.defineProperty(element, 'scrollTop', { value: scrollProperties.scrollTop, writable: true });
  Object.defineProperty(element, 'scrollHeight', { value: scrollProperties.scrollHeight, writable: true });
  Object.defineProperty(element, 'clientHeight', { value: scrollProperties.clientHeight, writable: true });
  fireEvent.scroll(element);
};

// Virtual scrolling utilities
export const calculateVisibleRange = (scrollTop: number, itemHeight: number, containerHeight: number, totalItems: number) => {
  const start = Math.floor(scrollTop / itemHeight);
  const visibleCount = Math.ceil(containerHeight / itemHeight);
  const end = Math.min(start + visibleCount + 5, totalItems);
  return { start, end };
};

export const createVirtualItems = (totalItems: number, prefix: string = 'Virtual Item') => {
  return Array.from({ length: totalItems }, (_, i) => `${prefix} ${i + 1}`);
};

// Animation Utilities
export const createAnimationStage = (stage: number) => ({
  transform: `translateX(${stage * 50}px) scale(${1 + stage * 0.1})`,
  transition: 'all 0.1s ease-in-out',
  opacity: stage > 0 ? 1 : 0.5
});

export const getMovementDirection = (direction: string, distance: number = 100) => {
  const movements = {
    left: { x: -distance, y: 0 },
    right: { x: distance, y: 0 },
    up: { x: 0, y: -distance },
    down: { x: 0, y: distance }
  };
  return movements[direction as keyof typeof movements] || { x: 0, y: 0 };
};

export const calculateNewPosition = (currentPosition: { x: number, y: number }, movement: { x: number, y: number }) => {
  return {
    x: currentPosition.x + movement.x,
    y: currentPosition.y + movement.y
  };
};

// Test setup utilities
export const setupInteractiveTest = () => {
  const server = createMockWebSocketServer();
  setupTestEnvironment(server);
  return server;
};

export const teardownInteractiveTest = () => {
  cleanupTestEnvironment();
};

// Common test patterns
export const expectFileCountChange = (getByTestId: Function, expectedCount: number) => {
  expect(getByTestId('file-count')).toHaveTextContent(`${expectedCount} files`);
};

export const expectItemOrder = (getByTestId: Function, expectedOrder: string[]) => {
  expectedOrder.forEach((expectedText, index) => {
    expect(getByTestId(`item-${index}`)).toHaveTextContent(expectedText);
  });
};

export const expectScrollBehavior = (getByTestId: Function, expectedItems: number) => {
  expect(getByTestId('item-count')).toHaveTextContent(`${expectedItems} items`);
};

// Animation test utilities
export const expectAnimationStage = (getByTestId: Function, expectedStage: number) => {
  expect(getByTestId('animated-element')).toHaveTextContent(`Stage ${expectedStage}`);
};

export const expectAnimationStatus = (getByTestId: Function, expectedStatus: string) => {
  expect(getByTestId('animation-status')).toHaveTextContent(expectedStatus);
};

export const expectGesturePosition = (getByTestId: Function, expectedX: number, expectedY: number) => {
  expect(getByTestId('gesture-element')).toHaveTextContent(`Position: ${expectedX}, ${expectedY}`);
};

// Error simulation utilities
export const simulateDropValidation = (zone: 'valid' | 'invalid', item: string, invalidItems: string[]) => {
  if (zone === 'valid' && invalidItems.includes(item)) {
    throw new Error('Invalid item cannot be placed in valid zone');
  }
  return true;
};

// Item generation utilities
export const generateItems = (count: number, prefix: string = 'Item') => {
  return Array.from({ length: count }, (_, i) => ({
    id: `${i + 1}`,
    text: `${prefix} ${i + 1}`,
    order: i + 1
  }));
};

export const generateScrollItems = (count: number, prefix: string = 'Scroll Item') => {
  return Array.from({ length: count }, (_, i) => `${prefix} ${i + 1}`);
};

// State management utilities
export const saveScrollPosition = (position: number) => {
  localStorage.setItem('scroll_position', position.toString());
};

export const restoreScrollPosition = (): number => {
  const saved = localStorage.getItem('scroll_position');
  return saved ? parseInt(saved) : 0;
};

// Mock item creation for different test scenarios
export const createMockDragItems = () => generateItems(4);
export const createMockScrollItems = () => generateScrollItems(50);
export const createMockVirtualItems = () => createVirtualItems(1000);

// Export test framework utilities
export { 
  React, render, waitFor, screen, fireEvent, act,
  setupTestEnvironment, cleanupTestEnvironment,
  createMockWebSocketServer, simulateNetworkDelay,
  waitForUserInteraction, TEST_TIMEOUTS, WS
};