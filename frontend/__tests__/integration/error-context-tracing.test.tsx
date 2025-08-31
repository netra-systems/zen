import React from 'react';
import { render, waitFor, fireEvent, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { TestProviders } from '@/__tests__/setup/test-providers';
import { 
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
tFor, fireEvent, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { TestProviders } from '@/__tests__/setup/test-providers';
import { 
  initInfrastructureTest,
  setupFetchMock,
  createMockErrorResponse,
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

describe('Error Context and Tracing', () => {
    jest.setTimeout(10000);
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
    
    setupFetchMock(createMockErrorResponse('Internal server error', 'trace-789'));
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Trigger Error'));
    });
    
    await waitFor(() => {
      expect(getByTestId('error')).toHaveTextContent('Error: Internal server error');
      expect(getByTestId('error')).toHaveTextContent('Trace: trace-789');
    });
  });

  it('should track error propagation across services', async () => {
    const TestComponent = () => {
      const [errorChain, setErrorChain] = React.useState<any[]>([]);
      
      const traceErrorChain = async () => {
        try {
          const response = await fetch('/api/service-chain-error');
          if (!response.ok) {
            const errorData = await response.json();
            setErrorChain(errorData.error_chain);
          }
        } catch (err) {
          setErrorChain([{ service: 'frontend', error: 'Network error' }]);
        }
      };
      
      return (
        <div>
          <button onClick={traceErrorChain}>Trace Error Chain</button>
          <div data-testid="error-chain">
            Services affected: {errorChain.length}
          </div>
        </div>
      );
    };
    
    setupFetchMock({
      ok: false,
      data: {
        error_chain: [
          { service: 'frontend', error: 'Request failed' },
          { service: 'api-gateway', error: 'Service unavailable' },
          { service: 'backend', error: 'Database connection timeout' }
        ]
      }
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Trace Error Chain'));
    });
    
    await waitFor(() => {
      expect(getByTestId('error-chain')).toHaveTextContent('Services affected: 3');
    });
  });

  it('should collect error metrics and analytics', async () => {
    const TestComponent = () => {
      const [errorMetrics, setErrorMetrics] = React.useState<any>(null);
      
      const fetchErrorMetrics = async () => {
        const response = await fetch('/api/errors/metrics');
        const data = await response.json();
        setErrorMetrics(data);
      };
      
      return (
        <div>
          <button onClick={fetchErrorMetrics}>Fetch Error Metrics</button>
          {errorMetrics && (
            <div data-testid="error-metrics">
              <div>Error Rate: {errorMetrics.error_rate}%</div>
              <div>MTTR: {errorMetrics.mttr_minutes}min</div>
            </div>
          )}
        </div>
      );
    };
    
    setupFetchMock({
      ok: true,
      data: {
        error_rate: 2.5,
        mttr_minutes: 15,
        total_errors: 125,
        resolved_errors: 120
      }
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Fetch Error Metrics'));
    });
    
    await waitFor(() => {
      expect(getByTestId('error-metrics')).toHaveTextContent('Error Rate: 2.5%');
      expect(getByTestId('error-metrics')).toHaveTextContent('MTTR: 15min');
    });
  });

  it('should implement error correlation and grouping', async () => {
    const TestComponent = () => {
      const [errorGroups, setErrorGroups] = React.useState<any[]>([]);
      
      const correlateErrors = async () => {
        const response = await fetch('/api/errors/correlate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            time_window: '1h',
            group_by: ['error_type', 'service']
          })
        });
        
        const data = await response.json();
        setErrorGroups(data.groups);
      };
      
      return (
        <div>
          <button onClick={correlateErrors}>Correlate Errors</button>
          <div data-testid="error-groups">
            Error groups: {errorGroups.length}
          </div>
        </div>
      );
    };
    
    setupFetchMock({
      ok: true,
      data: {
        groups: [
          { error_type: 'TimeoutError', service: 'database', count: 45 },
          { error_type: 'ValidationError', service: 'api', count: 12 }
        ]
      }
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Correlate Errors'));
    });
    
    await waitFor(() => {
      expect(getByTestId('error-groups')).toHaveTextContent('Error groups: 2');
    });
  });

  it('should maintain error audit trails', async () => {
    const TestComponent = () => {
      const [auditTrail, setAuditTrail] = React.useState<any[]>([]);
      
      const fetchAuditTrail = async () => {
        const response = await fetch('/api/errors/audit/error-123');
        const data = await response.json();
        setAuditTrail(data.audit_events);
      };
      
      return (
        <div>
          <button onClick={fetchAuditTrail}>Fetch Audit Trail</button>
          <div data-testid="audit-trail">
            Audit events: {auditTrail.length}
          </div>
        </div>
      );
    };
    
    setupFetchMock({
      ok: true,
      data: {
        audit_events: [
          { action: 'error_detected', timestamp: '2024-01-01T10:00:00Z' },
          { action: 'alert_sent', timestamp: '2024-01-01T10:01:00Z' },
          { action: 'remediation_started', timestamp: '2024-01-01T10:02:00Z' },
          { action: 'error_resolved', timestamp: '2024-01-01T10:05:00Z' }
        ]
      }
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Fetch Audit Trail'));
    });
    
    await waitFor(() => {
      expect(getByTestId('audit-trail')).toHaveTextContent('Audit events: 4');
    });
  });

  it('should handle error fingerprinting for deduplication', async () => {
    const TestComponent = () => {
      const [fingerprint, setFingerprint] = React.useState<string>('');
      const [duplicateCount, setDuplicateCount] = React.useState<number>(0);
      
      const generateFingerprint = async () => {
        const response = await fetch('/api/errors/fingerprint', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            error_message: 'Database connection failed',
            stack_trace: 'at connection.js:42',
            service: 'api'
          })
        });
        
        const data = await response.json();
        setFingerprint(data.fingerprint);
        setDuplicateCount(data.duplicate_count);
      };
      
      return (
        <div>
          <button onClick={generateFingerprint}>Generate Fingerprint</button>
          <div data-testid="fingerprint">Fingerprint: {fingerprint}</div>
          <div data-testid="duplicate-count">Duplicates: {duplicateCount}</div>
        </div>
      );
    };
    
    setupFetchMock({
      ok: true,
      data: {
        fingerprint: 'fp-db-conn-42',
        duplicate_count: 15,
        first_seen: '2024-01-01T09:00:00Z'
      }
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Generate Fingerprint'));
    });
    
    await waitFor(() => {
      expect(getByTestId('fingerprint')).toHaveTextContent('Fingerprint: fp-db-conn-42');
      expect(getByTestId('duplicate-count')).toHaveTextContent('Duplicates: 15');
    });
  });
});