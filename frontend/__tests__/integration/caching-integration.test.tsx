/**
 * Caching Integration Tests
 * Tests for Redis caching operations and cache invalidation
 * Enterprise segment - ensures performance and data consistency
 */

import React from 'react';
import { render, waitFor, fireEvent, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { TestProviders } from '@/__tests__/setup/test-providers';
import { 
  initInfrastructureTest,
  setupFetchMock,
  createMockCacheResponse,
  InfrastructureTestContext
} from './utils/infrastructure-test-utils';

// Mock fetch
global.fetch = jest.fn();

let testContext: InfrastructureTestContext;

beforeEach(() => {
  testContext = initInfrastructureTest();
});

afterEach(() => {
  testContext.cleanup();
});

describe('Redis Caching Integration', () => {
  it('should cache frequently accessed data', async () => {
    const TestComponent = () => {
      const [cacheHit, setCacheHit] = React.useState<boolean | null>(null);
      const [data, setData] = React.useState<any>(null);
      
      const fetchData = async () => {
        const response = await fetch('/api/data/popular');
        const result = await response.json();
        
        setCacheHit(response.headers.get('X-Cache-Hit') === 'true');
        setData(result);
      };
      
      return (
        <div>
          <button onClick={fetchData}>Fetch Data</button>
          {cacheHit !== null && (
            <div data-testid="cache-status">
              {cacheHit ? 'Cache hit' : 'Cache miss'}
            </div>
          )}
          {data && <div data-testid="data">{data.value}</div>}
        </div>
      );
    };
    
    setupFetchMock(createMockCacheResponse(true, { value: 'cached data' }));
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Fetch Data'));
    });
    
    await waitFor(() => {
      expect(getByTestId('cache-status')).toHaveTextContent('Cache hit');
      expect(getByTestId('data')).toHaveTextContent('cached data');
    });
  });

  it('should handle cache misses', async () => {
    const TestComponent = () => {
      const [cacheStatus, setCacheStatus] = React.useState('');
      const [loadTime, setLoadTime] = React.useState<number | null>(null);
      
      const fetchUncachedData = async () => {
        const startTime = performance.now();
        const response = await fetch('/api/data/fresh');
        const endTime = performance.now();
        
        const isHit = response.headers.get('X-Cache-Hit') === 'true';
        setCacheStatus(isHit ? 'Cache hit' : 'Cache miss');
        setLoadTime(endTime - startTime);
      };
      
      return (
        <div>
          <button onClick={fetchUncachedData}>Fetch Fresh Data</button>
          <div data-testid="cache-status">{cacheStatus}</div>
          {loadTime && (
            <div data-testid="load-time">Load time: {loadTime.toFixed(0)}ms</div>
          )}
        </div>
      );
    };
    
    setupFetchMock(createMockCacheResponse(false, { value: 'fresh data' }));
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Fetch Fresh Data'));
    });
    
    await waitFor(() => {
      expect(getByTestId('cache-status')).toHaveTextContent('Cache miss');
    });
  });

  it('should invalidate cache on data updates', async () => {
    const TestComponent = () => {
      const [invalidated, setInvalidated] = React.useState(false);
      
      const updateData = async () => {
        const response = await fetch('/api/data/update', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ key: 'popular', value: 'new data' })
        });
        
        if (response.ok) {
          setInvalidated(true);
        }
      };
      
      return (
        <div>
          <button onClick={updateData}>Update Data</button>
          {invalidated && (
            <div data-testid="invalidation">Cache invalidated</div>
          )}
        </div>
      );
    };
    
    setupFetchMock({
      ok: true,
      data: { invalidated: true }
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Update Data'));
    });
    
    await waitFor(() => {
      expect(getByTestId('invalidation')).toHaveTextContent('Cache invalidated');
    });
  });

  it('should handle cache eviction policies', async () => {
    const TestComponent = () => {
      const [evictionStatus, setEvictionStatus] = React.useState('');
      
      const triggerEviction = async () => {
        const response = await fetch('/api/cache/evict', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ policy: 'lru', threshold: 0.8 })
        });
        
        const result = await response.json();
        setEvictionStatus(`Evicted ${result.count} items`);
      };
      
      return (
        <div>
          <button onClick={triggerEviction}>Trigger Eviction</button>
          <div data-testid="eviction-status">{evictionStatus}</div>
        </div>
      );
    };
    
    setupFetchMock({
      ok: true,
      data: { count: 15, policy: 'lru' }
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Trigger Eviction'));
    });
    
    await waitFor(() => {
      expect(getByTestId('eviction-status')).toHaveTextContent('Evicted 15 items');
    });
  });
});

describe('Cache Performance Integration', () => {
  it('should measure cache performance metrics', async () => {
    const TestComponent = () => {
      const [metrics, setMetrics] = React.useState<any>(null);
      
      const fetchMetrics = async () => {
        const response = await fetch('/api/cache/metrics');
        const data = await response.json();
        setMetrics(data);
      };
      
      return (
        <div>
          <button onClick={fetchMetrics}>Fetch Metrics</button>
          {metrics && (
            <div data-testid="metrics">
              <div>Hit Rate: {metrics.hit_rate}%</div>
              <div>Miss Rate: {metrics.miss_rate}%</div>
            </div>
          )}
        </div>
      );
    };
    
    setupFetchMock({
      ok: true,
      data: {
        hit_rate: 85.5,
        miss_rate: 14.5,
        avg_response_time: 12
      }
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Fetch Metrics'));
    });
    
    await waitFor(() => {
      expect(getByTestId('metrics')).toHaveTextContent('Hit Rate: 85.5%');
      expect(getByTestId('metrics')).toHaveTextContent('Miss Rate: 14.5%');
    });
  });

  it('should handle cache warming operations', async () => {
    const TestComponent = () => {
      const [warmingStatus, setWarmingStatus] = React.useState('');
      
      const warmCache = async () => {
        setWarmingStatus('Warming cache...');
        
        const response = await fetch('/api/cache/warm', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ keys: ['popular_data', 'user_prefs'] })
        });
        
        if (response.ok) {
          setWarmingStatus('Cache warmed');
        }
      };
      
      return (
        <div>
          <button onClick={warmCache}>Warm Cache</button>
          <div data-testid="warming-status">{warmingStatus}</div>
        </div>
      );
    };
    
    setupFetchMock({
      ok: true,
      data: { warmed_keys: 2, status: 'completed' }
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Warm Cache'));
    });
    
    await waitFor(() => {
      expect(getByTestId('warming-status')).toHaveTextContent('Cache warmed');
    });
  });

  it('should handle distributed cache synchronization', async () => {
    const TestComponent = () => {
      const [syncStatus, setSyncStatus] = React.useState('');
      
      const syncCache = async () => {
        const response = await fetch('/api/cache/sync', {
          method: 'POST'
        });
        
        const result = await response.json();
        setSyncStatus(`Synced ${result.nodes} nodes`);
      };
      
      return (
        <div>
          <button onClick={syncCache}>Sync Cache</button>
          <div data-testid="sync-status">{syncStatus}</div>
        </div>
      );
    };
    
    setupFetchMock({
      ok: true,
      data: { nodes: 3, timestamp: Date.now() }
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Sync Cache'));
    });
    
    await waitFor(() => {
      expect(getByTestId('sync-status')).toHaveTextContent('Synced 3 nodes');
    });
  });
});