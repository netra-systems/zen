/**
 * usePrevious Hook Test Suite
 * 25 comprehensive tests for the usePrevious hook
 */

import React from 'react';
import { renderHook } from '@testing-library/react';

// Simple usePrevious hook implementation
function usePrevious<T>(value: T): T | undefined {
  const ref = React.useRef<T>();
  
  React.useEffect(() => {
    ref.current = value;
  });
  
  return ref.current;
}

// usePrevious with initial value
function usePreviousWithInitial<T>(value: T, initialValue: T): T {
  const ref = React.useRef<T>(initialValue);
  
  React.useEffect(() => {
    ref.current = value;
  });
  
  return ref.current;
}

// usePrevious with comparison function
function usePreviousWithComparison<T>(
  value: T,
  compare?: (prev: T | undefined, current: T) => boolean
): T | undefined {
  const ref = React.useRef<T>();
  const prevValue = ref.current;
  
  React.useEffect(() => {
    // If no comparison function or comparison returns true, update
    if (!compare || compare(ref.current, value)) {
      ref.current = value;
    }
  });
  
  return prevValue;
}

// usePreviousArray to track multiple previous values
function usePreviousArray<T>(value: T, count: number): (T | undefined)[] {
  const [array, setArray] = React.useState<(T | undefined)[]>(() => [value]);
  const valueRef = React.useRef<T>(value);
  
  React.useEffect(() => {
    if (valueRef.current !== value) {
      setArray(prev => [value, ...prev.slice(0, count - 1)]);
      valueRef.current = value;
    }
  }, [value, count]);
  
  return array;
}

// usePreviousState that returns both current and previous
function usePreviousState<T>(value: T): { current: T; previous: T | undefined; hasChanged: boolean } {
  const ref = React.useRef<T>();
  const hasChanged = ref.current !== value;
  
  React.useEffect(() => {
    ref.current = value;
  });
  
  return {
    current: value,
    previous: ref.current,
    hasChanged
  };
}

// usePreviousProps for tracking prop changes
function usePreviousProps<T extends Record<string, any>>(props: T): Partial<T> | undefined {
  const ref = React.useRef<T>();
  
  React.useEffect(() => {
    ref.current = props;
  });
  
  return ref.current;
}

// usePreviousCallback for tracking function references
function usePreviousCallback<T extends (...args: any[]) => any>(callback: T): T | undefined {
  const ref = React.useRef<T>();
  
  React.useEffect(() => {
    ref.current = callback;
  });
  
  return ref.current;
}

describe('usePrevious Hook - Basic Functionality', () => {
  test('should return undefined on first render', () => {
    const { result } = renderHook(() => usePrevious('initial'));
    
    expect(result.current).toBeUndefined();
  });

  test('should return previous value after rerender', () => {
    const { result, rerender } = renderHook(
      ({ value }) => usePrevious(value),
      { initialProps: { value: 'initial' } }
    );

    expect(result.current).toBeUndefined();

    rerender({ value: 'updated' });
    expect(result.current).toBe('initial');
  });

  test('should track multiple value changes', () => {
    const { result, rerender } = renderHook(
      ({ value }) => usePrevious(value),
      { initialProps: { value: 'first' } }
    );

    expect(result.current).toBeUndefined();

    rerender({ value: 'second' });
    expect(result.current).toBe('first');

    rerender({ value: 'third' });
    expect(result.current).toBe('second');

    rerender({ value: 'fourth' });
    expect(result.current).toBe('third');
  });

  test('should handle same value rerenders', () => {
    const { result, rerender } = renderHook(
      ({ value }) => usePrevious(value),
      { initialProps: { value: 'constant' } }
    );

    rerender({ value: 'constant' });
    expect(result.current).toBe('constant');

    rerender({ value: 'constant' });
    expect(result.current).toBe('constant');
  });
});

describe('usePrevious Hook - Data Types', () => {
  test('should work with string values', () => {
    const { result, rerender } = renderHook(
      ({ value }) => usePrevious(value),
      { initialProps: { value: 'hello' } }
    );

    rerender({ value: 'world' });
    expect(result.current).toBe('hello');
  });

  test('should work with number values', () => {
    const { result, rerender } = renderHook(
      ({ value }) => usePrevious(value),
      { initialProps: { value: 42 } }
    );

    rerender({ value: 84 });
    expect(result.current).toBe(42);
  });

  test('should work with boolean values', () => {
    const { result, rerender } = renderHook(
      ({ value }) => usePrevious(value),
      { initialProps: { value: true } }
    );

    rerender({ value: false });
    expect(result.current).toBe(true);
  });

  test('should work with object values', () => {
    const obj1 = { name: 'first', count: 1 };
    const obj2 = { name: 'second', count: 2 };
    
    const { result, rerender } = renderHook(
      ({ value }) => usePrevious(value),
      { initialProps: { value: obj1 } }
    );

    rerender({ value: obj2 });
    expect(result.current).toBe(obj1);
  });

  test('should work with array values', () => {
    const arr1 = [1, 2, 3];
    const arr2 = [4, 5, 6];
    
    const { result, rerender } = renderHook(
      ({ value }) => usePrevious(value),
      { initialProps: { value: arr1 } }
    );

    rerender({ value: arr2 });
    expect(result.current).toBe(arr1);
  });

  test('should work with function values', () => {
    const fn1 = () => 'first';
    const fn2 = () => 'second';
    
    const { result, rerender } = renderHook(
      ({ value }) => usePrevious(value),
      { initialProps: { value: fn1 } }
    );

    rerender({ value: fn2 });
    expect(result.current).toBe(fn1);
  });
});

describe('usePreviousWithInitial Hook - Initial Value Support', () => {
  test('should return initial value on first render', () => {
    const { result } = renderHook(() => usePreviousWithInitial('current', 'initial'));
    
    expect(result.current).toBe('initial');
  });

  test('should track values with initial value provided', () => {
    const { result, rerender } = renderHook(
      ({ value }) => usePreviousWithInitial(value, 'default'),
      { initialProps: { value: 'first' } }
    );

    expect(result.current).toBe('default');

    rerender({ value: 'second' });
    expect(result.current).toBe('first');

    rerender({ value: 'third' });
    expect(result.current).toBe('second');
  });

  test('should handle different types for initial value', () => {
    const { result, rerender } = renderHook(
      ({ value }) => usePreviousWithInitial(value, 0),
      { initialProps: { value: 10 } }
    );

    expect(result.current).toBe(0);

    rerender({ value: 20 });
    expect(result.current).toBe(10);
  });
});

describe('usePreviousWithComparison Hook - Custom Comparison', () => {
  test('should use custom comparison function', () => {
    const compare = (prev: number | undefined, current: number) => {
      return prev === undefined || Math.abs(prev - current) >= 5;
    };

    const { result, rerender } = renderHook(
      ({ value }) => usePreviousWithComparison(value, compare),
      { initialProps: { value: 10 } }
    );

    expect(result.current).toBeUndefined();

    // Small change - should not update previous value (comparison returns false)
    rerender({ value: 12 });
    expect(result.current).toBe(10); // Should return the value that was stored on first render

    // Large change - should update (comparison returns true)
    rerender({ value: 20 });
    expect(result.current).toBe(10); // Should return previous value
  });

  test('should work without comparison function', () => {
    const { result, rerender } = renderHook(
      ({ value }) => usePreviousWithComparison(value),
      { initialProps: { value: 'test' } }
    );

    rerender({ value: 'updated' });
    expect(result.current).toBe('test');
  });

  test('should handle object comparison', () => {
    const compare = (prev: any, current: any) => {
      return !prev || prev.id !== current.id;
    };

    const obj1 = { id: 1, name: 'first' };
    const obj2 = { id: 1, name: 'updated' };
    const obj3 = { id: 2, name: 'second' };

    const { result, rerender } = renderHook(
      ({ value }) => usePreviousWithComparison(value, compare),
      { initialProps: { value: obj1 } }
    );

    expect(result.current).toBeUndefined();

    // Same ID - should not update (comparison returns false)
    rerender({ value: obj2 });
    expect(result.current).toBe(obj1); // Should return the stored value

    // Different ID - should update (comparison returns true) 
    rerender({ value: obj3 });
    expect(result.current).toBe(obj1); // Should return previous value before update
  });
});

describe('usePreviousArray Hook - Multiple Previous Values', () => {
  test('should track specified number of previous values', () => {
    const { result, rerender } = renderHook(
      ({ value }) => usePreviousArray(value, 3),
      { initialProps: { value: 'first' } }
    );

    expect(result.current).toEqual(['first']);

    rerender({ value: 'second' });
    expect(result.current).toEqual(['second', 'first']);

    rerender({ value: 'third' });
    expect(result.current).toEqual(['third', 'second', 'first']);

    rerender({ value: 'fourth' });
    expect(result.current).toEqual(['fourth', 'third', 'second']);
  });

  test('should handle count of 1', () => {
    const { result, rerender } = renderHook(
      ({ value }) => usePreviousArray(value, 1),
      { initialProps: { value: 'test' } }
    );

    expect(result.current).toEqual(['test']);

    rerender({ value: 'updated' });
    expect(result.current).toEqual(['updated']);
  });

  test('should handle large count values', () => {
    const { result, rerender } = renderHook(
      ({ value }) => usePreviousArray(value, 10),
      { initialProps: { value: 1 } }
    );

    for (let i = 2; i <= 15; i++) {
      rerender({ value: i });
    }

    expect(result.current).toHaveLength(10);
    expect(result.current[0]).toBe(15);
    expect(result.current[9]).toBe(6);
  });
});

describe('usePreviousState Hook - Enhanced State Tracking', () => {
  test('should return current, previous, and change status', () => {
    const { result, rerender } = renderHook(
      ({ value }) => usePreviousState(value),
      { initialProps: { value: 'initial' } }
    );

    expect(result.current.current).toBe('initial');
    expect(result.current.previous).toBeUndefined();
    expect(result.current.hasChanged).toBe(true);

    rerender({ value: 'updated' });
    expect(result.current.current).toBe('updated');
    expect(result.current.previous).toBe('initial');
    expect(result.current.hasChanged).toBe(true);

    rerender({ value: 'updated' });
    expect(result.current.current).toBe('updated');
    expect(result.current.previous).toBe('updated');
    expect(result.current.hasChanged).toBe(false);
  });

  test('should detect changes correctly', () => {
    const { result, rerender } = renderHook(
      ({ value }) => usePreviousState(value),
      { initialProps: { value: 42 } }
    );

    expect(result.current.hasChanged).toBe(true);

    rerender({ value: 42 });
    expect(result.current.hasChanged).toBe(false);

    rerender({ value: 84 });
    expect(result.current.hasChanged).toBe(true);
  });
});

describe('usePreviousProps Hook - Props Tracking', () => {
  test('should track previous props object', () => {
    const props1 = { name: 'John', age: 30 };
    const props2 = { name: 'Jane', age: 25 };

    const { result, rerender } = renderHook(
      ({ props }) => usePreviousProps(props),
      { initialProps: { props: props1 } }
    );

    expect(result.current).toBeUndefined();

    rerender({ props: props2 });
    expect(result.current).toBe(props1);
  });

  test('should handle partial prop changes', () => {
    interface Props {
      id: number;
      name: string;
      isActive: boolean;
    }

    const props1: Props = { id: 1, name: 'Test', isActive: true };
    const props2: Props = { id: 1, name: 'Updated', isActive: true };

    const { result, rerender } = renderHook(
      ({ props }) => usePreviousProps(props),
      { initialProps: { props: props1 } }
    );

    rerender({ props: props2 });
    expect(result.current).toEqual(props1);
  });
});

describe('usePreviousCallback Hook - Function Tracking', () => {
  test('should track previous callback function', () => {
    const callback1 = jest.fn(() => 'first');
    const callback2 = jest.fn(() => 'second');

    const { result, rerender } = renderHook(
      ({ callback }) => usePreviousCallback(callback),
      { initialProps: { callback: callback1 } }
    );

    expect(result.current).toBeUndefined();

    rerender({ callback: callback2 });
    expect(result.current).toBe(callback1);
  });

  test('should detect function reference changes', () => {
    const stableCallback = jest.fn();

    const { result, rerender } = renderHook(
      ({ callback }) => usePreviousCallback(callback),
      { initialProps: { callback: stableCallback } }
    );

    rerender({ callback: stableCallback });
    expect(result.current).toBe(stableCallback);

    const newCallback = jest.fn();
    rerender({ callback: newCallback });
    expect(result.current).toBe(stableCallback);
  });
});

describe('usePrevious Hook - Edge Cases', () => {
  test('should handle null values', () => {
    const { result, rerender } = renderHook(
      ({ value }) => usePrevious(value),
      { initialProps: { value: null as string | null } }
    );

    rerender({ value: 'not null' });
    expect(result.current).toBeNull();

    rerender({ value: null });
    expect(result.current).toBe('not null');
  });

  test('should handle undefined values', () => {
    const { result, rerender } = renderHook(
      ({ value }) => usePrevious(value),
      { initialProps: { value: undefined as string | undefined } }
    );

    rerender({ value: 'defined' });
    expect(result.current).toBeUndefined();

    rerender({ value: undefined });
    expect(result.current).toBe('defined');
  });

  test('should handle rapid state changes', () => {
    const { result, rerender } = renderHook(
      ({ value }) => usePrevious(value),
      { initialProps: { value: 0 } }
    );

    for (let i = 1; i <= 100; i++) {
      rerender({ value: i });
      expect(result.current).toBe(i - 1);
    }
  });

  test('should maintain reference equality for objects', () => {
    const obj = { immutable: 'object' };
    
    const { result, rerender } = renderHook(
      ({ value }) => usePrevious(value),
      { initialProps: { value: obj } }
    );

    const newObj = { different: 'object' };
    rerender({ value: newObj });
    
    expect(result.current).toBe(obj);
    expect(result.current).not.toBe(newObj);
  });

  test('should work with deeply nested objects', () => {
    const deepObj1 = {
      level1: {
        level2: {
          level3: {
            value: 'deep'
          }
        }
      }
    };

    const deepObj2 = {
      level1: {
        level2: {
          level3: {
            value: 'deeper'
          }
        }
      }
    };

    const { result, rerender } = renderHook(
      ({ value }) => usePrevious(value),
      { initialProps: { value: deepObj1 } }
    );

    rerender({ value: deepObj2 });
    expect(result.current).toBe(deepObj1);
    expect(result.current?.level1.level2.level3.value).toBe('deep');
  });
});