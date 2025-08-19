/**
 * Performance Test Helpers
 * 
 * Shared utilities, components, and verification functions for performance testing.
 * BVJ: Enterprise segment - reusable performance testing infrastructure.
 */

import {
  React,
  fireEvent,
  waitFor,
  act,
  simulateAsyncDelay,
  usePerformanceMonitor,
  TEST_TIMEOUTS
} from '../test-utils';
import { PERFORMANCE_THRESHOLDS } from '../utils/performance-test-utils';

// Performance monitoring utilities (≤8 lines each)
export const measureRenderTime = (renderFn: () => void): number => {
  const startTime = performance.now();
  renderFn();
  return performance.now() - startTime;
};

export const measureInteractionLatency = async (
  interaction: () => void,
  verification: () => boolean
): Promise<number> => {
  const startTime = performance.now();
  interaction();
  
  while (!verification() && (performance.now() - startTime) < 1000) {
    await simulateAsyncDelay(1);
  }
  
  return performance.now() - startTime;
};

export const createPerformanceProfiler = () => {
  const measurements: Array<{ name: string; duration: number; timestamp: number }> = [];
  
  const startMeasurement = (name: string) => {
    const startTime = performance.now();
    return () => {
      const duration = performance.now() - startTime;
      measurements.push({ name, duration, timestamp: Date.now() });
      return duration;
    };
  };
  
  return { measurements, startMeasurement };
};

// Utility functions (≤8 lines each)
export const debounce = <T extends (...args: any[]) => void>(func: T, delay: number): T => {
  let timeoutId: NodeJS.Timeout;
  
  return ((...args: any[]) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => func(...args), delay);
  }) as T;
};

// Component factory functions (≤8 lines each)
export const createLargeListComponent = () => {
  return () => {
    const items = React.useMemo(() => 
      Array.from({ length: 1000 }, (_, i) => ({ id: i, value: `Item ${i}` })), []
    );
    
    const { metrics, trackRender } = usePerformanceMonitor();
    
    React.useEffect(() => {
      trackRender();
    });
    
    return renderLargeList(items, metrics);
  };
};

export const createRapidRerenderComponent = () => {
  return () => {
    const [counter, setCounter] = React.useState(0);
    const [renderTimes, setRenderTimes] = React.useState<number[]>([]);
    
    const triggerRerender = () => {
      const startTime = performance.now();
      setCounter(c => c + 1);
      
      React.startTransition(() => {
        setRenderTimes(prev => [...prev, performance.now() - startTime]);
      });
    };
    
    return renderRapidRerenderComponent(counter, renderTimes, triggerRerender);
  };
};

export const createVirtualScrollComponent = () => {
  return () => {
    const [visibleItems, setVisibleItems] = React.useState(20);
    const [scrollPerformance, setScrollPerformance] = React.useState<number[]>([]);
    
    const handleVirtualScroll = (direction: 'up' | 'down') => {
      const startTime = performance.now();
      
      if (direction === 'down' && visibleItems < 1000) {
        setVisibleItems(v => Math.min(v + 20, 1000));
      } else if (direction === 'up' && visibleItems > 20) {
        setVisibleItems(v => Math.max(v - 20, 20));
      }
      
      setScrollPerformance(prev => [...prev, performance.now() - startTime]);
    };
    
    return renderVirtualScrollComponent(visibleItems, scrollPerformance, handleVirtualScroll);
  };
};

export const createInteractiveComponent = () => {
  return () => {
    const [interactions, setInteractions] = React.useState<Array<{ latency: number; timestamp: number }>>([]);
    
    const handleInteraction = async () => {
      const startTime = performance.now();
      
      await simulateAsyncDelay(5); // Simulate some processing
      
      const latency = performance.now() - startTime;
      setInteractions(prev => [...prev, { latency, timestamp: Date.now() }]);
    };
    
    return renderInteractiveComponent(interactions, handleInteraction);
  };
};

export const createHeavyComputationComponent = () => {
  return () => {
    const [isComputing, setIsComputing] = React.useState(false);
    const [responsiveness, setResponsiveness] = React.useState<number[]>([]);
    
    const startHeavyComputation = () => {
      setIsComputing(true);
      
      React.startTransition(() => {
        // Simulate heavy computation in chunks
        const computeChunk = (remaining: number) => {
          if (remaining <= 0) {
            setIsComputing(false);
            return;
          }
          
          const startTime = performance.now();
          
          // Simulate computation
          for (let i = 0; i < 10000; i++) {
            Math.random();
          }
          
          setResponsiveness(prev => [...prev, performance.now() - startTime]);
          setTimeout(() => computeChunk(remaining - 1), 1);
        };
        
        computeChunk(10);
      });
    };
    
    return renderHeavyComputationComponent(isComputing, responsiveness, startHeavyComputation);
  };
};

export const createDebounceComponent = () => {
  return () => {
    const [inputValue, setInputValue] = React.useState('');
    const [debouncedValue, setDebouncedValue] = React.useState('');
    const [updateCount, setUpdateCount] = React.useState(0);
    
    const debouncedUpdate = React.useMemo(
      () => debounce((value: string) => {
        setDebouncedValue(value);
        setUpdateCount(c => c + 1);
      }, 300),
      []
    );
    
    React.useEffect(() => {
      debouncedUpdate(inputValue);
    }, [inputValue, debouncedUpdate]);
    
    return renderDebounceComponent(inputValue, setInputValue, debouncedValue, updateCount);
  };
};

export const createMemoryMonitorComponent = () => {
  return () => {
    const [memoryData, setMemoryData] = React.useState<any[]>([]);
    const [memoryUsage, setMemoryUsage] = React.useState(0);
    
    const allocateMemory = () => {
      const newData = Array.from({ length: 10000 }, (_, i) => ({
        id: i,
        data: new Array(100).fill(Math.random())
      }));
      
      setMemoryData(prev => [...prev, ...newData]);
      setMemoryUsage(memoryData.length * 0.001); // Rough estimate
    };
    
    const clearMemory = () => {
      setMemoryData([]);
      setMemoryUsage(0);
    };
    
    return renderMemoryMonitorComponent(memoryData, memoryUsage, allocateMemory, clearMemory);
  };
};

export const createBundleOptimizationComponent = () => {
  return () => {
    const [lazyComponents, setLazyComponents] = React.useState<string[]>([]);
    const [loadTimes, setLoadTimes] = React.useState<number[]>([]);
    
    const loadLazyComponent = async (componentName: string) => {
      const startTime = performance.now();
      
      // Simulate dynamic import
      await simulateAsyncDelay(50);
      
      const loadTime = performance.now() - startTime;
      setLazyComponents(prev => [...prev, componentName]);
      setLoadTimes(prev => [...prev, loadTime]);
    };
    
    return renderBundleOptimizationComponent(lazyComponents, loadTimes, loadLazyComponent);
  };
};

export const createDOMManagementComponent = () => {
  return () => {
    const [domNodes, setDomNodes] = React.useState(100);
    const [domPerformance, setDomPerformance] = React.useState<number[]>([]);
    
    const updateDOMNodes = (change: number) => {
      const startTime = performance.now();
      
      setDomNodes(prev => Math.max(0, prev + change));
      
      const updateTime = performance.now() - startTime;
      setDomPerformance(prev => [...prev, updateTime]);
    };
    
    return renderDOMManagementComponent(domNodes, domPerformance, updateDOMNodes);
  };
};

export const createConcurrentUpdateComponent = () => {
  return () => {
    const [updates, setUpdates] = React.useState<Array<{ id: number; value: number; priority: string }>>([]);
    
    const triggerConcurrentUpdates = () => {
      // Simulate concurrent updates with different priorities
      React.startTransition(() => {
        setUpdates(prev => [...prev, { id: Date.now(), value: Math.random(), priority: 'low' }]);
      });
      
      setUpdates(prev => [...prev, { id: Date.now() + 1, value: Math.random(), priority: 'high' }]);
      
      React.startTransition(() => {
        setUpdates(prev => [...prev, { id: Date.now() + 2, value: Math.random(), priority: 'low' }]);
      });
    };
    
    return renderConcurrentUpdateComponent(updates, triggerConcurrentUpdates);
  };
};

export const createPriorityUpdateComponent = () => {
  return () => {
    const [criticalData, setCriticalData] = React.useState('');
    const [normalData, setNormalData] = React.useState('');
    const [updateLatencies, setUpdateLatencies] = React.useState<Array<{ type: string; latency: number }>>([]);
    
    const triggerPriorityUpdate = (type: 'critical' | 'normal') => {
      const startTime = performance.now();
      
      if (type === 'critical') {
        setCriticalData(`Critical update at ${Date.now()}`);
      } else {
        React.startTransition(() => {
          setNormalData(`Normal update at ${Date.now()}`);
        });
      }
      
      React.startTransition(() => {
        setUpdateLatencies(prev => [...prev, { type, latency: performance.now() - startTime }]);
      });
    };
    
    return renderPriorityUpdateComponent(criticalData, normalData, updateLatencies, triggerPriorityUpdate);
  };
};

// UI rendering functions (≤8 lines each)
const renderLargeList = (items: any[], metrics: any) => (
  <div data-testid="large-list">
    <div data-testid="render-count">Renders: {metrics.renderCount}</div>
    <div data-testid="last-render-time">Last render: {metrics.lastRenderTime.toFixed(2)}ms</div>
    <div data-testid="item-count">{items.length} items</div>
    {items.slice(0, 100).map(item => <div key={item.id}>{item.value}</div>)}
  </div>
);

const renderRapidRerenderComponent = (counter: number, renderTimes: number[], triggerRerender: any) => (
  <div>
    <div data-testid="counter">{counter}</div>
    <div data-testid="average-render-time">
      {renderTimes.length > 0 ? (renderTimes.reduce((a, b) => a + b, 0) / renderTimes.length).toFixed(2) : 0}ms
    </div>
    <button onClick={triggerRerender}>Trigger Rerender</button>
  </div>
);

const renderVirtualScrollComponent = (visibleItems: number, scrollPerformance: number[], handleVirtualScroll: any) => (
  <div>
    <div data-testid="visible-items">{visibleItems} visible</div>
    <div data-testid="scroll-performance">
      Avg scroll time: {scrollPerformance.length > 0 ? 
        (scrollPerformance.reduce((a, b) => a + b, 0) / scrollPerformance.length).toFixed(2) : 0}ms
    </div>
    <button onClick={() => handleVirtualScroll('down')}>Scroll Down</button>
    <button onClick={() => handleVirtualScroll('up')}>Scroll Up</button>
  </div>
);

const renderInteractiveComponent = (interactions: any[], handleInteraction: any) => (
  <div>
    <div data-testid="interaction-count">{interactions.length} interactions</div>
    <div data-testid="average-latency">
      {interactions.length > 0 ? 
        (interactions.reduce((sum, i) => sum + i.latency, 0) / interactions.length).toFixed(2) : 0}ms
    </div>
    <button onClick={handleInteraction}>Interact</button>
  </div>
);

const renderHeavyComputationComponent = (isComputing: boolean, responsiveness: number[], startComputation: any) => (
  <div>
    <div data-testid="computation-status">{isComputing ? 'computing' : 'idle'}</div>
    <div data-testid="responsiveness-score">
      {responsiveness.length > 0 ? 
        (responsiveness.reduce((a, b) => a + b, 0) / responsiveness.length).toFixed(2) : 0}ms
    </div>
    <button onClick={startComputation} disabled={isComputing}>Start Computation</button>
  </div>
);

const renderDebounceComponent = (inputValue: string, setInputValue: any, debouncedValue: string, updateCount: number) => (
  <div>
    <input 
      data-testid="debounce-input"
      value={inputValue}
      onChange={(e) => setInputValue(e.target.value)}
      placeholder="Type to test debouncing"
    />
    <div data-testid="debounced-value">{debouncedValue}</div>
    <div data-testid="update-count">{updateCount} updates</div>
  </div>
);

const renderMemoryMonitorComponent = (memoryData: any[], memoryUsage: number, allocateMemory: any, clearMemory: any) => (
  <div>
    <div data-testid="memory-usage">{memoryUsage.toFixed(2)}MB</div>
    <div data-testid="data-count">{memoryData.length} objects</div>
    <button onClick={allocateMemory}>Allocate Memory</button>
    <button onClick={clearMemory}>Clear Memory</button>
  </div>
);

const renderBundleOptimizationComponent = (lazyComponents: string[], loadTimes: number[], loadLazyComponent: any) => (
  <div>
    <div data-testid="loaded-components">{lazyComponents.length} loaded</div>
    <div data-testid="average-load-time">
      {loadTimes.length > 0 ? (loadTimes.reduce((a, b) => a + b, 0) / loadTimes.length).toFixed(2) : 0}ms
    </div>
    <button onClick={() => loadLazyComponent('LazyComponent1')}>Load Component 1</button>
    <button onClick={() => loadLazyComponent('LazyComponent2')}>Load Component 2</button>
  </div>
);

const renderDOMManagementComponent = (domNodes: number, domPerformance: number[], updateDOMNodes: any) => (
  <div>
    <div data-testid="dom-node-count">{domNodes} nodes</div>
    <div data-testid="dom-update-performance">
      {domPerformance.length > 0 ? (domPerformance.slice(-1)[0]).toFixed(2) : 0}ms
    </div>
    <button onClick={() => updateDOMNodes(50)}>Add Nodes</button>
    <button onClick={() => updateDOMNodes(-50)}>Remove Nodes</button>
  </div>
);

const renderConcurrentUpdateComponent = (updates: any[], triggerConcurrentUpdates: any) => (
  <div>
    <div data-testid="update-count">{updates.length} updates</div>
    <div data-testid="high-priority-updates">
      {updates.filter(u => u.priority === 'high').length} high priority
    </div>
    <button onClick={triggerConcurrentUpdates}>Trigger Concurrent Updates</button>
  </div>
);

const renderPriorityUpdateComponent = (
  criticalData: string, normalData: string, updateLatencies: any[], triggerPriorityUpdate: any
) => (
  <div>
    <div data-testid="critical-data">{criticalData}</div>
    <div data-testid="normal-data">{normalData}</div>
    <div data-testid="critical-latency">
      Critical avg: {updateLatencies.filter(u => u.type === 'critical').length > 0 ?
        (updateLatencies.filter(u => u.type === 'critical').reduce((sum, u) => sum + u.latency, 0) / 
         updateLatencies.filter(u => u.type === 'critical').length).toFixed(2) : 0}ms
    </div>
    <button onClick={() => triggerPriorityUpdate('critical')}>Critical Update</button>
    <button onClick={() => triggerPriorityUpdate('normal')}>Normal Update</button>
  </div>
);

// Test verification functions (≤8 lines each)
export const verifyRenderPerformance = async (getByTestId: any, renderTime: number): Promise<void> => {
  expect(renderTime).toBeLessThan(PERFORMANCE_THRESHOLDS.MAX_RENDER_TIME_MS);
  expect(getByTestId('item-count')).toHaveTextContent('1000 items');
  
  await waitFor(() => {
    expect(getByTestId('render-count')).toHaveTextContent('Renders: 1');
  });
};

export const testRapidRerendering = async (getByText: any, getByTestId: any): Promise<void> => {
  // Trigger multiple rapid rerenders
  await act(async () => {
    for (let i = 0; i < 10; i++) {
      fireEvent.click(getByText('Trigger Rerender'));
    }
  });
  
  await waitFor(() => {
    expect(getByTestId('counter')).toHaveTextContent('10');
  });
  
  const avgRenderTime = parseFloat(getByTestId('average-render-time').textContent?.split('ms')[0] || '0');
  expect(avgRenderTime).toBeLessThan(PERFORMANCE_THRESHOLDS.MAX_RENDER_TIME_MS);
};

export const testVirtualScrolling = async (getByTestId: any): Promise<void> => {
  const scrollUpButton = getByTestId('scroll-performance').closest('div')?.querySelector('button:last-child');
  const scrollDownButton = getByTestId('scroll-performance').closest('div')?.querySelector('button:first-child');
  
  if (scrollDownButton) fireEvent.click(scrollDownButton);
  if (scrollDownButton) fireEvent.click(scrollDownButton);
  
  await waitFor(() => {
    expect(getByTestId('visible-items')).toHaveTextContent('60 visible');
  });
};

export const testInteractionLatency = async (getByText: any, getByTestId: any): Promise<void> => {
  fireEvent.click(getByText('Interact'));
  fireEvent.click(getByText('Interact'));
  fireEvent.click(getByText('Interact'));
  
  await waitFor(() => {
    expect(getByTestId('interaction-count')).toHaveTextContent('3 interactions');
  });
  
  const avgLatency = parseFloat(getByTestId('average-latency').textContent?.split('ms')[0] || '0');
  expect(avgLatency).toBeLessThan(PERFORMANCE_THRESHOLDS.MAX_INTERACTION_TIME_MS);
};

export const testComputationResponsiveness = async (getByText: any, getByTestId: any): Promise<void> => {
  fireEvent.click(getByText('Start Computation'));
  
  await waitFor(() => {
    expect(getByTestId('computation-status')).toHaveTextContent('computing');
  });
  
  await waitFor(() => {
    expect(getByTestId('computation-status')).toHaveTextContent('idle');
  }, { timeout: TEST_TIMEOUTS.LONG });
};

export const testInteractionDebouncing = async (getByTestId: any): Promise<void> => {
  const input = getByTestId('debounce-input');
  
  // Rapid typing
  fireEvent.change(input, { target: { value: 'a' } });
  fireEvent.change(input, { target: { value: 'ab' } });
  fireEvent.change(input, { target: { value: 'abc' } });
  
  await waitFor(() => {
    expect(getByTestId('debounced-value')).toHaveTextContent('abc');
    expect(getByTestId('update-count')).toHaveTextContent('1 updates');
  }, { timeout: 500 });
};

export const testMemoryUtilization = async (getByText: any, getByTestId: any): Promise<void> => {
  fireEvent.click(getByText('Allocate Memory'));
  fireEvent.click(getByText('Allocate Memory'));
  
  await waitFor(() => {
    const memoryUsage = parseFloat(getByTestId('memory-usage').textContent?.split('MB')[0] || '0');
    expect(memoryUsage).toBeGreaterThan(0);
    expect(memoryUsage).toBeLessThan(PERFORMANCE_THRESHOLDS.MEMORY_LEAK_THRESHOLD_MB);
  });
  
  fireEvent.click(getByText('Clear Memory'));
  
  await waitFor(() => {
    expect(getByTestId('memory-usage')).toHaveTextContent('0.00MB');
  });
};

export const testBundleOptimization = async (getByTestId: any): Promise<void> => {
  const loadButton1 = getByTestId('loaded-components').closest('div')?.querySelector('button:first-of-type');
  const loadButton2 = getByTestId('loaded-components').closest('div')?.querySelector('button:last-of-type');
  
  if (loadButton1) fireEvent.click(loadButton1);
  if (loadButton2) fireEvent.click(loadButton2);
  
  await waitFor(() => {
    expect(getByTestId('loaded-components')).toHaveTextContent('2 loaded');
  });
};

export const testDOMNodeManagement = async (getByText: any, getByTestId: any): Promise<void> => {
  fireEvent.click(getByText('Add Nodes'));
  
  await waitFor(() => {
    expect(getByTestId('dom-node-count')).toHaveTextContent('150 nodes');
  });
  
  fireEvent.click(getByText('Remove Nodes'));
  
  await waitFor(() => {
    expect(getByTestId('dom-node-count')).toHaveTextContent('100 nodes');
  });
};

export const testConcurrentUpdates = async (getByText: any, getByTestId: any): Promise<void> => {
  await act(async () => {
    fireEvent.click(getByText('Trigger Concurrent Updates'));
  });
  
  await waitFor(() => {
    expect(getByTestId('update-count')).toHaveTextContent('3 updates');
    expect(getByTestId('high-priority-updates')).toHaveTextContent('1 high priority');
  });
};

export const testUpdatePrioritization = async (getByText: any, getByTestId: any): Promise<void> => {
  await act(async () => {
    fireEvent.click(getByText('Critical Update'));
    fireEvent.click(getByText('Normal Update'));
  });
  
  await waitFor(() => {
    expect(getByTestId('critical-data')).not.toHaveTextContent('');
    expect(getByTestId('normal-data')).not.toHaveTextContent('');
  });
  
  const criticalLatency = parseFloat(getByTestId('critical-latency').textContent?.split('ms')[0]?.split(': ')[1] || '0');
  expect(criticalLatency).toBeLessThan(PERFORMANCE_THRESHOLDS.MAX_INTERACTION_TIME_MS);
};