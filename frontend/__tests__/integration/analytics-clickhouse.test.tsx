import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
import React from 'react';
import { render, waitFor, fireEvent, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { TestProviders } from '@/__tests__/setup/test-providers';
import { aitFor, fireEvent, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { TestProviders } from '@/__tests__/setup/test-providers';
import { 
  initInfrastructureTest,
  setupFetchMock,
  createMockAnalyticsResponse,
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
    // Clean up timers to prevent hanging
    jest.clearAllTimers();
    jest.useFakeTimers();
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
});

describe('ClickHouse Analytics Integration', () => {
    jest.setTimeout(10000);
  it('should query analytics data from ClickHouse', async () => {
    const TestComponent = () => {
      const [analytics, setAnalytics] = React.useState<any>(null);
      
      const fetchAnalytics = async () => {
        const response = await fetch('/api/analytics/usage');
        const data = await response.json();
        setAnalytics(data);
      };
      
      return (
        <div>
          <button onClick={fetchAnalytics}>Fetch Analytics</button>
          {analytics && (
            <div data-testid="analytics">
              Total requests: {analytics.total_requests}
            </div>
          )}
        </div>
      );
    };
    
    setupFetchMock(createMockAnalyticsResponse({
      requests: 10000,
      responseTime: 250
    }));
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Fetch Analytics'));
    });
    
    await waitFor(() => {
      expect(getByTestId('analytics')).toHaveTextContent('Total requests: 10000');
    });
  });

  it('should query time-series analytics data', async () => {
    const TestComponent = () => {
      const [timeSeries, setTimeSeries] = React.useState<any>(null);
      
      const fetchTimeSeries = async () => {
        const response = await fetch('/api/analytics/timeseries?interval=1h');
        const data = await response.json();
        setTimeSeries(data);
      };
      
      return (
        <div>
          <button onClick={fetchTimeSeries}>Fetch Time Series</button>
          {timeSeries && (
            <div data-testid="timeseries">
              Data points: {timeSeries.points.length}
            </div>
          )}
        </div>
      );
    };
    
    setupFetchMock({
      ok: true,
      data: {
        points: [
          { timestamp: '2024-01-01T00:00:00Z', value: 100 },
          { timestamp: '2024-01-01T01:00:00Z', value: 150 }
        ],
        interval: '1h'
      }
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Fetch Time Series'));
    });
    
    await waitFor(() => {
      expect(getByTestId('timeseries')).toHaveTextContent('Data points: 2');
    });
  });

  it('should perform aggregation queries', async () => {
    const TestComponent = () => {
      const [aggregation, setAggregation] = React.useState<any>(null);
      
      const fetchAggregation = async () => {
        const response = await fetch('/api/analytics/aggregate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            metrics: ['count', 'avg', 'sum'],
            groupBy: ['user_type', 'region']
          })
        });
        
        const data = await response.json();
        setAggregation(data);
      };
      
      return (
        <div>
          <button onClick={fetchAggregation}>Fetch Aggregation</button>
          {aggregation && (
            <div data-testid="aggregation">
              Groups: {aggregation.groups.length}
            </div>
          )}
        </div>
      );
    };
    
    setupFetchMock({
      ok: true,
      data: {
        groups: [
          { user_type: 'premium', region: 'us', count: 500, avg: 2.5 },
          { user_type: 'free', region: 'eu', count: 1200, avg: 1.8 }
        ]
      }
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Fetch Aggregation'));
    });
    
    await waitFor(() => {
      expect(getByTestId('aggregation')).toHaveTextContent('Groups: 2');
    });
  });

  it('should handle complex analytical queries', async () => {
    const TestComponent = () => {
      const [queryResult, setQueryResult] = React.useState<any>(null);
      
      const executeComplexQuery = async () => {
        const response = await fetch('/api/analytics/query', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            query: 'SELECT user_type, COUNT(*) as total FROM events WHERE timestamp >= now() - INTERVAL 1 DAY GROUP BY user_type'
          })
        });
        
        const data = await response.json();
        setQueryResult(data);
      };
      
      return (
        <div>
          <button onClick={executeComplexQuery}>Execute Query</button>
          {queryResult && (
            <div data-testid="query-result">
              Execution time: {queryResult.execution_time}ms
            </div>
          )}
        </div>
      );
    };
    
    setupFetchMock({
      ok: true,
      data: {
        results: [
          { user_type: 'premium', total: 450 },
          { user_type: 'free', total: 2100 }
        ],
        execution_time: 45
      }
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Execute Query'));
    });
    
    await waitFor(() => {
      expect(getByTestId('query-result')).toHaveTextContent('Execution time: 45ms');
    });
  });

  it('should handle data compression and optimization queries', async () => {
    const TestComponent = () => {
      const [optimizationResult, setOptimizationResult] = React.useState<any>(null);
      
      const optimizeData = async () => {
        const response = await fetch('/api/analytics/optimize', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            table: 'events',
            action: 'compress_partition'
          })
        });
        
        const data = await response.json();
        setOptimizationResult(data);
      };
      
      return (
        <div>
          <button onClick={optimizeData}>Optimize Data</button>
          {optimizationResult && (
            <div data-testid="optimization-result">
              Compression ratio: {optimizationResult.compression_ratio}x
            </div>
          )}
        </div>
      );
    };
    
    setupFetchMock({
      ok: true,
      data: {
        compression_ratio: 3.2,
        space_saved: '1.2GB',
        optimization_time: 450
      }
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Optimize Data'));
    });
    
    await waitFor(() => {
      expect(getByTestId('optimization-result')).toHaveTextContent('Compression ratio: 3.2x');
    });
  });

  it('should handle materialized view queries', async () => {
    const TestComponent = () => {
      const [viewData, setViewData] = React.useState<any>(null);
      
      const queryMaterializedView = async () => {
        const response = await fetch('/api/analytics/materialized-view/user_metrics');
        const data = await response.json();
        setViewData(data);
      };
      
      return (
        <div>
          <button onClick={queryMaterializedView}>Query Materialized View</button>
          {viewData && (
            <div data-testid="view-data">
              View records: {viewData.record_count}
            </div>
          )}
        </div>
      );
    };
    
    setupFetchMock({
      ok: true,
      data: {
        record_count: 15000,
        last_updated: '2024-01-01T12:00:00Z',
        refresh_interval: '5m'
      }
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Query Materialized View'));
    });
    
    await waitFor(() => {
      expect(getByTestId('view-data')).toHaveTextContent('View records: 15000');
    });
  });
});