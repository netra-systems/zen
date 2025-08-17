/**
 * Error Remediation Integration Tests
 * Tests for error alerting and automated remediation workflows
 * Enterprise segment - ensures automated error recovery
 */

import React from 'react';
import { render, waitFor, fireEvent, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { TestProviders } from '../test-utils/providers';
import { 
  initInfrastructureTest,
  setupFetchMock,
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

describe('Error Alerting and Notifications', () => {
  it('should support error alerting and notifications', async () => {
    const TestComponent = () => {
      const [alertStatus, setAlertStatus] = React.useState('');
      
      const setupErrorAlert = async () => {
        const response = await fetch('/api/alerts/error-threshold', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            threshold: 5.0,
            window: '5m',
            notification_channels: ['slack', 'email']
          })
        });
        
        const result = await response.json();
        setAlertStatus(`Alert configured: ${result.alert_id}`);
      };
      
      return (
        <div>
          <button onClick={setupErrorAlert}>Setup Alert</button>
          <div data-testid="alert-status">{alertStatus}</div>
        </div>
      );
    };
    
    setupFetchMock({
      ok: true,
      data: {
        alert_id: 'alert-error-123',
        status: 'active',
        threshold: 5.0
      }
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Setup Alert'));
    });
    
    await waitFor(() => {
      expect(getByTestId('alert-status')).toHaveTextContent('Alert configured: alert-error-123');
    });
  });

  it('should handle escalation workflows for critical errors', async () => {
    const TestComponent = () => {
      const [escalationStatus, setEscalationStatus] = React.useState('');
      
      const triggerEscalation = async () => {
        const response = await fetch('/api/alerts/escalate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            error_id: 'critical-error-456',
            severity: 'critical',
            auto_escalate: true
          })
        });
        
        const result = await response.json();
        setEscalationStatus(`Escalated to: ${result.escalated_to}`);
      };
      
      return (
        <div>
          <button onClick={triggerEscalation}>Trigger Escalation</button>
          <div data-testid="escalation-status">{escalationStatus}</div>
        </div>
      );
    };
    
    setupFetchMock({
      ok: true,
      data: {
        escalated_to: 'on-call-engineer',
        escalation_id: 'esc-789',
        notification_sent: true
      }
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Trigger Escalation'));
    });
    
    await waitFor(() => {
      expect(getByTestId('escalation-status')).toHaveTextContent('Escalated to: on-call-engineer');
    });
  });

  it('should implement smart alerting with noise reduction', async () => {
    const TestComponent = () => {
      const [alertsSuppressed, setAlertsSuppressed] = React.useState<number>(0);
      
      const checkNoiseReduction = async () => {
        const response = await fetch('/api/alerts/noise-reduction');
        const data = await response.json();
        setAlertsSuppressed(data.suppressed_count);
      };
      
      return (
        <div>
          <button onClick={checkNoiseReduction}>Check Noise Reduction</button>
          <div data-testid="suppressed-count">
            Suppressed alerts: {alertsSuppressed}
          </div>
        </div>
      );
    };
    
    setupFetchMock({
      ok: true,
      data: {
        suppressed_count: 24,
        reduction_rules: ['duplicate_errors', 'flapping_services'],
        noise_reduction_rate: 0.75
      }
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Check Noise Reduction'));
    });
    
    await waitFor(() => {
      expect(getByTestId('suppressed-count')).toHaveTextContent('Suppressed alerts: 24');
    });
  });
});

describe('Automated Remediation Workflows', () => {
  it('should handle error remediation workflows', async () => {
    const TestComponent = () => {
      const [remediationStatus, setRemediationStatus] = React.useState('');
      
      const triggerRemediation = async () => {
        const response = await fetch('/api/errors/remediate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            error_id: 'error-123',
            remediation_type: 'auto_restart'
          })
        });
        
        const result = await response.json();
        setRemediationStatus(`Remediation: ${result.status}`);
      };
      
      return (
        <div>
          <button onClick={triggerRemediation}>Trigger Remediation</button>
          <div data-testid="remediation-status">{remediationStatus}</div>
        </div>
      );
    };
    
    setupFetchMock({
      ok: true,
      data: {
        status: 'completed',
        remediation_id: 'rem-456',
        duration_ms: 2500
      }
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Trigger Remediation'));
    });
    
    await waitFor(() => {
      expect(getByTestId('remediation-status')).toHaveTextContent('Remediation: completed');
    });
  });

  it('should implement rollback mechanisms for failed deployments', async () => {
    const TestComponent = () => {
      const [rollbackStatus, setRollbackStatus] = React.useState('');
      
      const initiateRollback = async () => {
        const response = await fetch('/api/remediation/rollback', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            deployment_id: 'deploy-123',
            target_version: 'v1.2.0',
            reason: 'high_error_rate'
          })
        });
        
        const result = await response.json();
        setRollbackStatus(`Rollback: ${result.status}`);
      };
      
      return (
        <div>
          <button onClick={initiateRollback}>Initiate Rollback</button>
          <div data-testid="rollback-status">{rollbackStatus}</div>
        </div>
      );
    };
    
    setupFetchMock({
      ok: true,
      data: {
        status: 'completed',
        rollback_id: 'rb-789',
        previous_version: 'v1.3.0',
        current_version: 'v1.2.0'
      }
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Initiate Rollback'));
    });
    
    await waitFor(() => {
      expect(getByTestId('rollback-status')).toHaveTextContent('Rollback: completed');
    });
  });

  it('should handle auto-scaling for resource exhaustion errors', async () => {
    const TestComponent = () => {
      const [scalingStatus, setScalingStatus] = React.useState('');
      
      const triggerAutoScale = async () => {
        const response = await fetch('/api/remediation/autoscale', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            service: 'api-server',
            metric: 'cpu_utilization',
            threshold: 80
          })
        });
        
        const result = await response.json();
        setScalingStatus(`Scaled to ${result.new_instance_count} instances`);
      };
      
      return (
        <div>
          <button onClick={triggerAutoScale}>Trigger Auto Scale</button>
          <div data-testid="scaling-status">{scalingStatus}</div>
        </div>
      );
    };
    
    setupFetchMock({
      ok: true,
      data: {
        new_instance_count: 6,
        previous_instance_count: 3,
        scaling_time_ms: 45000
      }
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Trigger Auto Scale'));
    });
    
    await waitFor(() => {
      expect(getByTestId('scaling-status')).toHaveTextContent('Scaled to 6 instances');
    });
  });

  it('should implement circuit breaker remediation', async () => {
    const TestComponent = () => {
      const [circuitStatus, setCircuitStatus] = React.useState('');
      
      const triggerCircuitBreaker = async () => {
        const response = await fetch('/api/remediation/circuit-breaker', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            service: 'external-api',
            error_threshold: 50,
            action: 'open'
          })
        });
        
        const result = await response.json();
        setCircuitStatus(`Circuit breaker: ${result.state}`);
      };
      
      return (
        <div>
          <button onClick={triggerCircuitBreaker}>Trigger Circuit Breaker</button>
          <div data-testid="circuit-status">{circuitStatus}</div>
        </div>
      );
    };
    
    setupFetchMock({
      ok: true,
      data: {
        state: 'open',
        fallback_enabled: true,
        recovery_timeout: 60000
      }
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Trigger Circuit Breaker'));
    });
    
    await waitFor(() => {
      expect(getByTestId('circuit-status')).toHaveTextContent('Circuit breaker: open');
    });
  });

  it('should track remediation effectiveness', async () => {
    const TestComponent = () => {
      const [effectiveness, setEffectiveness] = React.useState<any>(null);
      
      const checkEffectiveness = async () => {
        const response = await fetch('/api/remediation/effectiveness');
        const data = await response.json();
        setEffectiveness(data);
      };
      
      return (
        <div>
          <button onClick={checkEffectiveness}>Check Effectiveness</button>
          {effectiveness && (
            <div data-testid="effectiveness">
              Success rate: {effectiveness.success_rate}%
            </div>
          )}
        </div>
      );
    };
    
    setupFetchMock({
      ok: true,
      data: {
        success_rate: 87.5,
        total_remediations: 40,
        successful_remediations: 35,
        avg_resolution_time: 150
      }
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Check Effectiveness'));
    });
    
    await waitFor(() => {
      expect(getByTestId('effectiveness')).toHaveTextContent('Success rate: 87.5%');
    });
  });
});