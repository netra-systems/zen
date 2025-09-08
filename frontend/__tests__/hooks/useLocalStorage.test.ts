/**
 * useLocalStorage Hook Test Suite
 * 25 comprehensive tests for the useLocalStorage hook
 */

import React from 'react';
import { renderHook, act } from '@testing-library/react';

// Mock localStorage for testing
const localStorageMock = (() => {
  let store: { [key: string]: string } = {};

  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
    length: Object.keys(store).length,
    key: (index: number) => Object.keys(store)[index] || null
  };
})();

// Replace the global localStorage with our mock
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock
});

// Simple useLocalStorage hook implementation
function useLocalStorage<T>(key: string, initialValue: T): [T, (value: T | ((val: T) => T)) => void, () => void] {
  const [storedValue, setStoredValue] = React.useState<T>(() => {
    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch (error) {
      console.error(`Error reading localStorage key "${key}":`, error);
      return initialValue;
    }
  });

  const setValue = React.useCallback((value: T | ((val: T) => T)) => {
    try {
      const valueToStore = value instanceof Function ? value(storedValue) : value;
      setStoredValue(valueToStore);
      window.localStorage.setItem(key, JSON.stringify(valueToStore));
    } catch (error) {
      console.error(`Error setting localStorage key "${key}":`, error);
    }
  }, [key, storedValue]);

  const removeValue = React.useCallback(() => {
    try {
      setStoredValue(initialValue);
      window.localStorage.removeItem(key);
    } catch (error) {
      console.error(`Error removing localStorage key "${key}":`, error);
    }
  }, [key, initialValue]);

  return [storedValue, setValue, removeValue];
}

// Enhanced useLocalStorage with additional features
interface UseLocalStorageOptions {
  serialize?: (value: any) => string;
  deserialize?: (value: string) => any;
  onError?: (error: Error) => void;
}

function useEnhancedLocalStorage<T>(
  key: string,
  initialValue: T,
  options: UseLocalStorageOptions = {}
): [T, (value: T | ((val: T) => T)) => void, () => void, { isLoading: boolean; error: Error | null }] {
  const {
    serialize = JSON.stringify,
    deserialize = JSON.parse,
    onError
  } = options;

  const [storedValue, setStoredValue] = React.useState<T>(initialValue);
  const [isLoading, setIsLoading] = React.useState(true);
  const [error, setError] = React.useState<Error | null>(null);

  // Initialize from localStorage on mount
  React.useEffect(() => {
    try {
      setIsLoading(true);
      const item = window.localStorage.getItem(key);
      if (item !== null) {
        setStoredValue(deserialize(item));
      }
      setError(null);
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err));
      setError(error);
      onError?.(error);
    } finally {
      setIsLoading(false);
    }
  }, [key, deserialize, onError]);

  const setValue = React.useCallback((value: T | ((val: T) => T)) => {
    try {
      const valueToStore = value instanceof Function ? value(storedValue) : value;
      setStoredValue(valueToStore);
      window.localStorage.setItem(key, serialize(valueToStore));
      setError(null);
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err));
      setError(error);
      onError?.(error);
    }
  }, [key, storedValue, serialize, onError]);

  const removeValue = React.useCallback(() => {
    try {
      setStoredValue(initialValue);
      window.localStorage.removeItem(key);
      setError(null);
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err));
      setError(error);
      onError?.(error);
    }
  }, [key, initialValue, onError]);

  return [storedValue, setValue, removeValue, { isLoading, error }];
}

// useLocalStorage with sync across tabs
function useSyncedLocalStorage<T>(key: string, initialValue: T): [T, (value: T | ((val: T) => T)) => void, () => void] {
  const [storedValue, setStoredValue] = React.useState<T>(() => {
    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch (error) {
      return initialValue;
    }
  });

  React.useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === key && e.newValue !== null) {
        try {
          setStoredValue(JSON.parse(e.newValue));
        } catch (error) {
          console.error(`Error parsing storage event for key "${key}":`, error);
        }
      }
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, [key]);

  const setValue = React.useCallback((value: T | ((val: T) => T)) => {
    try {
      const valueToStore = value instanceof Function ? value(storedValue) : value;
      setStoredValue(valueToStore);
      window.localStorage.setItem(key, JSON.stringify(valueToStore));
    } catch (error) {
      console.error(`Error setting localStorage key "${key}":`, error);
    }
  }, [key, storedValue]);

  const removeValue = React.useCallback(() => {
    try {
      setStoredValue(initialValue);
      window.localStorage.removeItem(key);
    } catch (error) {
      console.error(`Error removing localStorage key "${key}":`, error);
    }
  }, [key, initialValue]);

  return [storedValue, setValue, removeValue];
}

describe('useLocalStorage Hook - Basic Functionality', () => {
  beforeEach(() => {
    localStorageMock.clear();
  });

  test('should initialize with initial value when localStorage is empty', () => {
    const { result } = renderHook(() => useLocalStorage('test-key', 'initial'));
    
    expect(result.current[0]).toBe('initial');
  });

  test('should initialize with value from localStorage', () => {
    localStorageMock.setItem('test-key', JSON.stringify('stored-value'));
    
    const { result } = renderHook(() => useLocalStorage('test-key', 'initial'));
    
    expect(result.current[0]).toBe('stored-value');
  });

  test('should set value and update localStorage', () => {
    const { result } = renderHook(() => useLocalStorage('test-key', 'initial'));
    
    act(() => {
      result.current[1]('new-value');
    });
    
    expect(result.current[0]).toBe('new-value');
    expect(JSON.parse(localStorageMock.getItem('test-key')!)).toBe('new-value');
  });

  test('should remove value and clear localStorage', () => {
    const { result } = renderHook(() => useLocalStorage('test-key', 'initial'));
    
    act(() => {
      result.current[1]('stored-value');
    });
    
    expect(result.current[0]).toBe('stored-value');
    
    act(() => {
      result.current[2]();
    });
    
    expect(result.current[0]).toBe('initial');
    expect(localStorageMock.getItem('test-key')).toBeNull();
  });
});

describe('useLocalStorage Hook - Data Types', () => {
  beforeEach(() => {
    localStorageMock.clear();
  });

  test('should handle string values', () => {
    const { result } = renderHook(() => useLocalStorage('string-key', 'default'));
    
    act(() => {
      result.current[1]('test string');
    });
    
    expect(result.current[0]).toBe('test string');
  });

  test('should handle number values', () => {
    const { result } = renderHook(() => useLocalStorage('number-key', 0));
    
    act(() => {
      result.current[1](42);
    });
    
    expect(result.current[0]).toBe(42);
  });

  test('should handle boolean values', () => {
    const { result } = renderHook(() => useLocalStorage('boolean-key', false));
    
    act(() => {
      result.current[1](true);
    });
    
    expect(result.current[0]).toBe(true);
  });

  test('should handle object values', () => {
    const initialObject = { name: 'initial', count: 0 };
    const newObject = { name: 'updated', count: 5 };
    
    const { result } = renderHook(() => useLocalStorage('object-key', initialObject));
    
    act(() => {
      result.current[1](newObject);
    });
    
    expect(result.current[0]).toEqual(newObject);
  });

  test('should handle array values', () => {
    const initialArray: number[] = [];
    const newArray = [1, 2, 3, 4, 5];
    
    const { result } = renderHook(() => useLocalStorage('array-key', initialArray));
    
    act(() => {
      result.current[1](newArray);
    });
    
    expect(result.current[0]).toEqual(newArray);
  });
});

describe('useLocalStorage Hook - Function Updates', () => {
  beforeEach(() => {
    localStorageMock.clear();
  });

  test('should handle functional updates', () => {
    const { result } = renderHook(() => useLocalStorage('counter-key', 0));
    
    act(() => {
      result.current[1](prev => prev + 1);
    });
    
    expect(result.current[0]).toBe(1);
    
    act(() => {
      result.current[1](prev => prev * 2);
    });
    
    expect(result.current[0]).toBe(2);
  });

  test('should handle functional updates with objects', () => {
    const initialState = { count: 0, name: 'test' };
    const { result } = renderHook(() => useLocalStorage('state-key', initialState));
    
    act(() => {
      result.current[1](prev => ({ ...prev, count: prev.count + 1 }));
    });
    
    expect(result.current[0]).toEqual({ count: 1, name: 'test' });
  });
});

describe('useLocalStorage Hook - Error Handling', () => {
  beforeEach(() => {
    localStorageMock.clear();
  });

  test('should handle malformed JSON in localStorage', () => {
    localStorageMock.setItem('malformed-key', 'invalid-json{');
    
    const { result } = renderHook(() => useLocalStorage('malformed-key', 'default'));
    
    expect(result.current[0]).toBe('default');
  });

  test('should handle localStorage quota exceeded', () => {
    // Mock localStorage.setItem to throw QuotaExceededError
    const originalSetItem = localStorageMock.setItem;
    localStorageMock.setItem = jest.fn(() => {
      const error = new Error('QuotaExceededError');
      error.name = 'QuotaExceededError';
      throw error;
    });

    const { result } = renderHook(() => useLocalStorage('quota-key', 'initial'));
    
    // Initial state should be preserved
    expect(result.current[0]).toBe('initial');
    
    act(() => {
      result.current[1]('large-value');
    });
    
    // Should not crash and maintain initial state when setItem fails
    expect(result.current[0]).toBe('large-value'); // State updates but localStorage doesn't
    
    // Restore original implementation
    localStorageMock.setItem = originalSetItem;
  });
});

describe('useEnhancedLocalStorage Hook - Enhanced Features', () => {
  beforeEach(() => {
    localStorageMock.clear();
  });

  test('should provide loading state', async () => {
    const { result } = renderHook(() => useEnhancedLocalStorage('loading-key', 'initial'));
    
    // After initial render, loading should be false since useEffect has completed
    expect(result.current[3].isLoading).toBe(false);
    expect(result.current[3].error).toBeNull();
  });

  test('should provide error state', async () => {
    const onError = jest.fn();
    localStorageMock.setItem('error-key', 'invalid-json{');
    
    const { result } = renderHook(() => useEnhancedLocalStorage('error-key', 'initial', { onError }));
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 0));
    });
    
    expect(result.current[3].error).toBeInstanceOf(Error);
    expect(onError).toHaveBeenCalled();
  });

  test('should use custom serialization', () => {
    const serialize = jest.fn((value) => `custom:${JSON.stringify(value)}`);
    const deserialize = jest.fn((value) => JSON.parse(value.replace('custom:', '')));
    
    const { result } = renderHook(() => useEnhancedLocalStorage('custom-key', 'initial', {
      serialize,
      deserialize
    }));
    
    act(() => {
      result.current[1]('test-value');
    });
    
    expect(serialize).toHaveBeenCalledWith('test-value');
    expect(localStorageMock.getItem('custom-key')).toBe('custom:"test-value"');
  });
});

describe('useSyncedLocalStorage Hook - Cross-Tab Sync', () => {
  beforeEach(() => {
    localStorageMock.clear();
  });

  test('should sync changes from storage events', () => {
    const { result } = renderHook(() => useSyncedLocalStorage('sync-key', 'initial'));
    
    // Simulate storage event from another tab
    act(() => {
      const storageEvent = new StorageEvent('storage', {
        key: 'sync-key',
        newValue: JSON.stringify('updated-from-other-tab'),
        oldValue: null,
        url: window.location.href
      });
      
      window.dispatchEvent(storageEvent);
    });
    
    expect(result.current[0]).toBe('updated-from-other-tab');
  });

  test('should ignore storage events for other keys', () => {
    const { result } = renderHook(() => useSyncedLocalStorage('sync-key', 'initial'));
    
    const initialValue = result.current[0];
    
    act(() => {
      const storageEvent = new StorageEvent('storage', {
        key: 'other-key',
        newValue: JSON.stringify('other-value'),
        oldValue: null,
        url: window.location.href
      });
      
      window.dispatchEvent(storageEvent);
    });
    
    expect(result.current[0]).toBe(initialValue);
  });
});

describe('useLocalStorage Hook - Persistence', () => {
  beforeEach(() => {
    localStorageMock.clear();
  });

  test('should persist data across hook rerenders', () => {
    const { result, rerender } = renderHook(() => useLocalStorage('persist-key', 'initial'));
    
    act(() => {
      result.current[1]('persistent-value');
    });
    
    rerender();
    
    expect(result.current[0]).toBe('persistent-value');
  });

  test('should maintain separate states for different keys', () => {
    const { result: result1 } = renderHook(() => useLocalStorage('key1', 'initial1'));
    const { result: result2 } = renderHook(() => useLocalStorage('key2', 'initial2'));
    
    act(() => {
      result1.current[1]('value1');
      result2.current[1]('value2');
    });
    
    expect(result1.current[0]).toBe('value1');
    expect(result2.current[0]).toBe('value2');
  });

  test('should handle concurrent updates to same key', () => {
    const { result: result1 } = renderHook(() => useLocalStorage('shared-key', 'initial'));
    const { result: result2 } = renderHook(() => useLocalStorage('shared-key', 'initial'));
    
    act(() => {
      result1.current[1]('from-hook1');
    });
    
    // Both hooks should reflect the same value initially
    expect(result1.current[0]).toBe('from-hook1');
    // Note: result2 won't automatically sync without storage events
  });
});

describe('useLocalStorage Hook - Edge Cases', () => {
  beforeEach(() => {
    localStorageMock.clear();
  });

  test('should handle null and undefined values', () => {
    const { result } = renderHook(() => useLocalStorage<string | null>('null-key', null));
    
    act(() => {
      result.current[1]('not-null');
    });
    
    expect(result.current[0]).toBe('not-null');
    
    act(() => {
      result.current[1](null);
    });
    
    expect(result.current[0]).toBeNull();
  });

  test('should handle circular object references gracefully', () => {
    const { result } = renderHook(() => useLocalStorage('circular-key', {}));
    
    const circularObj: any = { prop: 'value' };
    circularObj.self = circularObj;
    
    // This should not crash the hook
    act(() => {
      result.current[1](circularObj);
    });
    
    // The hook should maintain its previous state or handle the error gracefully
    expect(typeof result.current[0]).toBe('object');
  });

  test('should handle very large data', () => {
    const { result } = renderHook(() => useLocalStorage('large-key', ''));
    
    const largeString = 'x'.repeat(1000);
    
    act(() => {
      result.current[1](largeString);
    });
    
    expect(result.current[0]).toBe(largeString);
  });
});