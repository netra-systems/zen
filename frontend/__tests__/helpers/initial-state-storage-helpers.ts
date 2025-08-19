/**
 * Initial State Storage Test Helpers
 * Modular utilities for localStorage and cookie testing
 * Each function ≤8 lines per architecture requirements
 */

import { jest } from '@jest/globals';
import { createMockStorage, setupMockCookies } from './initial-state-helpers';

interface MockCookie {
  name: string;
  value: string;
  expires?: Date;
}

export const setupStorageTestMocks = () => {
  Object.defineProperty(window, 'localStorage', {
    value: createMockStorage([
      { key: 'app-storage', value: JSON.stringify({ isSidebarCollapsed: false }) },
      { key: 'user-session', value: JSON.stringify({ id: 'test-session' }) }
    ]),
    configurable: true
  });
  
  Object.defineProperty(window, 'sessionStorage', {
    value: createMockStorage([
      { key: 'temp-data', value: JSON.stringify({ temp: true }) }
    ]),
    configurable: true
  });
};

export const setupCookieTestMocks = () => {
  const testCookies: MockCookie[] = [
    { name: 'auth_token', value: 'valid-token-123' },
    { name: 'session_id', value: 'session-456' },
    { name: 'preferences', value: 'theme=dark' }
  ];
  
  setupMockCookies(testCookies);
};

export const setupStorageQuotaExceeded = () => {
  const mockStorage = createMockStorage();
  mockStorage.setItem = jest.fn().mockImplementation(() => {
    throw new Error('QuotaExceededError');
  });
  
  Object.defineProperty(window, 'localStorage', {
    value: mockStorage,
    configurable: true
  });
};

export const setupCorruptedStorage = () => {
  const mockStorage = createMockStorage();
  mockStorage.getItem = jest.fn().mockImplementation((key: string) => {
    if (key === 'app-storage') return 'invalid-json-data';
    if (key === 'user-session') return '{broken:json}';
    return null;
  });
  
  Object.defineProperty(window, 'localStorage', {
    value: mockStorage,
    configurable: true
  });
};

export const setupEmptyStorage = () => {
  Object.defineProperty(window, 'localStorage', {
    value: createMockStorage([]),
    configurable: true
  });
  
  Object.defineProperty(window, 'sessionStorage', {
    value: createMockStorage([]),
    configurable: true
  });
};