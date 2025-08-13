/**
 * Performance and Memory Management Integration Tests
 * 
 * Tests memory management, resource cleanup, large dataset handling,
 * real-time collaboration sync, and advanced error boundaries.
 */

import {
  React,
  render,
  waitFor,
  screen,
  fireEvent,
  act,
  setupTestEnvironment,
  cleanupTestEnvironment,
  createMockWebSocketServer,
  simulateNetworkDelay,
  createMockError,
  TEST_TIMEOUTS,
  WS
} from './test-utils';

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

describe('Performance and Memory Management Tests', () => {
  let server: WS;
  
  beforeEach(() => {
    server = createMockWebSocketServer();
    setupTestEnvironment(server);
  });

  afterEach(() => {
    cleanupTestEnvironment();
  });

  describe('Memory Management Integration', () => {
    it('should cleanup resources on unmount', async () => {
      const cleanupTracker = { cleanupCalled: false, timersCleared: 0, listenersRemoved: 0 };
      
      const ResourceComponent = () => {
        React.useEffect(() => {
          const timers: NodeJS.Timeout[] = [];
          const listeners: Array<{ element: EventTarget, event: string, handler: () => void }> = [];
          
          // Create resources that need cleanup
          const timer1 = setInterval(() => {}, 1000);
          const timer2 = setTimeout(() => {}, 5000);
          timers.push(timer1, timer2);
          
          const resizeHandler = () => {};
          const scrollHandler = () => {};
          window.addEventListener('resize', resizeHandler);
          document.addEventListener('scroll', scrollHandler);
          
          listeners.push(
            { element: window, event: 'resize', handler: resizeHandler },
            { element: document, event: 'scroll', handler: scrollHandler }
          );
          
          const cleanup = () => {
            cleanupTracker.cleanupCalled = true;
            
            // Clear timers
            timers.forEach(timer => {
              clearInterval(timer);
              clearTimeout(timer);
              cleanupTracker.timersCleared++;
            });
            
            // Remove listeners
            listeners.forEach(({ element, event, handler }) => {
              element.removeEventListener(event, handler);
              cleanupTracker.listenersRemoved++;
            });
          };
          
          return cleanup;
        }, []);
        
        return <div data-testid="resource-component">Resource Component Active</div>;
      };
      
      const { getByTestId, unmount } = render(<ResourceComponent />);
      
      expect(getByTestId('resource-component')).toHaveTextContent('Resource Component Active');
      expect(cleanupTracker.cleanupCalled).toBe(false);
      
      unmount();
      
      // Verify cleanup was properly executed
      expect(cleanupTracker.cleanupCalled).toBe(true);
      expect(cleanupTracker.timersCleared).toBe(2);
      expect(cleanupTracker.listenersRemoved).toBe(2);
    });

    it('should manage large data sets efficiently', async () => {
      const LargeDataComponent = () => {
        const [data, setData] = React.useState<any[]>([]);
        const [isLoading, setIsLoading] = React.useState(false);
        const [progress, setProgress] = React.useState(0);
        const [memoryUsage, setMemoryUsage] = React.useState(0);
        
        const loadLargeDataset = async () => {
          setIsLoading(true);
          setProgress(0);
          
          const chunkSize = 500;
          const totalSize = 2000;
          let loadedItems = 0;
          
          for (let i = 0; i < totalSize; i += chunkSize) {
            const chunk = Array.from({ length: Math.min(chunkSize, totalSize - i) }, (_, j) => ({
              id: i + j,
              value: `Item ${i + j}`,
              timestamp: Date.now(),
              data: new Array(10).fill(Math.random()) // Some data to consume memory
            }));
            
            setData(prev => [...prev, ...chunk]);
            loadedItems += chunk.length;
            setProgress(Math.round((loadedItems / totalSize) * 100));
            
            // Simulate memory tracking
            setMemoryUsage(loadedItems * 0.001); // Rough memory estimate
            
            // Allow UI to update between chunks
            await new Promise(resolve => setTimeout(resolve, 10));
          }
          
          setIsLoading(false);
        };
        
        const clearData = () => {
          setData([]);
          setMemoryUsage(0);
          setProgress(0);
        };
        
        // Cleanup large data on unmount to prevent memory leaks
        React.useEffect(() => {
          return () => {
            setData([]);
          };
        }, []);
        
        return (
          <div>
            <button onClick={loadLargeDataset} disabled={isLoading}>
              Load Large Dataset
            </button>
            <button onClick={clearData} disabled={isLoading}>
              Clear Data
            </button>
            <div data-testid="data-size">{data.length} items</div>
            <div data-testid="loading-status">
              {isLoading ? `Loading... ${progress}%` : 'Ready'}
            </div>
            <div data-testid="memory-usage">
              Memory: {memoryUsage.toFixed(2)}MB
            </div>
          </div>
        );
      };
      
      const { getByText, getByTestId } = render(<LargeDataComponent />);
      
      expect(getByTestId('data-size')).toHaveTextContent('0 items');
      expect(getByTestId('memory-usage')).toHaveTextContent('Memory: 0.00MB');
      
      fireEvent.click(getByText('Load Large Dataset'));
      
      await waitFor(() => {
        expect(getByTestId('loading-status')).toHaveTextContent('Loading...');
      });
      
      await waitFor(() => {
        expect(getByTestId('data-size')).toHaveTextContent('2000 items');
        expect(getByTestId('loading-status')).toHaveTextContent('Ready');
      }, { timeout: TEST_TIMEOUTS.LONG });
      
      // Verify memory usage is tracked
      const memoryText = getByTestId('memory-usage').textContent;
      expect(memoryText).toContain('Memory: 2.00MB');
      
      // Test cleanup
      fireEvent.click(getByText('Clear Data'));
      
      await waitFor(() => {
        expect(getByTestId('data-size')).toHaveTextContent('0 items');
        expect(getByTestId('memory-usage')).toHaveTextContent('Memory: 0.00MB');
      });
    });

    it('should handle memory-intensive operations with proper cleanup', async () => {
      const MemoryIntensiveComponent = () => {
        const [workers] = React.useState(() => new Set<Worker>());
        const [activeOperations, setActiveOperations] = React.useState(0);
        const [results, setResults] = React.useState<any[]>([]);
        
        const startIntensiveOperation = async () => {
          setActiveOperations(prev => prev + 1);
          
          try {
            // Simulate CPU-intensive operation
            const result = await new Promise(resolve => {
              const worker = {
                postMessage: () => {},
                terminate: () => workers.delete(worker as any),
                onmessage: null
              } as any;
              
              workers.add(worker);
              
              setTimeout(() => {
                resolve({
                  id: Date.now(),
                  processed: Math.floor(Math.random() * 1000),
                  timestamp: new Date().toISOString()
                });
                worker.terminate();
              }, 100);
            });
            
            setResults(prev => [...prev, result]);
          } finally {
            setActiveOperations(prev => prev - 1);
          }
        };
        
        // Cleanup all workers on unmount
        React.useEffect(() => {
          return () => {
            workers.forEach(worker => worker.terminate());
            workers.clear();
          };
        }, [workers]);
        
        return (
          <div>
            <button onClick={startIntensiveOperation} disabled={activeOperations >= 3}>
              Start Operation
            </button>
            <div data-testid="active-operations">{activeOperations} running</div>
            <div data-testid="worker-count">{workers.size} workers</div>
            <div data-testid="result-count">{results.length} results</div>
          </div>
        );
      };
      
      const { getByText, getByTestId, unmount } = render(<MemoryIntensiveComponent />);
      
      // Start multiple operations
      fireEvent.click(getByText('Start Operation'));
      fireEvent.click(getByText('Start Operation'));
      
      await waitFor(() => {
        expect(getByTestId('active-operations')).toHaveTextContent('2 running');
      });
      
      await waitFor(() => {
        expect(getByTestId('result-count')).toHaveTextContent('2 results');
        expect(getByTestId('active-operations')).toHaveTextContent('0 running');
      }, { timeout: TEST_TIMEOUTS.SHORT });
      
      unmount();
    });
  });

  describe('Real-time Collaboration Sync', () => {
    it('should handle conflict resolution in collaborative editing', async () => {
      const CollaborativeEditor = () => {
        const [content, setContent] = React.useState('Initial content');
        const [conflicts, setConflicts] = React.useState<any[]>([]);
        const [version, setVersion] = React.useState(1);
        const [syncStatus, setSyncStatus] = React.useState('synced');
        
        const handleLocalChange = (newContent: string) => {
          setContent(newContent);
          setSyncStatus('pending');
          setVersion(prev => prev + 1);
        };
        
        const handleRemoteChange = (remoteContent: string, remoteVersion: number) => {
          if (remoteVersion > version) {
            // Remote is newer, accept it
            setContent(remoteContent);
            setVersion(remoteVersion);
            setSyncStatus('synced');
          } else if (remoteVersion === version && remoteContent !== content) {
            // Conflict detected
            setConflicts(prev => [...prev, {
              id: Date.now(),
              local: content,
              remote: remoteContent,
              localVersion: version,
              remoteVersion
            }]);
            setSyncStatus('conflict');
          }
        };
        
        const resolveConflict = (resolution: 'local' | 'remote' | 'merge', conflictId: number) => {
          const conflict = conflicts.find(c => c.id === conflictId);
          if (!conflict) return;
          
          let resolvedContent = content;
          if (resolution === 'remote') {
            resolvedContent = conflict.remote;
          } else if (resolution === 'merge') {
            resolvedContent = `${conflict.local} | ${conflict.remote}`;
          }
          
          setContent(resolvedContent);
          setConflicts(prev => prev.filter(c => c.id !== conflictId));
          setVersion(prev => prev + 1);
          setSyncStatus('synced');
        };
        
        // Simulate receiving remote changes
        const simulateRemoteChange = (remoteContent: string) => {
          handleRemoteChange(remoteContent, version);
        };
        
        return (
          <div>
            <textarea
              data-testid="editor"
              value={content}
              onChange={(e) => handleLocalChange(e.target.value)}
            />
            <div data-testid="version">Version: {version}</div>
            <div data-testid="sync-status">Status: {syncStatus}</div>
            <div data-testid="conflict-count">{conflicts.length} conflicts</div>
            
            {conflicts.map((conflict) => (
              <div key={conflict.id} data-testid={`conflict-${conflict.id}`}>
                <div>Conflict:</div>
                <div>Local: {conflict.local}</div>
                <div>Remote: {conflict.remote}</div>
                <button onClick={() => resolveConflict('local', conflict.id)}>
                  Keep Local
                </button>
                <button onClick={() => resolveConflict('remote', conflict.id)}>
                  Keep Remote
                </button>
                <button onClick={() => resolveConflict('merge', conflict.id)}>
                  Merge Both
                </button>
              </div>
            ))}
            
            <button onClick={() => simulateRemoteChange('Remote change')}>
              Simulate Remote Change
            </button>
          </div>
        );
      };
      
      const { getByTestId, getByText } = render(<CollaborativeEditor />);
      
      expect(getByTestId('sync-status')).toHaveTextContent('Status: synced');
      expect(getByTestId('conflict-count')).toHaveTextContent('0 conflicts');
      
      // Make local change
      fireEvent.change(getByTestId('editor'), { 
        target: { value: 'Local change' } 
      });
      
      await waitFor(() => {
        expect(getByTestId('sync-status')).toHaveTextContent('Status: pending');
      });
      
      // Simulate remote change that conflicts
      fireEvent.click(getByText('Simulate Remote Change'));
      
      await waitFor(() => {
        expect(getByTestId('conflict-count')).toHaveTextContent('1 conflicts');
        expect(getByTestId('sync-status')).toHaveTextContent('Status: conflict');
      });
    });

    it('should maintain operation history for undo/redo', async () => {
      const UndoRedoComponent = () => {
        const [history, setHistory] = React.useState<string[]>(['Initial state']);
        const [currentIndex, setCurrentIndex] = React.useState(0);
        const [maxHistorySize] = React.useState(50);
        
        const performAction = (action: string) => {
          const newHistory = history.slice(0, currentIndex + 1);
          newHistory.push(action);
          
          // Limit history size to prevent memory bloat
          const trimmedHistory = newHistory.length > maxHistorySize 
            ? newHistory.slice(-maxHistorySize)
            : newHistory;
          
          setHistory(trimmedHistory);
          setCurrentIndex(trimmedHistory.length - 1);
        };
        
        const undo = () => {
          if (currentIndex > 0) {
            setCurrentIndex(currentIndex - 1);
          }
        };
        
        const redo = () => {
          if (currentIndex < history.length - 1) {
            setCurrentIndex(currentIndex + 1);
          }
        };
        
        const clearHistory = () => {
          const currentState = history[currentIndex];
          setHistory([currentState]);
          setCurrentIndex(0);
        };
        
        return (
          <div>
            <div data-testid="current-state">{history[currentIndex]}</div>
            <div data-testid="history-info">
              {currentIndex + 1} of {history.length} states
            </div>
            
            <button onClick={() => performAction(`Action at ${Date.now()}`)}>
              Perform Action
            </button>
            <button onClick={undo} disabled={currentIndex === 0}>
              Undo
            </button>
            <button onClick={redo} disabled={currentIndex === history.length - 1}>
              Redo
            </button>
            <button onClick={clearHistory}>
              Clear History
            </button>
            
            <div data-testid="can-undo">{currentIndex > 0 ? 'yes' : 'no'}</div>
            <div data-testid="can-redo">
              {currentIndex < history.length - 1 ? 'yes' : 'no'}
            </div>
          </div>
        );
      };
      
      const { getByText, getByTestId } = render(<UndoRedoComponent />);
      
      expect(getByTestId('current-state')).toHaveTextContent('Initial state');
      expect(getByTestId('can-undo')).toHaveTextContent('no');
      expect(getByTestId('can-redo')).toHaveTextContent('no');
      
      // Perform multiple actions
      fireEvent.click(getByText('Perform Action'));
      fireEvent.click(getByText('Perform Action'));
      fireEvent.click(getByText('Perform Action'));
      
      await waitFor(() => {
        expect(getByTestId('history-info')).toHaveTextContent('4 of 4 states');
        expect(getByTestId('can-undo')).toHaveTextContent('yes');
      });
      
      // Test undo
      fireEvent.click(getByText('Undo'));
      
      await waitFor(() => {
        expect(getByTestId('history-info')).toHaveTextContent('3 of 4 states');
        expect(getByTestId('can-redo')).toHaveTextContent('yes');
      });
      
      // Test redo
      fireEvent.click(getByText('Redo'));
      
      await waitFor(() => {
        expect(getByTestId('history-info')).toHaveTextContent('4 of 4 states');
        expect(getByTestId('can-redo')).toHaveTextContent('no');
      });
    });
  });

  describe('Advanced Error Boundaries', () => {
    it('should recover from component errors gracefully', async () => {
      class ErrorBoundary extends React.Component<
        { children: React.ReactNode },
        { hasError: boolean; errorInfo: any; retryCount: number }
      > {
        constructor(props: any) {
          super(props);
          this.state = { hasError: false, errorInfo: null, retryCount: 0 };
        }
        
        static getDerivedStateFromError(error: Error) {
          return { hasError: true };
        }
        
        componentDidCatch(error: Error, errorInfo: any) {
          this.setState({ errorInfo });
        }
        
        retry = () => {
          this.setState(prev => ({
            hasError: false,
            errorInfo: null,
            retryCount: prev.retryCount + 1
          }));
        }
        
        render() {
          if (this.state.hasError) {
            return (
              <div data-testid="error-boundary">
                <div>Something went wrong!</div>
                <div data-testid="retry-count">Retries: {this.state.retryCount}</div>
                <button onClick={this.retry}>Try Again</button>
              </div>
            );
          }
          
          return this.props.children;
        }
      }
      
      const ProblematicComponent = ({ shouldError }: { shouldError: boolean }) => {
        if (shouldError) {
          throw createMockError('Component error for testing');
        }
        return <div data-testid="working-component">Component working fine</div>;
      };
      
      const TestWrapper = () => {
        const [shouldError, setShouldError] = React.useState(false);
        
        return (
          <div>
            <button onClick={() => setShouldError(true)}>Trigger Error</button>
            <button onClick={() => setShouldError(false)}>Fix Component</button>
            <ErrorBoundary>
              <ProblematicComponent shouldError={shouldError} />
            </ErrorBoundary>
          </div>
        );
      };
      
      const { getByText, getByTestId } = render(<TestWrapper />);
      
      // Initially working
      expect(getByTestId('working-component')).toHaveTextContent('Component working fine');
      
      // Trigger error
      fireEvent.click(getByText('Trigger Error'));
      
      await waitFor(() => {
        expect(getByTestId('error-boundary')).toHaveTextContent('Something went wrong!');
        expect(getByTestId('retry-count')).toHaveTextContent('Retries: 0');
      });
      
      // Try to retry (will still error)
      fireEvent.click(getByText('Try Again'));
      
      await waitFor(() => {
        expect(getByTestId('retry-count')).toHaveTextContent('Retries: 1');
      });
      
      // Fix the component first, then retry
      fireEvent.click(getByText('Fix Component'));
      fireEvent.click(getByText('Try Again'));
      
      await waitFor(() => {
        expect(getByTestId('working-component')).toHaveTextContent('Component working fine');
      });
    });
  });
});