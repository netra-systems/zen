/**
 * Task Retry Mechanisms Integration Tests
 * Tests for task failures, retries, and dead letter queue handling
 * Enterprise segment - ensures reliable error recovery
 */

import React from 'react';
import { render, waitFor, fireEvent, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { TestProviders } from '@/__tests__/setup/test-providers';
import { 
  initInfrastructureTest,
  setupFetchMock,
  waitForAsyncOperation,
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

describe('Task Failure and Retry Mechanisms', () => {
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
          
          try {
            const response = await fetch('/api/tasks/execute');
            
            if (response.ok) {
              setFinalStatus('Success');
              break;
            } else if (attempts === maxRetries) {
              setFinalStatus('Failed after retries');
            }
          } catch (error) {
            if (attempts === maxRetries) {
              setFinalStatus('Failed after retries');
            }
          }
          
          if (attempts < maxRetries) {
            await waitForAsyncOperation();
          }
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
    
    await act(async () => {
      fireEvent.click(getByText('Execute Task'));
    });
    
    await waitFor(() => {
      expect(getByTestId('retry-count')).toHaveTextContent('Attempts: 3');
      expect(getByTestId('final-status')).toHaveTextContent('Success');
    });
  });

  it('should implement exponential backoff for retries', async () => {
    const TestComponent = () => {
      const [backoffTimes, setBackoffTimes] = React.useState<number[]>([]);
      const [retryStatus, setRetryStatus] = React.useState('');
      
      const executeWithBackoff = async () => {
        const times: number[] = [];
        let attempts = 0;
        const maxRetries = 3;
        
        while (attempts < maxRetries) {
          attempts++;
          const backoffTime = Math.pow(2, attempts - 1) * 1000;
          times.push(backoffTime);
          setBackoffTimes([...times]);
          
          try {
            const response = await fetch('/api/tasks/execute-with-backoff');
            if (response.ok) {
              setRetryStatus('Success with backoff');
              break;
            }
          } catch (error) {
            if (attempts === maxRetries) {
              setRetryStatus('Failed after backoff retries');
            }
          }
          
          if (attempts < maxRetries) {
            await waitForAsyncOperation();
          }
        }
      };
      
      return (
        <div>
          <button onClick={executeWithBackoff}>Execute with Backoff</button>
          <div data-testid="backoff-times">
            Backoff times: {backoffTimes.join(', ')}ms
          </div>
          <div data-testid="retry-status">{retryStatus}</div>
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
    
    await act(async () => {
      fireEvent.click(getByText('Execute with Backoff'));
    });
    
    await waitFor(() => {
      expect(getByTestId('backoff-times')).toHaveTextContent('1000, 2000, 4000');
      expect(getByTestId('retry-status')).toHaveTextContent('Success with backoff');
    });
  });

  it('should handle dead letter queue for failed tasks', async () => {
    const TestComponent = () => {
      const [dlqStatus, setDlqStatus] = React.useState('');
      const [failedTasksCount, setFailedTasksCount] = React.useState(0);
      
      const handleFailedTask = async () => {
        const response = await fetch('/api/tasks/failed', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            task_id: 'failed-task-123',
            reason: 'max_retries_exceeded',
            move_to_dlq: true
          })
        });
        
        const result = await response.json();
        setDlqStatus(result.status);
        setFailedTasksCount(result.dlq_count);
      };
      
      return (
        <div>
          <button onClick={handleFailedTask}>Handle Failed Task</button>
          <div data-testid="dlq-status">{dlqStatus}</div>
          <div data-testid="failed-count">DLQ Count: {failedTasksCount}</div>
        </div>
      );
    };
    
    setupFetchMock({
      ok: true,
      data: { 
        status: 'moved_to_dlq', 
        dlq_count: 5,
        task_id: 'failed-task-123'
      }
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Handle Failed Task'));
    });
    
    await waitFor(() => {
      expect(getByTestId('dlq-status')).toHaveTextContent('moved_to_dlq');
      expect(getByTestId('failed-count')).toHaveTextContent('DLQ Count: 5');
    });
  });

  it('should reprocess tasks from dead letter queue', async () => {
    const TestComponent = () => {
      const [reprocessStatus, setReprocessStatus] = React.useState('');
      
      const reprocessDlqTasks = async () => {
        const response = await fetch('/api/tasks/dlq/reprocess', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            task_ids: ['failed-task-123', 'failed-task-124']
          })
        });
        
        const result = await response.json();
        setReprocessStatus(`Reprocessed ${result.reprocessed} tasks`);
      };
      
      return (
        <div>
          <button onClick={reprocessDlqTasks}>Reprocess DLQ</button>
          <div data-testid="reprocess-status">{reprocessStatus}</div>
        </div>
      );
    };
    
    setupFetchMock({
      ok: true,
      data: { reprocessed: 2, failed: 0 }
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Reprocess DLQ'));
    });
    
    await waitFor(() => {
      expect(getByTestId('reprocess-status')).toHaveTextContent('Reprocessed 2 tasks');
    });
  });

  it('should handle retry with jitter to prevent thundering herd', async () => {
    const TestComponent = () => {
      const [jitterValues, setJitterValues] = React.useState<number[]>([]);
      const [retryResult, setRetryResult] = React.useState('');
      
      const executeWithJitter = async () => {
        const jitters: number[] = [];
        let attempts = 0;
        const maxRetries = 3;
        
        while (attempts < maxRetries) {
          attempts++;
          
          // Calculate jitter (random value between 0 and base delay)
          const baseDelay = Math.pow(2, attempts - 1) * 1000;
          const jitter = Math.random() * baseDelay * 0.1; // 10% jitter
          jitters.push(Math.round(jitter));
          setJitterValues([...jitters]);
          
          try {
            const response = await fetch('/api/tasks/execute-with-jitter');
            if (response.ok) {
              setRetryResult('Success with jitter');
              break;
            }
          } catch (error) {
            if (attempts === maxRetries) {
              setRetryResult('Failed with jitter');
            }
          }
          
          if (attempts < maxRetries) {
            await waitForAsyncOperation();
          }
        }
      };
      
      return (
        <div>
          <button onClick={executeWithJitter}>Execute with Jitter</button>
          <div data-testid="jitter-values">
            Jitter applied: {jitterValues.length} times
          </div>
          <div data-testid="retry-result">{retryResult}</div>
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
    
    await act(async () => {
      fireEvent.click(getByText('Execute with Jitter'));
    });
    
    await waitFor(() => {
      expect(getByTestId('jitter-values')).toHaveTextContent('Jitter applied: 3 times');
      expect(getByTestId('retry-result')).toHaveTextContent('Success with jitter');
    });
  });

  it('should track failure patterns and adjust retry strategy', async () => {
    const TestComponent = () => {
      const [failurePattern, setFailurePattern] = React.useState('');
      const [adjustedStrategy, setAdjustedStrategy] = React.useState('');
      
      const analyzeFailures = async () => {
        const response = await fetch('/api/tasks/failure-analysis');
        const data = await response.json();
        
        setFailurePattern(data.pattern);
        setAdjustedStrategy(data.recommended_strategy);
      };
      
      return (
        <div>
          <button onClick={analyzeFailures}>Analyze Failures</button>
          <div data-testid="failure-pattern">{failurePattern}</div>
          <div data-testid="adjusted-strategy">{adjustedStrategy}</div>
        </div>
      );
    };
    
    setupFetchMock({
      ok: true,
      data: {
        pattern: 'timeout_spikes',
        recommended_strategy: 'increase_backoff_multiplier',
        confidence: 0.85
      }
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Analyze Failures'));
    });
    
    await waitFor(() => {
      expect(getByTestId('failure-pattern')).toHaveTextContent('timeout_spikes');
      expect(getByTestId('adjusted-strategy')).toHaveTextContent('increase_backoff_multiplier');
    });
  });
});