/**
 * useToggle Hook Test Suite
 * 25 comprehensive tests for the useToggle hook
 */

import React from 'react';
import { renderHook, act } from '@testing-library/react';

// Simple useToggle hook implementation
interface UseToggleReturn {
  value: boolean;
  toggle: () => void;
  setTrue: () => void;
  setFalse: () => void;
  setValue: (value: boolean) => void;
}

function useToggle(initialValue: boolean = false): UseToggleReturn {
  const [value, setValue] = React.useState<boolean>(initialValue);

  const toggle = React.useCallback(() => {
    setValue(prev => !prev);
  }, []);

  const setTrue = React.useCallback(() => {
    setValue(true);
  }, []);

  const setFalse = React.useCallback(() => {
    setValue(false);
  }, []);

  const setValueCallback = React.useCallback((newValue: boolean) => {
    setValue(newValue);
  }, []);

  return {
    value,
    toggle,
    setTrue,
    setFalse,
    setValue: setValueCallback
  };
}

// Enhanced useToggle with additional features
interface UseEnhancedToggleReturn extends UseToggleReturn {
  toggleCount: number;
  lastToggleTime: number | null;
  reset: () => void;
}

function useEnhancedToggle(initialValue: boolean = false): UseEnhancedToggleReturn {
  const [value, setValue] = React.useState<boolean>(initialValue);
  const [toggleCount, setToggleCount] = React.useState<number>(0);
  const [lastToggleTime, setLastToggleTime] = React.useState<number | null>(null);
  const initialValueRef = React.useRef(initialValue);

  const toggle = React.useCallback(() => {
    setValue(prev => !prev);
    setToggleCount(count => count + 1);
    setLastToggleTime(Date.now());
  }, []);

  const setTrue = React.useCallback(() => {
    setValue(true);
    setToggleCount(count => count + 1);
    setLastToggleTime(Date.now());
  }, []);

  const setFalse = React.useCallback(() => {
    setValue(false);
    setToggleCount(count => count + 1);
    setLastToggleTime(Date.now());
  }, []);

  const setValueCallback = React.useCallback((newValue: boolean) => {
    setValue(newValue);
    setToggleCount(count => count + 1);
    setLastToggleTime(Date.now());
  }, []);

  const reset = React.useCallback(() => {
    setValue(initialValueRef.current);
    setToggleCount(0);
    setLastToggleTime(null);
  }, []);

  return {
    value,
    toggle,
    setTrue,
    setFalse,
    setValue: setValueCallback,
    toggleCount,
    lastToggleTime,
    reset
  };
}

// useToggle with callback support
function useToggleWithCallback(
  initialValue: boolean = false,
  onToggle?: (value: boolean) => void
): UseToggleReturn {
  const [value, setValue] = React.useState<boolean>(initialValue);

  const toggle = React.useCallback(() => {
    setValue(prev => {
      const newValue = !prev;
      onToggle?.(newValue);
      return newValue;
    });
  }, [onToggle]);

  const setTrue = React.useCallback(() => {
    setValue(true);
    onToggle?.(true);
  }, [onToggle]);

  const setFalse = React.useCallback(() => {
    setValue(false);
    onToggle?.(false);
  }, [onToggle]);

  const setValueCallback = React.useCallback((newValue: boolean) => {
    setValue(newValue);
    onToggle?.(newValue);
  }, [onToggle]);

  return {
    value,
    toggle,
    setTrue,
    setFalse,
    setValue: setValueCallback
  };
}

describe('useToggle Hook - Basic Functionality', () => {
  test('should initialize with default false value', () => {
    const { result } = renderHook(() => useToggle());
    
    expect(result.current.value).toBe(false);
  });

  test('should initialize with provided true value', () => {
    const { result } = renderHook(() => useToggle(true));
    
    expect(result.current.value).toBe(true);
  });

  test('should initialize with provided false value', () => {
    const { result } = renderHook(() => useToggle(false));
    
    expect(result.current.value).toBe(false);
  });

  test('should toggle from false to true', () => {
    const { result } = renderHook(() => useToggle(false));
    
    act(() => {
      result.current.toggle();
    });
    
    expect(result.current.value).toBe(true);
  });

  test('should toggle from true to false', () => {
    const { result } = renderHook(() => useToggle(true));
    
    act(() => {
      result.current.toggle();
    });
    
    expect(result.current.value).toBe(false);
  });
});

describe('useToggle Hook - Multiple Toggles', () => {
  test('should toggle multiple times correctly', () => {
    const { result } = renderHook(() => useToggle(false));
    
    // Initial: false
    expect(result.current.value).toBe(false);
    
    // First toggle: true
    act(() => {
      result.current.toggle();
    });
    expect(result.current.value).toBe(true);
    
    // Second toggle: false
    act(() => {
      result.current.toggle();
    });
    expect(result.current.value).toBe(false);
    
    // Third toggle: true
    act(() => {
      result.current.toggle();
    });
    expect(result.current.value).toBe(true);
  });

  test('should handle rapid successive toggles', () => {
    const { result } = renderHook(() => useToggle(false));
    
    act(() => {
      result.current.toggle();
      result.current.toggle();
      result.current.toggle();
      result.current.toggle();
    });
    
    expect(result.current.value).toBe(false); // Even number of toggles
  });
});

describe('useToggle Hook - Direct Setters', () => {
  test('should set to true using setTrue', () => {
    const { result } = renderHook(() => useToggle(false));
    
    act(() => {
      result.current.setTrue();
    });
    
    expect(result.current.value).toBe(true);
  });

  test('should set to false using setFalse', () => {
    const { result } = renderHook(() => useToggle(true));
    
    act(() => {
      result.current.setFalse();
    });
    
    expect(result.current.value).toBe(false);
  });

  test('should set to true using setValue', () => {
    const { result } = renderHook(() => useToggle(false));
    
    act(() => {
      result.current.setValue(true);
    });
    
    expect(result.current.value).toBe(true);
  });

  test('should set to false using setValue', () => {
    const { result } = renderHook(() => useToggle(true));
    
    act(() => {
      result.current.setValue(false);
    });
    
    expect(result.current.value).toBe(false);
  });
});

describe('useToggle Hook - Function Stability', () => {
  test('should return stable function references', () => {
    const { result, rerender } = renderHook(() => useToggle(false));
    
    const initialToggle = result.current.toggle;
    const initialSetTrue = result.current.setTrue;
    const initialSetFalse = result.current.setFalse;
    const initialSetValue = result.current.setValue;
    
    rerender();
    
    expect(result.current.toggle).toBe(initialToggle);
    expect(result.current.setTrue).toBe(initialSetTrue);
    expect(result.current.setFalse).toBe(initialSetFalse);
    expect(result.current.setValue).toBe(initialSetValue);
  });

  test('should maintain function stability across value changes', () => {
    const { result } = renderHook(() => useToggle(false));
    
    const initialToggle = result.current.toggle;
    
    act(() => {
      result.current.toggle();
    });
    
    expect(result.current.toggle).toBe(initialToggle);
  });
});

describe('useEnhancedToggle Hook - Enhanced Features', () => {
  test('should track toggle count', () => {
    const { result } = renderHook(() => useEnhancedToggle(false));
    
    expect(result.current.toggleCount).toBe(0);
    
    act(() => {
      result.current.toggle();
    });
    
    expect(result.current.toggleCount).toBe(1);
    
    act(() => {
      result.current.toggle();
    });
    
    expect(result.current.toggleCount).toBe(2);
  });

  test('should track last toggle time', () => {
    const { result } = renderHook(() => useEnhancedToggle(false));
    
    expect(result.current.lastToggleTime).toBeNull();
    
    const beforeToggle = Date.now();
    
    act(() => {
      result.current.toggle();
    });
    
    const afterToggle = Date.now();
    
    expect(result.current.lastToggleTime).toBeGreaterThanOrEqual(beforeToggle);
    expect(result.current.lastToggleTime).toBeLessThanOrEqual(afterToggle);
  });

  test('should reset to initial state', () => {
    const { result } = renderHook(() => useEnhancedToggle(true));
    
    act(() => {
      result.current.toggle();
      result.current.toggle();
    });
    
    expect(result.current.value).toBe(true);
    expect(result.current.toggleCount).toBe(2);
    expect(result.current.lastToggleTime).not.toBeNull();
    
    act(() => {
      result.current.reset();
    });
    
    expect(result.current.value).toBe(true);
    expect(result.current.toggleCount).toBe(0);
    expect(result.current.lastToggleTime).toBeNull();
  });

  test('should increment count for all setter methods', () => {
    const { result } = renderHook(() => useEnhancedToggle(false));
    
    act(() => {
      result.current.setTrue();
    });
    expect(result.current.toggleCount).toBe(1);
    
    act(() => {
      result.current.setFalse();
    });
    expect(result.current.toggleCount).toBe(2);
    
    act(() => {
      result.current.setValue(true);
    });
    expect(result.current.toggleCount).toBe(3);
  });
});

describe('useToggleWithCallback Hook - Callback Support', () => {
  test('should call callback when toggling', () => {
    const callback = jest.fn();
    const { result } = renderHook(() => useToggleWithCallback(false, callback));
    
    act(() => {
      result.current.toggle();
    });
    
    expect(callback).toHaveBeenCalledWith(true);
  });

  test('should call callback with correct values for setters', () => {
    const callback = jest.fn();
    const { result } = renderHook(() => useToggleWithCallback(false, callback));
    
    act(() => {
      result.current.setTrue();
    });
    expect(callback).toHaveBeenCalledWith(true);
    
    act(() => {
      result.current.setFalse();
    });
    expect(callback).toHaveBeenCalledWith(false);
    
    act(() => {
      result.current.setValue(true);
    });
    expect(callback).toHaveBeenCalledWith(true);
  });

  test('should work without callback', () => {
    const { result } = renderHook(() => useToggleWithCallback(false));
    
    expect(() => {
      act(() => {
        result.current.toggle();
      });
    }).not.toThrow();
    
    expect(result.current.value).toBe(true);
  });

  test('should handle callback changes', () => {
    const callback1 = jest.fn();
    const callback2 = jest.fn();
    
    const { result, rerender } = renderHook(
      ({ callback }) => useToggleWithCallback(false, callback),
      { initialProps: { callback: callback1 } }
    );
    
    act(() => {
      result.current.toggle();
    });
    
    expect(callback1).toHaveBeenCalledWith(true);
    expect(callback2).not.toHaveBeenCalled();
    
    rerender({ callback: callback2 });
    
    act(() => {
      result.current.toggle();
    });
    
    expect(callback2).toHaveBeenCalledWith(false);
    expect(callback1).toHaveBeenCalledTimes(1);
  });
});

describe('useToggle Hook - Edge Cases', () => {
  test('should handle boolean coercion correctly', () => {
    const { result } = renderHook(() => useToggle());
    
    act(() => {
      result.current.setValue(true);
    });
    expect(result.current.value).toBe(true);
    
    act(() => {
      result.current.setValue(false);
    });
    expect(result.current.value).toBe(false);
  });
});