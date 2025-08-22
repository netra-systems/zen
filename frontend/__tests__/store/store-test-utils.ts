/**
 * Store Test Utilities
 * Provides common utilities for testing Zustand stores
 */

import { jest } from '@jest/globals';

export class GlobalTestUtils {
  static setupStoreTestEnvironment() {
    // Create a real storage implementation for better Zustand compatibility
    let store: Record<string, string> = {};
    
    const mockStorage = {
      getItem: jest.fn((key: string) => store[key] || null),
      setItem: jest.fn((key: string, value: string) => {
        store[key] = value;
      }),
      removeItem: jest.fn((key: string) => {
        delete store[key];
      }),
      clear: jest.fn(() => {
        store = {};
      }),
      key: jest.fn((index: number) => Object.keys(store)[index] || null),
      get length() { return Object.keys(store).length; }
    };
    
    // Set up proper window.localStorage replacement
    Object.defineProperty(window, 'localStorage', {
      value: mockStorage,
      writable: true,
      configurable: true
    });
    
    // Also set up sessionStorage
    Object.defineProperty(window, 'sessionStorage', {
      value: mockStorage,
      writable: true,
      configurable: true
    });
    
    return {
      mockStorage
    };
  }
  
  static cleanupStoreTestEnvironment() {
    jest.clearAllMocks();
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.clear();
    }
    if (typeof window !== 'undefined' && window.sessionStorage) {
      window.sessionStorage.clear();
    }
  }
  
  static createMockStore(initialState = {}) {
    const store = {
      ...initialState,
      setState: jest.fn((partial) => {
        Object.assign(store, typeof partial === 'function' ? partial(store) : partial);
      }),
      getState: jest.fn(() => store),
      subscribe: jest.fn(),
      destroy: jest.fn()
    };
    
    return store;
  }
  
  static waitForStoreUpdate(ms = 100) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}