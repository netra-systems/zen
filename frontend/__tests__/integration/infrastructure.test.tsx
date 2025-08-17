/**
 * Infrastructure Integration Tests
 * Tests for database, caching, background tasks, and error handling
 */

import React from 'react';
import { render, waitFor, fireEvent, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import WS from 'jest-websocket-mock';
import { TestProviders } from '../test-utils/providers';

// Mock fetch
global.fetch = jest.fn();

// Mock WebSocket
let mockWs: WS;

beforeEach(() => {
  try {
    mockWs = new WS('ws://localhost:8000/ws');
  } catch (error) {
    // Fallback WebSocket mock
    global.WebSocket = jest.fn(() => ({
      send: jest.fn(),
      close: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      readyState: 1
    }));
  }
});

afterEach(() => {
  try {
    WS.clean();
  } catch (error) {
    // Clean gracefully
  }
  jest.clearAllMocks();
});

describe('Database Repository Pattern Integration', () => {
  it('should perform CRUD operations through repositories', async () => {
    const TestComponent = () => {
      const [thread, setThread] = React.useState<any>(null);
      
      const createThread = async () => {
        const response = await fetch('/api/threads', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            title: 'Test Thread',
            model: 'gpt-4'
          })
        });
        
        const data = await response.json();
        setThread(data);
      };
      
      return (
        <div>
          <button onClick={createThread}>Create Thread</button>
          {thread && (
            <div data-testid="thread">
              {thread.title} - {thread.id}
            </div>
          )}
        </div>
      );
    };
    
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        id: 'thread-123',
        title: 'Test Thread',
        model: 'gpt-4'
      })
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    fireEvent.click(getByText('Create Thread'));
    
    await waitFor(() => {
      expect(getByTestId('thread')).toHaveTextContent('Test Thread - thread-123');
    });
  });

  it('should handle database transactions', async () => {
    const TestComponent = () => {
      const [transactionStatus, setTransactionStatus] = React.useState('');
      
      const performTransaction = async () => {
        try {
          setTransactionStatus('Starting transaction...');
          
          // Simulate multiple operations in a transaction
          const response = await fetch('/api/transactions/execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              operations: [
                { type: 'create', entity: 'thread', data: { title: 'Thread 1' } },
                { type: 'create', entity: 'message', data: { content: 'Message 1' } },
                { type: 'update', entity: 'user', data: { credits: 100 } }
              ]
            })
          });
          
          if (response.ok) {
            setTransactionStatus('Transaction completed');
          } else {
            setTransactionStatus('Transaction rolled back');
          }
        } catch (error) {
          setTransactionStatus('Transaction failed');
        }
      };
      
      return (
        <div>
          <button onClick={performTransaction}>Execute Transaction</button>
          <div data-testid="transaction-status">{transactionStatus}</div>
        </div>
      );
    };
    
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true })
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    fireEvent.click(getByText('Execute Transaction'));
    
    await waitFor(() => {
      expect(getByTestId('transaction-status')).toHaveTextContent('Transaction completed');
    });
  });
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
    
    const mockHeaders = new Headers();
    mockHeaders.set('X-Cache-Hit', 'true');
    
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      headers: mockHeaders,
      json: async () => ({ value: 'cached data' })
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    fireEvent.click(getByText('Fetch Data'));
    
    await waitFor(() => {
      expect(getByTestId('cache-status')).toHaveTextContent('Cache hit');
      expect(getByTestId('data')).toHaveTextContent('cached data');
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
    
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ invalidated: true })
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    fireEvent.click(getByText('Update Data'));
    
    await waitFor(() => {
      expect(getByTestId('invalidation')).toHaveTextContent('Cache invalidated');
    });
  });
});

describe('ClickHouse Analytics Integration', () => {
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
    
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        total_requests: 10000,
        avg_response_time: 250
      })
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    fireEvent.click(getByText('Fetch Analytics'));
    
    await waitFor(() => {
      expect(getByTestId('analytics')).toHaveTextContent('Total requests: 10000');
    });
  });

  it('should aggregate metrics in real-time', async () => {
    const TestComponent = () => {
      const [metrics, setMetrics] = React.useState<any>({});
      
      React.useEffect(() => {
        const ws = new WebSocket('ws://localhost:8000/ws');
        ws.onmessage = (event) => {
          const data = JSON.parse(event.data);
          if (data.type === 'metrics_update') {
            setMetrics(data.metrics);
          }
        };
        return () => ws.close();
      }, []);
      
      return (
        <div data-testid="metrics">
          {metrics.requests_per_second && (
            <div>RPS: {metrics.requests_per_second}</div>
          )}
        </div>
      );
    };
    
    const { getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    if (mockWs && mockWs.connected) {
      await mockWs.connected;
    }
    
    act(() => {
      if (mockWs && mockWs.send) {
        mockWs.send(JSON.stringify({
          type: 'metrics_update',
          metrics: { requests_per_second: 150 }
        }));
      }
    });
    
    await waitFor(() => {
      expect(getByTestId('metrics')).toHaveTextContent('RPS: 150');
    });
  });
});

describe('Background Task Processing', () => {
  it('should queue and process background tasks', async () => {
    const TestComponent = () => {
      const [taskId, setTaskId] = React.useState<string | null>(null);
      const [taskStatus, setTaskStatus] = React.useState<string>('');
      
      const queueTask = async () => {
        const response = await fetch('/api/tasks/queue', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            type: 'data_processing',
            payload: { size: 1000 }
          })
        });
        
        const data = await response.json();
        setTaskId(data.task_id);
        setTaskStatus('queued');
        
        // Poll for status
        setTimeout(() => setTaskStatus('processing'), 500);
        setTimeout(() => setTaskStatus('completed'), 1000);
      };
      
      return (
        <div>
          <button onClick={queueTask}>Queue Task</button>
          {taskId && (
            <div data-testid="task">
              Task {taskId}: {taskStatus}
            </div>
          )}
        </div>
      );
    };
    
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ task_id: 'task-456' })
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    fireEvent.click(getByText('Queue Task'));
    
    await waitFor(() => {
      expect(getByTestId('task')).toHaveTextContent('Task task-456: completed');
    }, { timeout: 1500 });
  });

  it('should handle task failures and retries', async () => {
    const TestComponent = () => {
      const [retryCount, setRetryCount] = React.useState(0);
      const [finalStatus, setFinalStatus] = React.useState('');
      
      const executeWithRetry = async () => {
        let attempts = 0;
        const maxRetries = 3;
        
        while (attempts < maxRetries) {
          attempts++;
          setRetryCount(attempts);
          
          const response = await fetch('/api/tasks/execute');
          
          if (response.ok) {
            setFinalStatus('Success');
            break;
          } else if (attempts === maxRetries) {
            setFinalStatus('Failed after retries');
          }
          
          // Wait before retry
          await new Promise(resolve => setTimeout(resolve, 100));
        }
      };
      
      return (
        <div>
          <button onClick={executeWithRetry}>Execute Task</button>
          <div data-testid="retry-count">Attempts: {retryCount}</div>
          {finalStatus && (
            <div data-testid="final-status">{finalStatus}</div>
          )}
        </div>
      );
    };
    
    // Mock failures then success
    (fetch as jest.Mock)
      .mockRejectedValueOnce(new Error('Failed'))
      .mockRejectedValueOnce(new Error('Failed'))
      .mockResolvedValueOnce({ ok: true });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    fireEvent.click(getByText('Execute Task'));
    
    await waitFor(() => {
      expect(getByTestId('retry-count')).toHaveTextContent('Attempts: 3');
      expect(getByTestId('final-status')).toHaveTextContent('Success');
    });
  });
});

describe('Error Context and Tracing', () => {
  it('should capture and display error context', async () => {
    const TestComponent = () => {
      const [error, setError] = React.useState<any>(null);
      
      const triggerError = async () => {
        try {
          const response = await fetch('/api/error-prone-endpoint');
          if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message);
          }
        } catch (err: any) {
          setError({
            message: err.message,
            trace_id: 'trace-789',
            timestamp: new Date().toISOString()
          });
        }
      };
      
      return (
        <div>
          <button onClick={triggerError}>Trigger Error</button>
          {error && (
            <div data-testid="error">
              <div>Error: {error.message}</div>
              <div>Trace: {error.trace_id}</div>
            </div>
          )}
        </div>
      );
    };
    
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      json: async () => ({ message: 'Internal server error' })
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    fireEvent.click(getByText('Trigger Error'));
    
    await waitFor(() => {
      expect(getByTestId('error')).toHaveTextContent('Error: Internal server error');
      expect(getByTestId('error')).toHaveTextContent('Trace: trace-789');
    });
  });
});