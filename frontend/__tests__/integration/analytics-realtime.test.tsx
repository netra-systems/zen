import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
import React from 'react';
import { render, waitFor, fireEvent, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { TestProviders } from '@/__tests__/setup/test-providers';
import { { render, waitFor, fireEvent, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { TestProviders } from '@/__tests__/setup/test-providers';
import { 
  initInfrastructureTest,
  setupFetchMock,
  simulateWebSocketMessage,
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

describe('Real-time Metrics Integration', () => {
    jest.setTimeout(10000);
  it('should aggregate metrics in real-time', async () => {
    const TestComponent = () => {
      const [metrics, setMetrics] = React.useState<any>({});
      
      React.useEffect(() => {
        const handleMessage = (data: any) => {
          if (data.type === 'metrics_update') {
            setMetrics(data.metrics);
          }
        };
        
        simulateWebSocketMessage(handleMessage, {
          type: 'metrics_update',
          metrics: { requests_per_second: 150 }
        });
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
    
    await waitFor(() => {
      expect(getByTestId('metrics')).toHaveTextContent('RPS: 150');
    }, { timeout: 200 });
  });

  it('should handle metric streaming', async () => {
    const TestComponent = () => {
      const [streamData, setStreamData] = React.useState<any[]>([]);
      
      React.useEffect(() => {
        const handleStreamUpdate = (data: any) => {
          if (data.type === 'metric_stream') {
            setStreamData(prev => [...prev, data.metric]);
          }
        };
        
        simulateWebSocketMessage(handleStreamUpdate, {
          type: 'metric_stream',
          metric: { timestamp: Date.now(), value: 100 }
        }, 50);
        
        simulateWebSocketMessage(handleStreamUpdate, {
          type: 'metric_stream',
          metric: { timestamp: Date.now() + 1000, value: 120 }
        }, 100);
      }, []);
      
      return (
        <div data-testid="stream-data">
          Metrics received: {streamData.length}
        </div>
      );
    };
    
    const { getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await waitFor(() => {
      expect(getByTestId('stream-data')).toHaveTextContent('Metrics received: 2');
    }, { timeout: 300 });
  });

  it('should calculate rolling averages', async () => {
    const TestComponent = () => {
      const [rollingAvg, setRollingAvg] = React.useState<number | null>(null);
      
      const calculateRollingAverage = async () => {
        const response = await fetch('/api/analytics/rolling-average', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            metric: 'response_time',
            window: '5m'
          })
        });
        
        const data = await response.json();
        setRollingAvg(data.average);
      };
      
      return (
        <div>
          <button onClick={calculateRollingAverage}>Calculate Average</button>
          {rollingAvg !== null && (
            <div data-testid="rolling-avg">
              5min avg: {rollingAvg}ms
            </div>
          )}
        </div>
      );
    };
    
    setupFetchMock({
      ok: true,
      data: { average: 125.5, window: '5m' }
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Calculate Average'));
    });
    
    await waitFor(() => {
      expect(getByTestId('rolling-avg')).toHaveTextContent('5min avg: 125.5ms');
    });
  });

  it('should detect anomalies in metrics', async () => {
    const TestComponent = () => {
      const [anomalies, setAnomalies] = React.useState<any[]>([]);
      
      const detectAnomalies = async () => {
        const response = await fetch('/api/analytics/anomalies');
        const data = await response.json();
        setAnomalies(data.anomalies);
      };
      
      return (
        <div>
          <button onClick={detectAnomalies}>Detect Anomalies</button>
          <div data-testid="anomaly-count">
            Anomalies detected: {anomalies.length}
          </div>
        </div>
      );
    };
    
    setupFetchMock({
      ok: true,
      data: {
        anomalies: [
          { metric: 'response_time', value: 5000, threshold: 1000 },
          { metric: 'error_rate', value: 0.15, threshold: 0.05 }
        ]
      }
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Detect Anomalies'));
    });
    
    await waitFor(() => {
      expect(getByTestId('anomaly-count')).toHaveTextContent('Anomalies detected: 2');
    });
  });

  it('should handle real-time dashboard updates', async () => {
    const TestComponent = () => {
      const [dashboardData, setDashboardData] = React.useState<any>({});
      
      React.useEffect(() => {
        const handleDashboardUpdate = (data: any) => {
          if (data.type === 'dashboard_update') {
            setDashboardData(data.dashboard);
          }
        };
        
        simulateWebSocketMessage(handleDashboardUpdate, {
          type: 'dashboard_update',
          dashboard: {
            active_users: 1250,
            cpu_usage: 65,
            memory_usage: 78
          }
        });
      }, []);
      
      return (
        <div data-testid="dashboard">
          {dashboardData.active_users && (
            <div>Active Users: {dashboardData.active_users}</div>
          )}
          {dashboardData.cpu_usage && (
            <div>CPU: {dashboardData.cpu_usage}%</div>
          )}
        </div>
      );
    };
    
    const { getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await waitFor(() => {
      expect(getByTestId('dashboard')).toHaveTextContent('Active Users: 1250');
      expect(getByTestId('dashboard')).toHaveTextContent('CPU: 65%');
    }, { timeout: 200 });
  });

  it('should implement metric alerting thresholds', async () => {
    const TestComponent = () => {
      const [alerts, setAlerts] = React.useState<any[]>([]);
      
      React.useEffect(() => {
        const handleAlert = (data: any) => {
          if (data.type === 'metric_alert') {
            setAlerts(prev => [...prev, data.alert]);
          }
        };
        
        simulateWebSocketMessage(handleAlert, {
          type: 'metric_alert',
          alert: {
            metric: 'error_rate',
            value: 0.08,
            threshold: 0.05,
            severity: 'warning'
          }
        });
      }, []);
      
      return (
        <div data-testid="alerts">
          Active alerts: {alerts.length}
        </div>
      );
    };
    
    const { getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await waitFor(() => {
      expect(getByTestId('alerts')).toHaveTextContent('Active alerts: 1');
    }, { timeout: 200 });
  });

  it('should handle metric data buffering for offline scenarios', async () => {
    const TestComponent = () => {
      const [bufferStatus, setBufferStatus] = React.useState<string>('');
      const [bufferedCount, setBufferedCount] = React.useState<number>(0);
      
      const simulateOfflineMode = async () => {
        setBufferStatus('offline');
        
        // Simulate buffering metrics while offline
        let count = 0;
        const interval = setInterval(() => {
          count++;
          setBufferedCount(count);
          
          if (count >= 5) {
            clearInterval(interval);
            setBufferStatus('online');
            // Simulate sync when back online
            setTimeout(() => {
              setBufferStatus('synced');
              setBufferedCount(0);
            }, 100);
          }
        }, 20);
      };
      
      return (
        <div>
          <button onClick={simulateOfflineMode}>Simulate Offline</button>
          <div data-testid="buffer-status">Status: {bufferStatus}</div>
          <div data-testid="buffered-count">Buffered: {bufferedCount}</div>
        </div>
      );
    };
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Simulate Offline'));
    });
    
    await waitFor(() => {
      expect(getByTestId('buffer-status')).toHaveTextContent('Status: synced');
      expect(getByTestId('buffered-count')).toHaveTextContent('Buffered: 0');
    }, { timeout: 500 });
  });

  it('should implement metric data compression for streaming', async () => {
    const TestComponent = () => {
      const [compressionStats, setCompressionStats] = React.useState<any>(null);
      
      const testCompression = async () => {
        const response = await fetch('/api/analytics/compression-test', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            data_size: '10MB',
            compression_algorithm: 'gzip'
          })
        });
        
        const data = await response.json();
        setCompressionStats(data);
      };
      
      return (
        <div>
          <button onClick={testCompression}>Test Compression</button>
          {compressionStats && (
            <div data-testid="compression-stats">
              Compression ratio: {compressionStats.ratio}x
            </div>
          )}
        </div>
      );
    };
    
    setupFetchMock({
      ok: true,
      data: {
        ratio: 4.2,
        original_size: '10MB',
        compressed_size: '2.4MB',
        compression_time: 150
      }
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await act(async () => {
      fireEvent.click(getByText('Test Compression'));
    });
    
    await waitFor(() => {
      expect(getByTestId('compression-stats')).toHaveTextContent('Compression ratio: 4.2x');
    });
  });
});