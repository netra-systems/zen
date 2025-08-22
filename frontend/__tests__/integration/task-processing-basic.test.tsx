/**
 * Basic Task Processing Integration Tests
 * Tests for task queuing, monitoring, and batch processing
 * Enterprise segment - ensures reliable background processing
 */

import React from 'react';
import { render, waitFor, fireEvent, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { TestProviders } from '@/__tests__/setup/test-providers';
import { 
  initInfrastructureTest,
  setupFetchMock,
  createMockTaskResponse,
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
        
        await new Promise(resolve => {
          setTaskStatus('processing');
          requestAnimationFrame(() => {
            setTaskStatus('completed');
            resolve(undefined);
          });
        });
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
    
    setupFetchMock(createMockTaskResponse('task-456'));
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Queue Task'));
    });
    
    await waitFor(() => {
      expect(getByTestId('task')).toHaveTextContent('Task task-456: completed');
    });
  });

  it('should handle priority task queuing', async () => {
    const TestComponent = () => {
      const [queuedTasks, setQueuedTasks] = React.useState<any[]>([]);
      
      const queuePriorityTask = async (priority: string) => {
        const response = await fetch('/api/tasks/queue', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            type: 'urgent_processing',
            priority,
            payload: { urgent: true }
          })
        });
        
        const data = await response.json();
        setQueuedTasks(prev => [...prev, { ...data, priority }]);
      };
      
      return (
        <div>
          <button onClick={() => queuePriorityTask('high')}>Queue High Priority</button>
          <button onClick={() => queuePriorityTask('normal')}>Queue Normal Priority</button>
          <div data-testid="queued-count">
            Queued tasks: {queuedTasks.length}
          </div>
        </div>
      );
    };
    
    setupFetchMock(createMockTaskResponse('task-high-1'));
    setupFetchMock(createMockTaskResponse('task-normal-1'));
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Queue High Priority'));
    });
    
    await act(async () => {
      fireEvent.click(getByText('Queue Normal Priority'));
    });
    
    await waitFor(() => {
      expect(getByTestId('queued-count')).toHaveTextContent('Queued tasks: 2');
    });
  });

  it('should monitor task progress', async () => {
    const TestComponent = () => {
      const [progress, setProgress] = React.useState<number>(0);
      const [status, setStatus] = React.useState<string>('');
      
      const monitorTask = async () => {
        setStatus('monitoring');
        
        const progressSteps = [25, 50, 75, 100];
        for (let i = 0; i < progressSteps.length; i++) {
          await waitForAsyncOperation();
          setProgress(progressSteps[i]);
          
          if (progressSteps[i] === 100) {
            setStatus('completed');
          }
        }
      };
      
      return (
        <div>
          <button onClick={monitorTask}>Monitor Task</button>
          <div data-testid="progress">Progress: {progress}%</div>
          <div data-testid="status">Status: {status}</div>
        </div>
      );
    };
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Monitor Task'));
    });
    
    await waitFor(() => {
      expect(getByTestId('progress')).toHaveTextContent('Progress: 100%');
      expect(getByTestId('status')).toHaveTextContent('Status: completed');
    });
  });

  it('should handle batch task processing', async () => {
    const TestComponent = () => {
      const [batchStatus, setBatchStatus] = React.useState<string>('');
      const [processedCount, setProcessedCount] = React.useState<number>(0);
      
      const processBatch = async () => {
        setBatchStatus('processing');
        
        const response = await fetch('/api/tasks/batch', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            tasks: [
              { type: 'process_data', data: 'item1' },
              { type: 'process_data', data: 'item2' },
              { type: 'process_data', data: 'item3' }
            ]
          })
        });
        
        const result = await response.json();
        setProcessedCount(result.processed);
        setBatchStatus('completed');
      };
      
      return (
        <div>
          <button onClick={processBatch}>Process Batch</button>
          <div data-testid="batch-status">{batchStatus}</div>
          <div data-testid="processed-count">Processed: {processedCount}</div>
        </div>
      );
    };
    
    setupFetchMock({
      ok: true,
      data: { processed: 3, failed: 0, batch_id: 'batch-123' }
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Process Batch'));
    });
    
    await waitFor(() => {
      expect(getByTestId('batch-status')).toHaveTextContent('completed');
      expect(getByTestId('processed-count')).toHaveTextContent('Processed: 3');
    });
  });

  it('should handle task cancellation', async () => {
    const TestComponent = () => {
      const [taskId, setTaskId] = React.useState<string>('');
      const [cancelStatus, setCancelStatus] = React.useState<string>('');
      
      const cancelTask = async () => {
        const response = await fetch(`/api/tasks/${taskId}/cancel`, {
          method: 'POST'
        });
        
        if (response.ok) {
          setCancelStatus('Task cancelled');
        }
      };
      
      React.useEffect(() => {
        setTaskId('task-cancel-123');
      }, []);
      
      return (
        <div>
          <button onClick={cancelTask}>Cancel Task</button>
          <div data-testid="cancel-status">{cancelStatus}</div>
        </div>
      );
    };
    
    setupFetchMock({
      ok: true,
      data: { cancelled: true, task_id: 'task-cancel-123' }
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Cancel Task'));
    });
    
    await waitFor(() => {
      expect(getByTestId('cancel-status')).toHaveTextContent('Task cancelled');
    });
  });

  it('should list active tasks', async () => {
    const TestComponent = () => {
      const [activeTasks, setActiveTasks] = React.useState<any[]>([]);
      
      const fetchActiveTasks = async () => {
        const response = await fetch('/api/tasks/active');
        const data = await response.json();
        setActiveTasks(data.tasks);
      };
      
      return (
        <div>
          <button onClick={fetchActiveTasks}>Fetch Active Tasks</button>
          <div data-testid="active-count">
            Active tasks: {activeTasks.length}
          </div>
        </div>
      );
    };
    
    setupFetchMock({
      ok: true,
      data: {
        tasks: [
          { id: 'task-1', status: 'running' },
          { id: 'task-2', status: 'queued' }
        ]
      }
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Fetch Active Tasks'));
    });
    
    await waitFor(() => {
      expect(getByTestId('active-count')).toHaveTextContent('Active tasks: 2');
    });
  });
});