/**
 * Store Test Utilities
 * Provides common utilities for testing Zustand stores
 */

import { jest } from '@jest/globals';

export class GlobalTestUtils {
  static setupStoreTestEnvironment() {
    // Mock localStorage
    const mockStorage = {
      getItem: jest.fn(),
      setItem: jest.fn(),
      removeItem: jest.fn(),
      clear: jest.fn(),
      key: jest.fn(),
      length: 0
    };
    
    Object.defineProperty(window, 'localStorage', {
      value: mockStorage,
      writable: true
    });
    
    // Mock sessionStorage
    Object.defineProperty(window, 'sessionStorage', {
      value: mockStorage,
      writable: true
    });
    
    return {
      mockStorage
    };
  }
  
  static cleanupStoreTestEnvironment() {
    jest.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
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