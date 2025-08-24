/**
 * Store Test Utilities
 * Provides common utilities for testing Zustand stores
 */

import { jest } from '@jest/globals';
import { renderHook } from '@testing-library/react';
import { useChatStore } from '@/store/chat';
import { Message, MessageRole } from '@/types/unified';

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

export class ChatStoreTestUtils {
  static initializeStore() {
    return renderHook(() => useChatStore());
  }

  static createMockMessage(
    id: string,
    role: MessageRole = 'user',
    content: string = 'Test message',
    options: Partial<Message> = {}
  ): Message {
    return {
      id,
      role,
      content,
      type: role === 'user' ? 'user' : 'ai',
      created_at: new Date().toISOString(),
      displayed_to_user: true,
      timestamp: Date.now(),
      ...options
    };
  }

  static createMockAiMessage(id: string, content: string = 'AI response'): Message {
    return this.createMockMessage(id, 'assistant', content);
  }

  static createMockUserMessage(id: string, content: string = 'User message'): Message {
    return this.createMockMessage(id, 'user', content);
  }

  static createMockSystemMessage(id: string, content: string = 'System message'): Message {
    return this.createMockMessage(id, 'system', content);
  }

  static createMockErrorMessage(id: string, error: string = 'Test error'): Message {
    return {
      id,
      role: 'system',
      content: error,
      type: 'error',
      created_at: new Date().toISOString(),
      displayed_to_user: true,
      timestamp: Date.now(),
      error
    };
  }

  static waitForState(hook: any, predicate: (state: any) => boolean, timeout = 1000) {
    return new Promise((resolve, reject) => {
      const startTime = Date.now();
      const checkState = () => {
        if (predicate(hook.result.current)) {
          resolve(hook.result.current);
        } else if (Date.now() - startTime > timeout) {
          reject(new Error('Timeout waiting for state condition'));
        } else {
          setTimeout(checkState, 10);
        }
      };
      checkState();
    });
  }
}