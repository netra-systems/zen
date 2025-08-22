/**
 * Unified Test Utilities
 * Shared testing utilities for frontend integration tests
 */

import React from 'react';
import { render, RenderOptions, RenderResult } from '@testing-library/react';
import { TestProviders } from '../setup/test-providers';

export interface RenderWithProvidersOptions extends Omit<RenderOptions, 'wrapper'> {
  initialState?: any;
}

export function renderWithProviders(
  ui: React.ReactElement,
  options: RenderWithProvidersOptions = {}
): RenderResult {
  const { initialState, ...renderOptions } = options;

  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <TestProviders initialState={initialState}>
      {children}
    </TestProviders>
  );

  return render(ui, { wrapper: Wrapper, ...renderOptions });
}

export async function waitForElement(testId: string, timeout = 3000): Promise<HTMLElement> {
  return new Promise((resolve, reject) => {
    const timeoutId = setTimeout(() => {
      reject(new Error(`Element with test-id "${testId}" not found within ${timeout}ms`));
    }, timeout);

    const interval = setInterval(() => {
      const element = document.querySelector(`[data-testid="${testId}"]`) as HTMLElement;
      if (element) {
        clearTimeout(timeoutId);
        clearInterval(interval);
        resolve(element);
      }
    }, 100);
  });
}

export async function safeAsync<T>(fn: () => Promise<T> | T): Promise<T> {
  try {
    return await fn();
  } catch (error) {
    console.error('safeAsync error:', error);
    throw error;
  }
}

export function resetAllMocks(): void {
  jest.clearAllMocks();
  jest.clearAllTimers();
}

export function flushPromises(): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, 0));
}

export function mockFetch(response: any): void {
  (global.fetch as jest.Mock) = jest.fn(() =>
    Promise.resolve({
      ok: true,
      json: () => Promise.resolve(response),
      text: () => Promise.resolve(JSON.stringify(response)),
    })
  );
}

export function createMockWebSocket(): WebSocket {
  return {
    send: jest.fn(),
    close: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    readyState: WebSocket.OPEN,
    url: 'ws://localhost:8000/ws',
    protocol: '',
    extensions: '',
    bufferedAmount: 0,
    binaryType: 'blob',
    onopen: null,
    onclose: null,
    onerror: null,
    onmessage: null,
    dispatchEvent: jest.fn(),
    CONNECTING: WebSocket.CONNECTING,
    OPEN: WebSocket.OPEN,
    CLOSING: WebSocket.CLOSING,
    CLOSED: WebSocket.CLOSED,
  } as any;
}