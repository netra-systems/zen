/**
 * Custom Hooks Test
 * Tests custom React hooks functionality and behavior
 */

import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { renderHook } from '@testing-library/react';
import '@testing-library/jest-dom';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

// Custom hook for local storage
const useLocalStorage = <T,>(key: string, initialValue: T) => {
  const [storedValue, setStoredValue] = React.useState<T>(() => {
    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch (error) {
      return initialValue;
    }
  });

  const setValue = React.useCallback((value: T | ((val: T) => T)) => {
    try {
      const valueToStore = value instanceof Function ? value(storedValue) : value;
      setStoredValue(valueToStore);
      window.localStorage.setItem(key, JSON.stringify(valueToStore));
    } catch (error) {
      console.error('Error saving to localStorage:', error);
    }
  }, [key, storedValue]);

  return [storedValue, setValue] as const;
};

// Custom hook for debounced value
const useDebounce = <T,>(value: T, delay: number) => {
  const [debouncedValue, setDebouncedValue] = React.useState(value);

  React.useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
};

// Custom hook for online status
const useOnlineStatus = () => {
  const [isOnline, setIsOnline] = React.useState(navigator.onLine);

  React.useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  return isOnline;
};

// Custom hook for previous value
const usePrevious = <T,>(value: T) => {
  const ref = React.useRef<T>();
  
  React.useEffect(() => {
    ref.current = value;
  }, [value]);
  
  return ref.current;
};

// Custom hook for counter with limits
const useCounter = (initialValue: number = 0, min?: number, max?: number) => {
  const [count, setCount] = React.useState(initialValue);

  const increment = React.useCallback(() => {
    setCount(prev => {
      const next = prev + 1;
      return max !== undefined && next > max ? prev : next;
    });
  }, [max]);

  const decrement = React.useCallback(() => {
    setCount(prev => {
      const next = prev - 1;
      return min !== undefined && next < min ? prev : next;
    });
  }, [min]);

  const reset = React.useCallback(() => {
    setCount(initialValue);
  }, [initialValue]);

  const set = React.useCallback((value: number) => {
    setCount(value);
  }, []);

  return { count, increment, decrement, reset, set };
};

describe('Custom Hooks', () => {
  setupAntiHang();
    jest.setTimeout(10000);
  beforeEach(() => {
    localStorage.clear();
  });

  it('should manage localStorage state with useLocalStorage hook', () => {
    const { result, rerender } = renderHook(() => 
      useLocalStorage('test-key', 'initial-value')
    );

    // Initial value should be set
    expect(result.current[0]).toBe('initial-value');

    // Update the value
    act(() => {
      result.current[1]('updated-value');
    });

    expect(result.current[0]).toBe('updated-value');
    expect(localStorage.getItem('test-key')).toBe('"updated-value"');

    // Re-render hook to simulate component remount
    rerender();
    expect(result.current[0]).toBe('updated-value');
  });

  it('should debounce values with useDebounce hook', async () => {
    const { result, rerender } = renderHook(
      ({ value, delay }) => useDebounce(value, delay),
      { initialProps: { value: 'initial', delay: 100 } }
    );

    // Initial value should be set immediately
    expect(result.current).toBe('initial');

    // Update value
    rerender({ value: 'updated', delay: 100 });

    // Value should still be 'initial' immediately after update
    expect(result.current).toBe('initial');

    // Wait for debounce delay
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 150));
    });

    // Now value should be updated
    expect(result.current).toBe('updated');
  });

  it('should track online status with useOnlineStatus hook', () => {
    const { result } = renderHook(() => useOnlineStatus());

    // Should start with online status
    expect(result.current).toBe(true);

    // Simulate going offline
    act(() => {
      Object.defineProperty(navigator, 'onLine', {
        writable: true,
        value: false,
      });
      window.dispatchEvent(new Event('offline'));
    });

    expect(result.current).toBe(false);

    // Simulate coming back online
    act(() => {
      Object.defineProperty(navigator, 'onLine', {
        writable: true,
        value: true,
      });
      window.dispatchEvent(new Event('online'));
    });

    expect(result.current).toBe(true);
  });

  it('should track previous values with usePrevious hook', () => {
    const { result, rerender } = renderHook(
      ({ value }) => usePrevious(value),
      { initialProps: { value: 'first' } }
    );

    // Initial render should have undefined previous value
    expect(result.current).toBeUndefined();

    // Update value
    rerender({ value: 'second' });
    expect(result.current).toBe('first');

    // Update again
    rerender({ value: 'third' });
    expect(result.current).toBe('second');
  });

  it('should manage counter with limits using useCounter hook', () => {
    const { result } = renderHook(() => useCounter(5, 0, 10));

    // Initial count
    expect(result.current.count).toBe(5);

    // Increment
    act(() => {
      result.current.increment();
    });
    expect(result.current.count).toBe(6);

    // Decrement
    act(() => {
      result.current.decrement();
    });
    expect(result.current.count).toBe(5);

    // Test max limit
    act(() => {
      result.current.set(10);
      result.current.increment();
    });
    expect(result.current.count).toBe(10); // Should not exceed max

    // Test min limit
    act(() => {
      result.current.set(0);
      result.current.decrement();
    });
    expect(result.current.count).toBe(0); // Should not go below min

    // Reset
    act(() => {
      result.current.reset();
    });
    expect(result.current.count).toBe(5);
  });

  it('should work with custom hooks in components', () => {
    const TestComponent: React.FC = () => {
      const [name, setName] = useLocalStorage('user-name', '');
      const [searchTerm, setSearchTerm] = React.useState('');
      const debouncedSearchTerm = useDebounce(searchTerm, 300);
      const isOnline = useOnlineStatus();
      const previousSearchTerm = usePrevious(debouncedSearchTerm);
      const counter = useCounter(0, 0, 5);

      return (
        <div>
          <div data-testid="name-display">Name: {name}</div>
          <input
            data-testid="name-input"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Enter name"
          />

          <div data-testid="search-term">Current: {searchTerm}</div>
          <div data-testid="debounced-search">Debounced: {debouncedSearchTerm}</div>
          <div data-testid="previous-search">Previous: {previousSearchTerm || 'none'}</div>
          <input
            data-testid="search-input"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search..."
          />

          <div data-testid="online-status">Online: {isOnline ? 'Yes' : 'No'}</div>

          <div data-testid="counter-value">Count: {counter.count}</div>
          <button data-testid="increment" onClick={counter.increment}>
            +
          </button>
          <button data-testid="decrement" onClick={counter.decrement}>
            -
          </button>
          <button data-testid="reset-counter" onClick={counter.reset}>
            Reset
          </button>
        </div>
      );
    };

    render(<TestComponent />);

    // Test localStorage hook
    expect(screen.getByTestId('name-display')).toHaveTextContent('Name: ');
    
    fireEvent.change(screen.getByTestId('name-input'), { target: { value: 'John' } });
    expect(screen.getByTestId('name-display')).toHaveTextContent('Name: John');

    // Test debounce hook
    expect(screen.getByTestId('debounced-search')).toHaveTextContent('Debounced: ');
    
    fireEvent.change(screen.getByTestId('search-input'), { target: { value: 'test' } });
    expect(screen.getByTestId('search-term')).toHaveTextContent('Current: test');
    expect(screen.getByTestId('debounced-search')).toHaveTextContent('Debounced: '); // Still empty due to debounce

    // Test online status hook
    expect(screen.getByTestId('online-status')).toHaveTextContent('Online: Yes');

    // Test counter hook
    expect(screen.getByTestId('counter-value')).toHaveTextContent('Count: 0');
    
    fireEvent.click(screen.getByTestId('increment'));
    expect(screen.getByTestId('counter-value')).toHaveTextContent('Count: 1');
    
    fireEvent.click(screen.getByTestId('decrement'));
    expect(screen.getByTestId('counter-value')).toHaveTextContent('Count: 0');
    
    fireEvent.click(screen.getByTestId('reset-counter'));
    expect(screen.getByTestId('counter-value')).toHaveTextContent('Count: 0');
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});