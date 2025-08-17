/**
 * Performance Testing Utilities
 * 
 * BVJ: Enterprise segment - ensures platform scalability, reduces infrastructure costs
 * Provides reusable utilities for performance and memory testing.
 */

import { React } from '../test-utils';

// Performance thresholds for Enterprise segment
export const PERFORMANCE_THRESHOLDS = {
  MEMORY_LEAK_THRESHOLD_MB: 50,
  MAX_RENDER_TIME_MS: 100,
  MAX_INTERACTION_TIME_MS: 16,
  LARGE_DATASET_SIZE: 2000,
  CHUNK_SIZE: 500,
  MAX_HISTORY_SIZE: 50,
  MAX_CONCURRENT_OPERATIONS: 3
} as const;

// Memory usage tracker for testing
export interface MemoryTracker {
  cleanupCalled: boolean;
  timersCleared: number;
  listenersRemoved: number;
}

// Resource cleanup configuration
export interface ResourceConfig {
  timers: NodeJS.Timeout[];
  listeners: Array<{
    element: EventTarget;
    event: string;
    handler: () => void;
  }>;
}

// Performance measurement utilities
export const createMemoryTracker = (): MemoryTracker => ({
  cleanupCalled: false,
  timersCleared: 0,
  listenersRemoved: 0
});

export const createResourceConfig = (): ResourceConfig => ({
  timers: [],
  listeners: []
});

export const addTimer = (
  config: ResourceConfig, 
  timer: NodeJS.Timeout
): void => {
  config.timers.push(timer);
};

export const addListener = (
  config: ResourceConfig,
  element: EventTarget,
  event: string,
  handler: () => void
): void => {
  element.addEventListener(event, handler);
  config.listeners.push({ element, event, handler });
};

export const cleanupResources = (
  config: ResourceConfig,
  tracker: MemoryTracker
): void => {
  tracker.cleanupCalled = true;
  cleanupTimers(config.timers, tracker);
  cleanupListeners(config.listeners, tracker);
};

const cleanupTimers = (
  timers: NodeJS.Timeout[],
  tracker: MemoryTracker
): void => {
  timers.forEach(timer => {
    clearInterval(timer);
    clearTimeout(timer);
    tracker.timersCleared++;
  });
};

const cleanupListeners = (
  listeners: Array<{ element: EventTarget; event: string; handler: () => void }>,
  tracker: MemoryTracker
): void => {
  listeners.forEach(({ element, event, handler }) => {
    element.removeEventListener(event, handler);
    tracker.listenersRemoved++;
  });
};

// Large dataset generation utilities
export const generateDataChunk = (
  startIndex: number,
  chunkSize: number
): Array<{ id: number; value: string; timestamp: number; data: number[] }> => {
  return Array.from({ length: chunkSize }, (_, i) => ({
    id: startIndex + i,
    value: `Item ${startIndex + i}`,
    timestamp: Date.now(),
    data: new Array(10).fill(Math.random())
  }));
};

export const calculateProgress = (
  loaded: number,
  total: number
): number => {
  return Math.round((loaded / total) * 100);
};

export const estimateMemoryUsage = (itemCount: number): number => {
  return itemCount * 0.001; // Rough memory estimate in MB
};

// Worker simulation utilities
export interface MockWorker {
  postMessage: () => void;
  terminate: () => void;
  onmessage: ((event: MessageEvent) => void) | null;
}

export const createMockWorker = (
  workers: Set<MockWorker>
): MockWorker => {
  const worker: MockWorker = {
    postMessage: () => {},
    terminate: () => workers.delete(worker),
    onmessage: null
  };
  workers.add(worker);
  return worker;
};

export const simulateWorkerResult = (): Promise<{
  id: number;
  processed: number;
  timestamp: string;
}> => {
  return new Promise(resolve => {
    setTimeout(() => {
      resolve({
        id: Date.now(),
        processed: Math.floor(Math.random() * 1000),
        timestamp: new Date().toISOString()
      });
    }, 100);
  });
};

export const terminateAllWorkers = (workers: Set<MockWorker>): void => {
  workers.forEach(worker => worker.terminate());
  workers.clear();
};

// Conflict resolution utilities
export interface Conflict {
  id: number;
  local: string;
  remote: string;
  localVersion: number;
  remoteVersion: number;
}

export const createConflict = (
  local: string,
  remote: string,
  localVersion: number,
  remoteVersion: number
): Conflict => ({
  id: Date.now(),
  local,
  remote,
  localVersion,
  remoteVersion
});

export const resolveConflictContent = (
  resolution: 'local' | 'remote' | 'merge',
  conflict: Conflict
): string => {
  switch (resolution) {
    case 'remote':
      return conflict.remote;
    case 'merge':
      return `${conflict.local} | ${conflict.remote}`;
    default:
      return conflict.local;
  }
};

// History management utilities
export const trimHistory = <T>(
  history: T[],
  maxSize: number
): T[] => {
  return history.length > maxSize 
    ? history.slice(-maxSize)
    : history;
};

export const addToHistory = <T>(
  history: T[],
  currentIndex: number,
  newItem: T,
  maxSize: number
): { newHistory: T[]; newIndex: number } => {
  const truncatedHistory = history.slice(0, currentIndex + 1);
  truncatedHistory.push(newItem);
  const trimmedHistory = trimHistory(truncatedHistory, maxSize);
  
  return {
    newHistory: trimmedHistory,
    newIndex: trimmedHistory.length - 1
  };
};

export const canUndo = (currentIndex: number): boolean => {
  return currentIndex > 0;
};

export const canRedo = (
  currentIndex: number,
  historyLength: number
): boolean => {
  return currentIndex < historyLength - 1;
};

// Async utilities for testing
export const simulateAsyncDelay = (ms: number = 10): Promise<void> => {
  return new Promise(resolve => setTimeout(resolve, ms));
};

export const createTestComponent = <P extends object>(
  Component: React.ComponentType<P>
) => {
  return (props: P) => <Component {...props} />;
};

// Performance monitoring hooks
export const usePerformanceMonitor = () => {
  const [metrics, setMetrics] = React.useState({
    renderCount: 0,
    lastRenderTime: 0
  });

  const trackRender = React.useCallback(() => {
    setMetrics(prev => ({
      renderCount: prev.renderCount + 1,
      lastRenderTime: performance.now()
    }));
  }, []);

  return { metrics, trackRender };
};