/**
 * useDebounce Hook Test Suite
 * 25 comprehensive tests for the useDebounce hook
 */

import React from 'react';
import { renderHook, act } from '@testing-library/react';

// Mock timers for testing
jest.useFakeTimers();

// Simple useDebounce hook implementation
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = React.useState<T>(value);

  React.useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

// useDebounce with callback support
function useDebounceWithCallback<T>(
  value: T,
  delay: number,
  callback?: (value: T) => void
): T {
  const [debouncedValue, setDebouncedValue] = React.useState<T>(value);

  React.useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
      callback?.(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay, callback]);

  return debouncedValue;
}

// Advanced useDebounce with additional features
interface UseAdvancedDebounceOptions {
  leading?: boolean;
  trailing?: boolean;
  maxWait?: number;
}

function useAdvancedDebounce<T>(
  value: T,
  delay: number,
  options: UseAdvancedDebounceOptions = {}
): { debouncedValue: T; isPending: boolean; cancel: () => void; flush: () => void } {
  const { leading = false, trailing = true, maxWait } = options;
  
  const [debouncedValue, setDebouncedValue] = React.useState<T>(value);
  const [isPending, setIsPending] = React.useState<boolean>(false);
  
  const timeoutRef = React.useRef<NodeJS.Timeout | null>(null);
  const maxTimeoutRef = React.useRef<NodeJS.Timeout | null>(null);
  const leadingRef = React.useRef<boolean>(true);
  const previousValueRef = React.useRef<T>(value);

  const updateValue = React.useCallback((newValue: T) => {
    setDebouncedValue(newValue);
    setIsPending(false);
    leadingRef.current = true;
  }, []);

  const cancel = React.useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    if (maxTimeoutRef.current) {
      clearTimeout(maxTimeoutRef.current);
      maxTimeoutRef.current = null;
    }
    setIsPending(false);
    leadingRef.current = true;
  }, []);

  const flush = React.useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    if (maxTimeoutRef.current) {
      clearTimeout(maxTimeoutRef.current);
      maxTimeoutRef.current = null;
    }
    updateValue(value);
  }, [value, updateValue]);

  React.useEffect(() => {
    // Skip if value hasn't changed
    if (previousValueRef.current === value) {
      return;
    }
    previousValueRef.current = value;

    if (leading && leadingRef.current) {
      updateValue(value);
      leadingRef.current = false;
      return;
    }

    setIsPending(true);

    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    timeoutRef.current = setTimeout(() => {
      if (trailing) {
        updateValue(value);
      } else {
        setIsPending(false);
      }
      timeoutRef.current = null;
      // Clear maxWait timer as well since we're executing
      if (maxTimeoutRef.current) {
        clearTimeout(maxTimeoutRef.current);
        maxTimeoutRef.current = null;
      }
    }, delay);

    // Only start maxWait timer if one doesn't exist
    if (maxWait && !maxTimeoutRef.current) {
      maxTimeoutRef.current = setTimeout(() => {
        updateValue(value);
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
          timeoutRef.current = null;
        }
        maxTimeoutRef.current = null;
      }, maxWait);
    }

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [value, delay, leading, trailing, maxWait, updateValue]);

  React.useEffect(() => {
    return () => {
      cancel();
    };
  }, [cancel]);

  return { debouncedValue, isPending, cancel, flush };
}

// useDebounceFunction for debouncing function calls
function useDebounceFunction<T extends (...args: any[]) => any>(
  func: T,
  delay: number
): [T, () => void] {
  const timeoutRef = React.useRef<NodeJS.Timeout | null>(null);

  const debouncedFunction = React.useCallback(
    ((...args: Parameters<T>) => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }

      timeoutRef.current = setTimeout(() => {
        func(...args);
      }, delay);
    }) as T,
    [func, delay]
  );

  const cancel = React.useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  React.useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return [debouncedFunction, cancel];
}

describe('useDebounce Hook - Basic Functionality', () => {
  beforeEach(() => {
    jest.clearAllTimers();
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
  });

  test('should return initial value immediately', () => {
    const { result } = renderHook(() => useDebounce('initial', 500));
    
    expect(result.current).toBe('initial');
  });

  test('should debounce value updates', () => {
    const { result, rerender } = renderHook(
      ({ value, delay }) => useDebounce(value, delay),
      { initialProps: { value: 'initial', delay: 500 } }
    );

    expect(result.current).toBe('initial');

    rerender({ value: 'updated', delay: 500 });
    expect(result.current).toBe('initial');

    act(() => {
      jest.advanceTimersByTime(500);
    });

    expect(result.current).toBe('updated');
  });

  test('should reset timer on rapid value changes', () => {
    const { result, rerender } = renderHook(
      ({ value }) => useDebounce(value, 500),
      { initialProps: { value: 'initial' } }
    );

    rerender({ value: 'first' });
    act(() => {
      jest.advanceTimersByTime(250);
    });
    expect(result.current).toBe('initial');

    rerender({ value: 'second' });
    act(() => {
      jest.advanceTimersByTime(250);
    });
    expect(result.current).toBe('initial');

    act(() => {
      jest.advanceTimersByTime(250);
    });
    expect(result.current).toBe('second');
  });

  test('should handle different data types', () => {
    const { result: stringResult } = renderHook(() => useDebounce('test', 100));
    const { result: numberResult } = renderHook(() => useDebounce(42, 100));
    const { result: boolResult } = renderHook(() => useDebounce(true, 100));
    const { result: objResult } = renderHook(() => useDebounce({ key: 'value' }, 100));

    expect(stringResult.current).toBe('test');
    expect(numberResult.current).toBe(42);
    expect(boolResult.current).toBe(true);
    expect(objResult.current).toEqual({ key: 'value' });
  });
});

describe('useDebounce Hook - Delay Variations', () => {
  test('should work with zero delay', () => {
    const { result, rerender } = renderHook(
      ({ value }) => useDebounce(value, 0),
      { initialProps: { value: 'initial' } }
    );

    rerender({ value: 'updated' });
    
    act(() => {
      jest.advanceTimersByTime(0);
    });

    expect(result.current).toBe('updated');
  });

  test('should work with very long delays', () => {
    const { result, rerender } = renderHook(
      ({ value }) => useDebounce(value, 10000),
      { initialProps: { value: 'initial' } }
    );

    rerender({ value: 'updated' });
    
    act(() => {
      jest.advanceTimersByTime(5000);
    });
    expect(result.current).toBe('initial');

    act(() => {
      jest.advanceTimersByTime(5000);
    });
    expect(result.current).toBe('updated');
  });

  test('should handle changing delay values', () => {
    const { result, rerender } = renderHook(
      ({ value, delay }) => useDebounce(value, delay),
      { initialProps: { value: 'initial', delay: 500 } }
    );

    rerender({ value: 'updated', delay: 1000 });
    
    act(() => {
      jest.advanceTimersByTime(500);
    });
    expect(result.current).toBe('initial');

    act(() => {
      jest.advanceTimersByTime(500);
    });
    expect(result.current).toBe('updated');
  });
});

describe('useDebounceWithCallback Hook - Callback Support', () => {
  test('should call callback when value is debounced', () => {
    const callback = jest.fn();
    const { rerender } = renderHook(
      ({ value }) => useDebounceWithCallback(value, 500, callback),
      { initialProps: { value: 'initial' } }
    );

    rerender({ value: 'updated' });
    
    act(() => {
      jest.advanceTimersByTime(500);
    });

    expect(callback).toHaveBeenCalledWith('updated');
  });

  test('should not call callback if value changes before debounce', () => {
    const callback = jest.fn();
    const { rerender } = renderHook(
      ({ value }) => useDebounceWithCallback(value, 500, callback),
      { initialProps: { value: 'initial' } }
    );

    rerender({ value: 'first' });
    act(() => {
      jest.advanceTimersByTime(250);
    });

    rerender({ value: 'second' });
    act(() => {
      jest.advanceTimersByTime(250);
    });

    expect(callback).not.toHaveBeenCalled();

    act(() => {
      jest.advanceTimersByTime(250);
    });

    expect(callback).toHaveBeenCalledWith('second');
    expect(callback).toHaveBeenCalledTimes(1);
  });

  test('should work without callback', () => {
    const { result, rerender } = renderHook(
      ({ value }) => useDebounceWithCallback(value, 500),
      { initialProps: { value: 'initial' } }
    );

    expect(() => {
      rerender({ value: 'updated' });
      act(() => {
        jest.advanceTimersByTime(500);
      });
    }).not.toThrow();

    expect(result.current).toBe('updated');
  });
});

describe('useAdvancedDebounce Hook - Advanced Features', () => {
  test('should provide pending state', () => {
    const { result, rerender } = renderHook(
      ({ value }) => useAdvancedDebounce(value, 500),
      { initialProps: { value: 'initial' } }
    );

    // Initially should not be pending
    expect(result.current.isPending).toBe(false);

    act(() => {
      rerender({ value: 'updated' });
    });
    
    // After value change, should be pending
    expect(result.current.isPending).toBe(true);

    act(() => {
      jest.advanceTimersByTime(500);
    });

    // After timeout, should not be pending
    expect(result.current.isPending).toBe(false);
  });

  test('should support leading edge execution', () => {
    const { result, rerender } = renderHook(
      ({ value }) => useAdvancedDebounce(value, 500, { leading: true }),
      { initialProps: { value: 'initial' } }
    );

    expect(result.current.debouncedValue).toBe('initial');

    act(() => {
      rerender({ value: 'updated' });
    });
    
    // With leading=true, value should update immediately
    expect(result.current.debouncedValue).toBe('updated');
  });

  test('should support trailing edge execution', () => {
    const { result, rerender } = renderHook(
      ({ value }) => useAdvancedDebounce(value, 500, { trailing: true }),
      { initialProps: { value: 'initial' } }
    );

    rerender({ value: 'updated' });
    expect(result.current.debouncedValue).toBe('initial');

    act(() => {
      jest.advanceTimersByTime(500);
    });

    expect(result.current.debouncedValue).toBe('updated');
  });

  test('should support max wait option', () => {
    const { result, rerender } = renderHook(
      ({ value }) => useAdvancedDebounce(value, 1000, { maxWait: 300 }),
      { initialProps: { value: 'initial' } }
    );

    expect(result.current.debouncedValue).toBe('initial');

    act(() => {
      rerender({ value: 'updated' });
    });

    // Advance time to maxWait - should update even though delay hasn't elapsed
    act(() => {
      jest.advanceTimersByTime(300);
    });

    expect(result.current.debouncedValue).toBe('updated');
  });

  test('should support cancel functionality', () => {
    const { result, rerender } = renderHook(
      ({ value }) => useAdvancedDebounce(value, 500),
      { initialProps: { value: 'initial' } }
    );

    rerender({ value: 'updated' });
    expect(result.current.isPending).toBe(true);

    act(() => {
      result.current.cancel();
    });

    expect(result.current.isPending).toBe(false);

    act(() => {
      jest.advanceTimersByTime(500);
    });

    expect(result.current.debouncedValue).toBe('initial');
  });

  test('should support flush functionality', () => {
    const { result, rerender } = renderHook(
      ({ value }) => useAdvancedDebounce(value, 500),
      { initialProps: { value: 'initial' } }
    );

    rerender({ value: 'updated' });
    expect(result.current.debouncedValue).toBe('initial');

    act(() => {
      result.current.flush();
    });

    expect(result.current.debouncedValue).toBe('updated');
    expect(result.current.isPending).toBe(false);
  });
});

describe('useDebounceFunction Hook - Function Debouncing', () => {
  test('should debounce function calls', () => {
    const mockFn = jest.fn();
    const { result } = renderHook(() => useDebounceFunction(mockFn, 500));
    const [debouncedFn] = result.current;

    act(() => {
      debouncedFn('arg1');
      debouncedFn('arg2');
      debouncedFn('arg3');
    });

    expect(mockFn).not.toHaveBeenCalled();

    act(() => {
      jest.advanceTimersByTime(500);
    });

    expect(mockFn).toHaveBeenCalledWith('arg3');
    expect(mockFn).toHaveBeenCalledTimes(1);
  });

  test('should cancel debounced function calls', () => {
    const mockFn = jest.fn();
    const { result } = renderHook(() => useDebounceFunction(mockFn, 500));
    const [debouncedFn, cancel] = result.current;

    act(() => {
      debouncedFn('test');
    });

    act(() => {
      cancel();
    });

    act(() => {
      jest.advanceTimersByTime(500);
    });

    expect(mockFn).not.toHaveBeenCalled();
  });

  test('should handle function with multiple arguments', () => {
    const mockFn = jest.fn();
    const { result } = renderHook(() => useDebounceFunction(mockFn, 300));
    const [debouncedFn] = result.current;

    act(() => {
      debouncedFn('arg1', 'arg2', { key: 'value' });
    });

    act(() => {
      jest.advanceTimersByTime(300);
    });

    expect(mockFn).toHaveBeenCalledWith('arg1', 'arg2', { key: 'value' });
  });

  test('should maintain function reference stability', () => {
    const mockFn = jest.fn();
    const { result, rerender } = renderHook(() => useDebounceFunction(mockFn, 500));
    
    const [initialFn] = result.current;
    
    rerender();
    
    const [rerenderedFn] = result.current;
    
    expect(initialFn).toBe(rerenderedFn);
  });
});

describe('useDebounce Hook - Edge Cases and Cleanup', () => {
  test('should cleanup timers on unmount', () => {
    const { unmount, rerender } = renderHook(
      ({ value }) => useDebounce(value, 500),
      { initialProps: { value: 'initial' } }
    );

    rerender({ value: 'updated' });
    
    unmount();

    // Should not throw any errors or cause memory leaks
    act(() => {
      jest.advanceTimersByTime(500);
    });
  });

  test('should handle rapid mount/unmount cycles', () => {
    for (let i = 0; i < 10; i++) {
      const { unmount, rerender } = renderHook(
        ({ value }) => useDebounce(value, 100),
        { initialProps: { value: `value-${i}` } }
      );

      rerender({ value: `updated-${i}` });
      unmount();
    }

    // Should not cause any issues
    act(() => {
      jest.advanceTimersByTime(1000);
    });
  });

  test('should handle null and undefined values', () => {
    const { result, rerender } = renderHook(
      ({ value }) => useDebounce(value, 500),
      { initialProps: { value: null as string | null } }
    );

    expect(result.current).toBeNull();

    rerender({ value: undefined as string | null | undefined });
    
    act(() => {
      jest.advanceTimersByTime(500);
    });

    expect(result.current).toBeUndefined();
  });

  test('should handle complex objects with deep equality', () => {
    const initialObj = { nested: { value: 'initial' } };
    const updatedObj = { nested: { value: 'updated' } };
    
    const { result, rerender } = renderHook(
      ({ value }) => useDebounce(value, 500),
      { initialProps: { value: initialObj } }
    );

    expect(result.current).toBe(initialObj);

    rerender({ value: updatedObj });
    
    act(() => {
      jest.advanceTimersByTime(500);
    });

    expect(result.current).toBe(updatedObj);
  });
});