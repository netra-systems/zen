/**
 * State Timing Utilities for Integration Tests
 * CRITICAL: Fixes state management timing issues and race conditions
 * Ensures proper state synchronization in async operations
 * ≤300 lines, ≤8 lines per function
 */

import React from 'react';
import { act, waitFor } from '@testing-library/react';

export interface StateWaitOptions {
  timeout?: number;
  interval?: number;
  retries?: number;
  strict?: boolean;
}

export interface StateChangeEvent<T> {
  previousState: T;
  nextState: T;
  timestamp: number;
  source: string;
}

/**
 * State Manager with timing synchronization
 */
export class StateTimingManager<T = any> {
  private state: T;
  private listeners: ((state: T) => void)[] = [];
  private changeHistory: StateChangeEvent<T>[] = [];
  private pendingUpdates: (() => void)[] = [];

  constructor(initialState: T) {
    this.state = initialState;
  }

  async setState(newState: Partial<T>, source = 'unknown'): Promise<void> {
    return act(async () => {
      const previousState = { ...this.state };
      this.state = { ...this.state, ...newState };
      
      this.changeHistory.push({
        previousState,
        nextState: this.state,
        timestamp: Date.now(),
        source
      });

      await this.notifyListeners();
    });
  }

  getState(): T {
    return { ...this.state };
  }

  subscribe(listener: (state: T) => void): () => void {
    this.listeners.push(listener);
    return () => {
      const index = this.listeners.indexOf(listener);
      if (index > -1) this.listeners.splice(index, 1);
    };
  }

  async waitForState(
    predicate: (state: T) => boolean,
    options: StateWaitOptions = {}
  ): Promise<T> {
    const { timeout = 5000, interval = 50 } = options;

    return waitFor(() => {
      const currentState = this.getState();
      if (predicate(currentState)) {
        return currentState;
      }
      throw new Error('State condition not met');
    }, { timeout, interval });
  }

  private async notifyListeners(): Promise<void> {
    await Promise.all(
      this.listeners.map(listener => 
        act(async () => {
          listener(this.state);
        })
      )
    );
  }

  getChangeHistory(): StateChangeEvent<T>[] {
    return [...this.changeHistory];
  }

  clearHistory(): void {
    this.changeHistory = [];
  }

  reset(initialState: T): void {
    act(() => {
      this.state = initialState;
      this.changeHistory = [];
    });
  }
}

/**
 * React Hook for State Timing Management
 */
export function useStateTimingManager<T>(initialState: T) {
  const [manager] = React.useState(() => new StateTimingManager(initialState));
  const [state, setState] = React.useState<T>(initialState);

  React.useEffect(() => {
    const unsubscribe = manager.subscribe((newState) => {
      setState(newState);
    });
    return unsubscribe;
  }, [manager]);

  return {
    state,
    setState: (newState: Partial<T>, source?: string) => manager.setState(newState, source),
    waitForState: (predicate: (state: T) => boolean, options?: StateWaitOptions) => 
      manager.waitForState(predicate, options),
    getHistory: () => manager.getChangeHistory(),
    reset: (newInitialState: T) => manager.reset(newInitialState)
  };
}

/**
 * Async State Operations with proper timing
 */
export class AsyncStateOperations {
  private static pendingOperations = new Map<string, Promise<any>>();

  static async sequentialUpdate<T>(
    operations: (() => Promise<T>)[]
  ): Promise<T[]> {
    const results: T[] = [];
    
    for (const operation of operations) {
      const result = await act(async () => {
        return operation();
      });
      results.push(result);
    }
    
    return results;
  }

  static async parallelUpdate<T>(
    operations: (() => Promise<T>)[]
  ): Promise<T[]> {
    return act(async () => {
      return Promise.all(operations.map(op => op()));
    });
  }

  static async batchedUpdate<T>(
    operations: (() => Promise<T>)[],
    batchSize: number = 3
  ): Promise<T[]> {
    const results: T[] = [];
    
    for (let i = 0; i < operations.length; i += batchSize) {
      const batch = operations.slice(i, i + batchSize);
      const batchResults = await this.parallelUpdate(batch);
      results.push(...batchResults);
    }
    
    return results;
  }

  static async debouncedUpdate<T>(
    operation: () => Promise<T>,
    key: string,
    delay: number = 100
  ): Promise<T> {
    // Cancel previous operation with same key
    const existingOperation = this.pendingOperations.get(key);
    if (existingOperation) {
      // Note: In real implementation, you'd cancel the promise
      this.pendingOperations.delete(key);
    }

    const newOperation = act(async () => {
      await new Promise(resolve => setTimeout(resolve, delay));
      return operation();
    });

    this.pendingOperations.set(key, newOperation);
    
    try {
      const result = await newOperation;
      this.pendingOperations.delete(key);
      return result;
    } catch (error) {
      this.pendingOperations.delete(key);
      throw error;
    }
  }
}

/**
 * Race Condition Prevention Utilities
 */
export class RaceConditionPrevention {
  private static locks = new Map<string, Promise<any>>();

  static async withLock<T>(
    key: string,
    operation: () => Promise<T>
  ): Promise<T> {
    // Wait for existing lock to release
    const existingLock = this.locks.get(key);
    if (existingLock) {
      await existingLock.catch(() => {}); // Ignore errors
    }

    // Create new lock
    const lockPromise = act(async () => {
      return operation();
    });

    this.locks.set(key, lockPromise);

    try {
      const result = await lockPromise;
      this.locks.delete(key);
      return result;
    } catch (error) {
      this.locks.delete(key);
      throw error;
    }
  }

  static async serialized<T>(
    operations: { key: string; operation: () => Promise<T> }[]
  ): Promise<T[]> {
    const results: T[] = [];
    
    for (const { key, operation } of operations) {
      const result = await this.withLock(key, operation);
      results.push(result);
    }
    
    return results;
  }

  static clearLocks(): void {
    this.locks.clear();
  }
}

/**
 * State Synchronization Utilities
 */
export const StateSynchronization = {
  async waitForMultipleStates<T>(
    conditions: Array<{
      manager: StateTimingManager<T>;
      predicate: (state: T) => boolean;
      name?: string;
    }>,
    options: StateWaitOptions = {}
  ): Promise<T[]> {
    const { timeout = 5000 } = options;
    
    return Promise.race([
      Promise.all(
        conditions.map(({ manager, predicate }) => 
          manager.waitForState(predicate, options)
        )
      ),
      new Promise<never>((_, reject) => 
        setTimeout(() => reject(new Error('Multi-state wait timeout')), timeout)
      )
    ]);
  },

  async syncStates<T>(
    managers: StateTimingManager<T>[],
    targetState: Partial<T>
  ): Promise<void> {
    await Promise.all(
      managers.map(manager => 
        manager.setState(targetState, 'sync')
      )
    );
  },

  async waitForStateStability<T>(
    manager: StateTimingManager<T>,
    stabilityDuration: number = 100
  ): Promise<T> {
    let lastChangeTime = Date.now();
    let stableState: T = manager.getState();

    const unsubscribe = manager.subscribe((newState) => {
      lastChangeTime = Date.now();
      stableState = newState;
    });

    try {
      return await waitFor(() => {
        if (Date.now() - lastChangeTime >= stabilityDuration) {
          return stableState;
        }
        throw new Error('State not stable');
      }, { timeout: 5000 });
    } finally {
      unsubscribe();
    }
  }
};

/**
 * Test Component for State Timing
 */
export const StateTimingTestComponent: React.FC<{
  initialState?: any;
  onStateChange?: (state: any) => void;
}> = ({ initialState = {}, onStateChange }) => {
  const { state, setState, waitForState } = useStateTimingManager(initialState);

  React.useEffect(() => {
    onStateChange?.(state);
  }, [state, onStateChange]);

  return (
    <div data-testid="state-timing-test">
      <div data-testid="current-state">{JSON.stringify(state)}</div>
      <button 
        data-testid="update-state" 
        onClick={() => setState({ updated: Date.now() })}
      >
        Update State
      </button>
      <button
        data-testid="async-update"
        onClick={async () => {
          await setState({ loading: true });
          await new Promise(resolve => setTimeout(resolve, 100));
          await setState({ loading: false, result: 'success' });
        }}
      >
        Async Update
      </button>
    </div>
  );
};

/**
 * Utility Functions for Common Patterns
 */
export const StateTimingUtils = {
  createManager: <T extends any>(initialState: T) => new StateTimingManager(initialState),
  
  async: AsyncStateOperations,
  
  raceCondition: RaceConditionPrevention,
  
  sync: StateSynchronization,

  async flushStateUpdates(): Promise<void> {
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 0));
    });
  },

  async waitForDOMUpdate(): Promise<void> {
    await act(async () => {
      await new Promise(resolve => requestAnimationFrame(() => resolve(undefined)));
    });
  }
};

export default StateTimingUtils;