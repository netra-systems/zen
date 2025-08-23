/**
 * React Act Testing Utilities
 * 
 * Comprehensive helpers for wrapping all state updates in act() to prevent warnings.
 * Use these utilities whenever you need to perform actions that trigger React state changes.
 */

import { act, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

/**
 * Wrap a Promise or timeout in act() for async operations
 */
export async function actWait(ms: number = 0): Promise<void> {
  await act(async () => {
    await new Promise(resolve => setTimeout(resolve, ms));
  });
}

/**
 * Wrap an async function call in act()
 */
export async function actAsync<T>(fn: () => Promise<T>): Promise<T> {
  let result: T;
  await act(async () => {
    result = await fn();
  });
  return result!;
}

/**
 * Wrap a synchronous function call in act()
 */
export function actSync<T>(fn: () => T): T {
  let result: T;
  act(() => {
    result = fn();
  });
  return result!;
}

/**
 * Create a callback wrapper that automatically wraps state updates in act()
 * Perfect for event handlers, WebSocket callbacks, and other async callbacks
 */
export function createActCallback<T extends (...args: any[]) => void>(callback: T): T {
  return ((...args: any[]) => {
    act(() => {
      callback(...args);
    });
  }) as T;
}

/**
 * Create an async callback wrapper that automatically wraps state updates in act()
 */
export function createActAsyncCallback<T extends (...args: any[]) => Promise<void>>(callback: T): T {
  return (async (...args: any[]) => {
    await act(async () => {
      await callback(...args);
    });
  }) as T;
}

/**
 * Wrap timer-based operations in act()
 */
export async function actTimer(fn: () => void, delay: number = 0): Promise<void> {
  await act(async () => {
    return new Promise<void>(resolve => {
      setTimeout(() => {
        fn();
        resolve();
      }, delay);
    });
  });
}

/**
 * Wrap state setter functions to always use act()
 */
export function wrapStateSetterWithAct<T>(setter: (value: T | ((prev: T) => T)) => void) {
  return (value: T | ((prev: T) => T)) => {
    act(() => {
      setter(value);
    });
  };
}

// ============================================================================
// ENHANCED UTILITIES FOR COMMON TEST PATTERNS
// ============================================================================

/**
 * Wrapped fireEvent that automatically uses act() for all event types
 */
export const actFireEvent = {
  click: async (element: Element) => {
    await act(async () => {
      fireEvent.click(element);
    });
  },
  
  change: async (element: Element, eventInit?: EventInit) => {
    await act(async () => {
      fireEvent.change(element, eventInit);
    });
  },
  
  input: async (element: Element, eventInit?: EventInit) => {
    await act(async () => {
      fireEvent.input(element, eventInit);
    });
  },
  
  submit: async (element: Element) => {
    await act(async () => {
      fireEvent.submit(element);
    });
  },
  
  keyDown: async (element: Element, eventInit?: EventInit) => {
    await act(async () => {
      fireEvent.keyDown(element, eventInit);
    });
  },
  
  keyUp: async (element: Element, eventInit?: EventInit) => {
    await act(async () => {
      fireEvent.keyUp(element, eventInit);
    });
  },
  
  focus: async (element: Element) => {
    await act(async () => {
      fireEvent.focus(element);
    });
  },
  
  blur: async (element: Element) => {
    await act(async () => {
      fireEvent.blur(element);
    });
  },
  
  touchStart: async (element: Element, eventInit?: EventInit) => {
    await act(async () => {
      fireEvent.touchStart(element, eventInit);
    });
  },
  
  touchEnd: async (element: Element, eventInit?: EventInit) => {
    await act(async () => {
      fireEvent.touchEnd(element, eventInit);
    });
  }
};

/**
 * Wrapped userEvent methods that ensure proper act() handling
 */
export const createActUserEvent = () => {
  const user = userEvent.setup();
  
  return {
    type: async (element: Element, text: string, options?: Parameters<typeof user.type>[2]) => {
      await act(async () => {
        await user.type(element, text, options);
      });
    },
    
    click: async (element: Element, options?: Parameters<typeof user.click>[1]) => {
      await act(async () => {
        await user.click(element, options);
      });
    },
    
    clear: async (element: Element) => {
      await act(async () => {
        await user.clear(element);
      });
    },
    
    keyboard: async (text: string, options?: Parameters<typeof user.keyboard>[1]) => {
      await act(async () => {
        await user.keyboard(text, options);
      });
    },
    
    selectOptions: async (element: Element, values: string | string[], options?: Parameters<typeof user.selectOptions>[2]) => {
      await act(async () => {
        await user.selectOptions(element, values, options);
      });
    },
    
    upload: async (element: Element, file: File | File[], options?: Parameters<typeof user.upload>[2]) => {
      await act(async () => {
        await user.upload(element, file, options);
      });
    }
  };
};

/**
 * Enhanced waitFor that works well with act()
 */
export const actWaitFor = async <T>(
  callback: () => T | Promise<T>,
  options?: Parameters<typeof waitFor>[1]
): Promise<T> => {
  let result: T;
  await act(async () => {
    result = await waitFor(callback, options);
  });
  return result!;
};

/**
 * Jest timer controls wrapped in act()
 */
export const actJest = {
  runAllTimers: async () => {
    await act(async () => {
      jest.runAllTimers();
    });
  },
  
  runOnlyPendingTimers: async () => {
    await act(async () => {
      jest.runOnlyPendingTimers();
    });
  },
  
  advanceTimersByTime: async (msToRun: number) => {
    await act(async () => {
      jest.advanceTimersByTime(msToRun);
    });
  },
  
  advanceTimersToNextTimer: async (steps?: number) => {
    await act(async () => {
      jest.advanceTimersToNextTimer(steps);
    });
  }
};

/**
 * Flush all microtasks and wait for DOM updates
 */
export const flushMicrotasks = async () => {
  await act(async () => {
    await new Promise(resolve => {
      setImmediate(resolve);
    });
  });
};

/**
 * Create a mock function that automatically wraps its calls in act()
 */
export function createActMockFunction<T extends (...args: any[]) => any>(
  implementation?: T
): jest.MockedFunction<T> {
  const mockFn = jest.fn();
  
  if (implementation) {
    mockFn.mockImplementation((...args: any[]) => {
      let result: any;
      act(() => {
        result = implementation(...args);
      });
      return result;
    });
  }
  
  return mockFn as jest.MockedFunction<T>;
}

/**
 * Create an async mock function that automatically wraps its calls in act()
 */
export function createActAsyncMockFunction<T extends (...args: any[]) => Promise<any>>(
  implementation?: T
): jest.MockedFunction<T> {
  const mockFn = jest.fn();
  
  if (implementation) {
    mockFn.mockImplementation(async (...args: any[]) => {
      let result: any;
      await act(async () => {
        result = await implementation(...args);
      });
      return result;
    });
  }
  
  return mockFn as jest.MockedFunction<T>;
}

/**
 * Batch multiple act-wrapped operations
 */
export async function actBatch(operations: Array<() => void | Promise<void>>): Promise<void> {
  await act(async () => {
    for (const operation of operations) {
      await operation();
    }
  });
}

export { act, fireEvent, waitFor };