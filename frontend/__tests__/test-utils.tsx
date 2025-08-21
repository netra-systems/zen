/**
 * Common Test Utilities
 * Central export point for all test utilities
 */

import React from 'react';
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import WS from 'jest-websocket-mock';

// Re-export React and testing utilities
export { React, render, screen, waitFor, fireEvent, act, userEvent };

// Re-export WebSocket mock
export { default as WS } from 'jest-websocket-mock';

// Test timeouts
export const TEST_TIMEOUTS = {
  SHORT: 1000,
  MEDIUM: 5000,
  LONG: 10000,
  VERY_LONG: 30000
};

/**
 * Setup test environment
 */
export function setupTestEnvironment() {
  // Clear all mocks
  jest.clearAllMocks();
  
  // Clear WebSocket mocks
  WS.clean();
  
  // Reset DOM
  document.body.innerHTML = '';
  
  // Setup any global mocks
  global.fetch = jest.fn();
  
  // Mock console methods to reduce noise
  jest.spyOn(console, 'error').mockImplementation(() => {});
  jest.spyOn(console, 'warn').mockImplementation(() => {});
}

/**
 * Cleanup test environment
 */
export function cleanupTestEnvironment() {
  // Clean WebSocket mocks
  WS.clean();
  
  // Restore mocks
  jest.restoreAllMocks();
  
  // Clear all timers
  jest.clearAllTimers();
  
  // Clear DOM
  document.body.innerHTML = '';
}

/**
 * Create mock WebSocket server
 */
export function createMockWebSocketServer(url: string = 'ws://localhost:8000/websocket') {
  const server = new WS(url);
  
  return {
    server,
    sendMessage: (message: any) => {
      server.send(JSON.stringify(message));
    },
    expectMessage: async (expectedMessage: any) => {
      await server.nextMessage;
      const messages = server.messages;
      const lastMessage = messages[messages.length - 1];
      expect(JSON.parse(lastMessage as string)).toEqual(expectedMessage);
    },
    close: () => {
      server.close();
    }
  };
}

/**
 * Wait for async updates
 */
export async function waitForAsync(ms: number = 0) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Flush all promises
 */
export async function flushPromises() {
  return new Promise(resolve => setImmediate(resolve));
}

// Export test providers from existing file
export { renderWithProviders } from './test-utils/render-with-providers';
export { TestProviders } from './setup/test-providers';