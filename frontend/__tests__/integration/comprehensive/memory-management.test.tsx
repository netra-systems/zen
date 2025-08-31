import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
import { mory Management Integration Tests
 * 
 * BVJ: Enterprise segment - ensures platform scalability, reduces infrastructure costs
 * Tests memory management, resource cleanup, and large dataset handling.
 */

import {
  React,
  render,
  waitFor,
  fireEvent,
  setupTestEnvironment,
  cleanupTestEnvironment,
  createMockWebSocketServer,
  TEST_TIMEOUTS,
  WS
} from './test-utils';

import {
  PERFORMANCE_THRESHOLDS,
  createMemoryTracker,
  createResourceConfig,
  addTimer,
  addListener,
  cleanupResources,
  generateDataChunk,
  calculateProgress,
  estimateMemoryUsage,
  simulateAsyncDelay,
  createMockWorker,
  simulateWorkerResult,
  terminateAllWorkers
} from './utils/performance-test-utils';

// Apply Next.js navigation mock
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    refresh: jest.fn(),
    back: jest.fn(),
    forward: jest.fn(),
    pathname: '/',
    query: {},
    asPath: '/',
  }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
}));

describe('Memory Management Integration Tests', () => {
    jest.setTimeout(10000);
  let server: WS;
  
  beforeEach(() => {
    server = createMockWebSocketServer();
    setupTestEnvironment(server);
  });

  afterEach(() => {
    cleanupTestEnvironment();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
  });

  describe('Resource Cleanup', () => {
      jest.setTimeout(10000);
    it('should cleanup resources on unmount', async () => {
      const tracker = createMemoryTracker();
      const ResourceComponent = createResourceComponent(tracker);
      
      const { getByTestId, unmount } = render(<ResourceComponent />);
      
      expect(getByTestId('resource-component')).toHaveTextContent('Resource Component Active');
      expect(tracker.cleanupCalled).toBe(false);
      
      unmount();
      
      verifyResourceCleanup(tracker);
    });

    it('should handle multiple resource types', async () => {
      const tracker = createMemoryTracker();
      const MultiResourceComponent = createMultiResourceComponent(tracker);
      
      const { unmount } = render(<MultiResourceComponent />);
      
      unmount();
      
      expect(tracker.cleanupCalled).toBe(true);
      expect(tracker.timersCleared).toBeGreaterThan(0);
      expect(tracker.listenersRemoved).toBeGreaterThan(0);
    });
  });

  describe('Large Dataset Management', () => {
      jest.setTimeout(10000);
    it('should manage large data sets efficiently', async () => {
      const LargeDataComponent = createLargeDataComponent();
      
      const { getByText, getByTestId } = render(<LargeDataComponent />);
      
      verifyInitialDataState(getByTestId);
      
      fireEvent.click(getByText('Load Large Dataset'));
      
      await verifyDataLoading(getByTestId);
      await verifyDataLoaded(getByTestId);
      
      fireEvent.click(getByText('Clear Data'));
      
      await verifyDataCleared(getByTestId);
    });

    it('should handle chunked loading with progress', async () => {
      const ChunkedLoadingComponent = createChunkedLoadingComponent();
      
      const { getByText, getByTestId } = render(<ChunkedLoadingComponent />);
      
      fireEvent.click(getByText('Load Data'));
      
      await verifyProgressUpdates(getByTestId);
      await verifyChunkedLoadingComplete(getByTestId);
    });
  });

  describe('Memory-Intensive Operations', () => {
      jest.setTimeout(10000);
    it('should handle memory-intensive operations with proper cleanup', async () => {
      const MemoryIntensiveComponent = createMemoryIntensiveComponent();
      
      const { getByText, getByTestId, unmount } = render(<MemoryIntensiveComponent />);
      
      await startMultipleOperations(getByText, getByTestId);
      await verifyOperationsComplete(getByTestId);
      
      unmount();
    });

    it('should limit concurrent operations', async () => {
      const ConcurrentLimitComponent = createConcurrentLimitComponent();
      
      const { getByText, getByTestId } = render(<ConcurrentLimitComponent />);
      
      await testConcurrencyLimit(getByText, getByTestId);
    });
  });
});

// Component factory functions (≤8 lines each)
const createResourceComponent = (tracker: any) => {
  return () => {
    React.useEffect(() => {
      const config = createResourceConfig();
      setupResourcesForTesting(config);
      return () => cleanupResources(config, tracker);
    }, []);
    
    return <div data-testid="resource-component">Resource Component Active</div>;
  };
};

const createMultiResourceComponent = (tracker: any) => {
  return () => {
    React.useEffect(() => {
      const config = createResourceConfig();
      setupMultipleResources(config);
      return () => cleanupResources(config, tracker);
    }, []);
    
    return <div data-testid="multi-resource">Multiple Resources Active</div>;
  };
};

const createLargeDataComponent = () => {
  return () => {
    const [data, setData] = React.useState<any[]>([]);
    const [isLoading, setIsLoading] = React.useState(false);
    const [progress, setProgress] = React.useState(0);
    const [memoryUsage, setMemoryUsage] = React.useState(0);
    
    const loadLargeDataset = () => loadDatasetWithProgress(
      setData, setIsLoading, setProgress, setMemoryUsage
    );
    
    const clearData = () => clearDataState(setData, setMemoryUsage, setProgress);
    
    return renderLargeDataUI(data, isLoading, progress, memoryUsage, loadLargeDataset, clearData);
  };
};

const createChunkedLoadingComponent = () => {
  return () => {
    const [chunks, setChunks] = React.useState<any[]>([]);
    const [loading, setLoading] = React.useState(false);
    
    const loadData = () => loadChunkedData(setChunks, setLoading);
    
    return renderChunkedLoadingUI(chunks, loading, loadData);
  };
};

const createMemoryIntensiveComponent = () => {
  return () => {
    const [workers] = React.useState(() => new Set<any>());
    const [activeOperations, setActiveOperations] = React.useState(0);
    const [results, setResults] = React.useState<any[]>([]);
    
    const startOperation = () => startIntensiveOperation(
      workers, setActiveOperations, setResults
    );
    
    React.useEffect(() => () => terminateAllWorkers(workers), [workers]);
    
    return renderMemoryIntensiveUI(activeOperations, workers, results, startOperation);
  };
};

const createConcurrentLimitComponent = () => {
  return () => {
    const [operations, setOperations] = React.useState(0);
    const [maxReached, setMaxReached] = React.useState(false);
    
    const startOperation = () => startLimitedOperation(setOperations, setMaxReached);
    
    return renderConcurrentLimitUI(operations, maxReached, startOperation);
  };
};

// Setup utility functions (≤8 lines each)
const setupResourcesForTesting = (config: any): void => {
  const timer1 = setInterval(() => {}, 1000);
  const timer2 = setTimeout(() => {}, 1000);
  addTimer(config, timer1);
  addTimer(config, timer2);
  
  const resizeHandler = () => {};
  const scrollHandler = () => {};
  addListener(config, window, 'resize', resizeHandler);
  addListener(config, document, 'scroll', scrollHandler);
};

const setupMultipleResources = (config: any): void => {
  for (let i = 0; i < 5; i++) {
    const timer = setTimeout(() => {}, i * 1000);
    addTimer(config, timer);
  }
  
  const handlers = [() => {}, () => {}, () => {}];
  handlers.forEach((handler, index) => {
    addListener(config, window, `event${index}`, handler);
  });
};

const loadDatasetWithProgress = async (
  setData: any, setIsLoading: any, setProgress: any, setMemoryUsage: any
): Promise<void> => {
  setIsLoading(true);
  setProgress(0);
  
  const { LARGE_DATASET_SIZE, CHUNK_SIZE } = PERFORMANCE_THRESHOLDS;
  let loadedItems = 0;
  
  for (let i = 0; i < LARGE_DATASET_SIZE; i += CHUNK_SIZE) {
    const remainingItems = Math.min(CHUNK_SIZE, LARGE_DATASET_SIZE - i);
    const chunk = generateDataChunk(i, remainingItems);
    
    setData((prev: any[]) => [...prev, ...chunk]);
    loadedItems += chunk.length;
    setProgress(calculateProgress(loadedItems, LARGE_DATASET_SIZE));
    setMemoryUsage(estimateMemoryUsage(loadedItems));
    
    await simulateAsyncDelay();
  }
  
  setIsLoading(false);
};

const loadChunkedData = async (setChunks: any, setLoading: any): Promise<void> => {
  setLoading(true);
  
  for (let i = 0; i < 5; i++) {
    const chunk = generateDataChunk(i * 100, 100);
    setChunks((prev: any[]) => [...prev, chunk]);
    await simulateAsyncDelay(50);
  }
  
  setLoading(false);
};

const startIntensiveOperation = async (
  workers: Set<any>, setActiveOperations: any, setResults: any
): Promise<void> => {
  setActiveOperations((prev: number) => prev + 1);
  
  try {
    const worker = createMockWorker(workers);
    const result = await simulateWorkerResult();
    setResults((prev: any[]) => [...prev, result]);
    worker.terminate();
  } finally {
    setActiveOperations((prev: number) => prev - 1);
  }
};

const startLimitedOperation = (setOperations: any, setMaxReached: any): void => {
  setOperations((prev: number) => {
    const newCount = prev + 1;
    if (newCount >= PERFORMANCE_THRESHOLDS.MAX_CONCURRENT_OPERATIONS) {
      setMaxReached(true);
    }
    return newCount;
  });
  
  setTimeout(() => {
    setOperations((prev: number) => prev - 1);
    setMaxReached(false);
  }, 1000);
};

// UI rendering functions (≤8 lines each)
const renderLargeDataUI = (
  data: any[], isLoading: boolean, progress: number, memoryUsage: number,
  loadDataset: () => void, clearData: () => void
) => (
  <div>
    <button onClick={loadDataset} disabled={isLoading}>Load Large Dataset</button>
    <button onClick={clearData} disabled={isLoading}>Clear Data</button>
    <div data-testid="data-size">{data.length} items</div>
    <div data-testid="loading-status">{isLoading ? `Loading... ${progress}%` : 'Ready'}</div>
    <div data-testid="memory-usage">Memory: {memoryUsage.toFixed(2)}MB</div>
  </div>
);

const renderChunkedLoadingUI = (chunks: any[], loading: boolean, loadData: () => void) => (
  <div>
    <button onClick={loadData} disabled={loading}>Load Data</button>
    <div data-testid="chunk-count">{chunks.length} chunks</div>
    <div data-testid="loading-status">{loading ? 'Loading...' : 'Ready'}</div>
  </div>
);

const renderMemoryIntensiveUI = (
  activeOperations: number, workers: Set<any>, results: any[], startOperation: () => void
) => (
  <div>
    <button onClick={startOperation} disabled={activeOperations >= PERFORMANCE_THRESHOLDS.MAX_CONCURRENT_OPERATIONS}>
      Start Operation
    </button>
    <div data-testid="active-operations">{activeOperations} running</div>
    <div data-testid="worker-count">{workers.size} workers</div>
    <div data-testid="result-count">{results.length} results</div>
  </div>
);

const renderConcurrentLimitUI = (operations: number, maxReached: boolean, startOperation: () => void) => (
  <div>
    <button onClick={startOperation} disabled={maxReached}>Start Operation</button>
    <div data-testid="operation-count">{operations} operations</div>
    <div data-testid="max-reached">{maxReached ? 'yes' : 'no'}</div>
  </div>
);

// Verification functions (≤8 lines each)
const verifyResourceCleanup = (tracker: any): void => {
  expect(tracker.cleanupCalled).toBe(true);
  expect(tracker.timersCleared).toBe(2);
  expect(tracker.listenersRemoved).toBe(2);
};

const verifyInitialDataState = (getByTestId: any): void => {
  expect(getByTestId('data-size')).toHaveTextContent('0 items');
  expect(getByTestId('memory-usage')).toHaveTextContent('Memory: 0.00MB');
};

const verifyDataLoading = async (getByTestId: any): Promise<void> => {
  await waitFor(() => {
    expect(getByTestId('loading-status')).toHaveTextContent('Loading...');
  });
};

const verifyDataLoaded = async (getByTestId: any): Promise<void> => {
  await waitFor(() => {
    expect(getByTestId('data-size')).toHaveTextContent('2000 items');
    expect(getByTestId('loading-status')).toHaveTextContent('Ready');
  }, { timeout: TEST_TIMEOUTS.LONG });
  
  const memoryText = getByTestId('memory-usage').textContent;
  expect(memoryText).toContain('Memory: 2.00MB');
};

const verifyDataCleared = async (getByTestId: any): Promise<void> => {
  await waitFor(() => {
    expect(getByTestId('data-size')).toHaveTextContent('0 items');
    expect(getByTestId('memory-usage')).toHaveTextContent('Memory: 0.00MB');
  });
};

const verifyProgressUpdates = async (getByTestId: any): Promise<void> => {
  await waitFor(() => {
    expect(getByTestId('loading-status')).toHaveTextContent('Loading...');
  });
};

const verifyChunkedLoadingComplete = async (getByTestId: any): Promise<void> => {
  await waitFor(() => {
    expect(getByTestId('chunk-count')).toHaveTextContent('5 chunks');
    expect(getByTestId('loading-status')).toHaveTextContent('Ready');
  }, { timeout: TEST_TIMEOUTS.SHORT });
};

const startMultipleOperations = async (getByText: any, getByTestId: any): Promise<void> => {
  fireEvent.click(getByText('Start Operation'));
  fireEvent.click(getByText('Start Operation'));
  
  await waitFor(() => {
    expect(getByTestId('active-operations')).toHaveTextContent('2 running');
  });
};

const verifyOperationsComplete = async (getByTestId: any): Promise<void> => {
  await waitFor(() => {
    expect(getByTestId('result-count')).toHaveTextContent('2 results');
    expect(getByTestId('active-operations')).toHaveTextContent('0 running');
  }, { timeout: TEST_TIMEOUTS.SHORT });
};

const testConcurrencyLimit = async (getByText: any, getByTestId: any): Promise<void> => {
  // Start maximum allowed operations
  for (let i = 0; i < PERFORMANCE_THRESHOLDS.MAX_CONCURRENT_OPERATIONS; i++) {
    fireEvent.click(getByText('Start Operation'));
  }
  
  await waitFor(() => {
    expect(getByTestId('max-reached')).toHaveTextContent('yes');
  });
};

const clearDataState = (setData: any, setMemoryUsage: any, setProgress: any): void => {
  setData([]);
  setMemoryUsage(0);
  setProgress(0);
};