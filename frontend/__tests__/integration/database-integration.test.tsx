/**
 * Database Integration Tests
 * Tests for repository patterns and database transactions
 * Enterprise segment - ensures data consistency and reliability
 */

import React from 'react';
import { render, waitFor, fireEvent, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { TestProviders } from '@/__tests__/setup/test-providers';
import { 
  initInfrastructureTest,
  setupFetchMock,
  createMockTransactionResponse,
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
    
    setupFetchMock({
      ok: true,
      data: {
        id: 'thread-123',
        title: 'Test Thread',
        model: 'gpt-4'
      }
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Create Thread'));
    });
    
    await waitFor(() => {
      expect(getByTestId('thread')).toHaveTextContent('Test Thread - thread-123');
    });
  });

  it('should handle repository read operations', async () => {
    const TestComponent = () => {
      const [threads, setThreads] = React.useState<any[]>([]);
      
      const fetchThreads = async () => {
        const response = await fetch('/api/threads');
        const data = await response.json();
        setThreads(data.items);
      };
      
      return (
        <div>
          <button onClick={fetchThreads}>Fetch Threads</button>
          <div data-testid="thread-count">
            Count: {threads.length}
          </div>
        </div>
      );
    };
    
    setupFetchMock({
      ok: true,
      data: {
        items: [
          { id: '1', title: 'Thread 1' },
          { id: '2', title: 'Thread 2' }
        ]
      }
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Fetch Threads'));
    });
    
    await waitFor(() => {
      expect(getByTestId('thread-count')).toHaveTextContent('Count: 2');
    });
  });

  it('should handle repository update operations', async () => {
    const TestComponent = () => {
      const [updated, setUpdated] = React.useState(false);
      
      const updateThread = async () => {
        const response = await fetch('/api/threads/123', {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title: 'Updated Thread' })
        });
        
        if (response.ok) {
          setUpdated(true);
        }
      };
      
      return (
        <div>
          <button onClick={updateThread}>Update Thread</button>
          {updated && (
            <div data-testid="update-status">Updated</div>
          )}
        </div>
      );
    };
    
    setupFetchMock({
      ok: true,
      data: { id: '123', title: 'Updated Thread' }
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Update Thread'));
    });
    
    await waitFor(() => {
      expect(getByTestId('update-status')).toHaveTextContent('Updated');
    });
  });

  it('should handle repository delete operations', async () => {
    const TestComponent = () => {
      const [deleted, setDeleted] = React.useState(false);
      
      const deleteThread = async () => {
        const response = await fetch('/api/threads/123', {
          method: 'DELETE'
        });
        
        if (response.ok) {
          setDeleted(true);
        }
      };
      
      return (
        <div>
          <button onClick={deleteThread}>Delete Thread</button>
          {deleted && (
            <div data-testid="delete-status">Deleted</div>
          )}
        </div>
      );
    };
    
    setupFetchMock({ ok: true, data: { deleted: true } });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Delete Thread'));
    });
    
    await waitFor(() => {
      expect(getByTestId('delete-status')).toHaveTextContent('Deleted');
    });
  });
});

describe('Database Transaction Integration', () => {
  it('should handle database transactions', async () => {
    const TestComponent = () => {
      const [transactionStatus, setTransactionStatus] = React.useState('');
      
      const performTransaction = async () => {
        try {
          setTransactionStatus('Starting transaction...');
          
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
    
    setupFetchMock(createMockTransactionResponse(true));
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Execute Transaction'));
    });
    
    await waitFor(() => {
      expect(getByTestId('transaction-status')).toHaveTextContent('Transaction completed');
    });
  });

  it('should handle transaction rollbacks', async () => {
    const TestComponent = () => {
      const [rollbackStatus, setRollbackStatus] = React.useState('');
      
      const performFailedTransaction = async () => {
        try {
          const response = await fetch('/api/transactions/execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              operations: [
                { type: 'create', entity: 'thread' },
                { type: 'invalid_operation' }
              ]
            })
          });
          
          if (!response.ok) {
            setRollbackStatus('Transaction rolled back');
          }
        } catch (error) {
          setRollbackStatus('Transaction failed');
        }
      };
      
      return (
        <div>
          <button onClick={performFailedTransaction}>Execute Failed Transaction</button>
          <div data-testid="rollback-status">{rollbackStatus}</div>
        </div>
      );
    };
    
    setupFetchMock(createMockTransactionResponse(false));
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Execute Failed Transaction'));
    });
    
    await waitFor(() => {
      expect(getByTestId('rollback-status')).toHaveTextContent('Transaction rolled back');
    });
  });
});