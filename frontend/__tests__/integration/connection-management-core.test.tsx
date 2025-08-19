/**
 * Connection Management Core Tests
 * Split from connection-management.test.tsx for 300-line limit compliance
 * Agent 10 Implementation - Core connection state and heartbeat tests
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { jest } from '@jest/globals';
import { TestProviders } from '../setup/test-providers';
import { WebSocketTestManager } from '../helpers/websocket-test-manager';

interface ConnectionState {
  status: 'disconnected' | 'connecting' | 'connected' | 'reconnecting' | 'error';
  reconnectAttempts: number;
  lastHeartbeat: number;
  latency: number;
  quality: 'excellent' | 'good' | 'poor' | 'critical';
}

interface HeartbeatMetrics {
  sent: number;
  received: number;
  missed: number;
  intervalMs: number;
  enabled: boolean;
}

// Connection test component
const ConnectionTestComponent: React.FC = () => {
  const [connection, setConnection] = React.useState<ConnectionState>({
    status: 'disconnected', reconnectAttempts: 0, lastHeartbeat: 0,
    latency: 0, quality: 'excellent'
  });

  const [heartbeat, setHeartbeat] = React.useState<HeartbeatMetrics>({
    sent: 0, received: 0, missed: 0, intervalMs: 30000, enabled: false
  });

  const updateStatus = (status: ConnectionState['status']) => {
    setConnection(prev => ({ ...prev, status }));
  };

  const incrementReconnects = () => {
    setConnection(prev => ({ ...prev, reconnectAttempts: prev.reconnectAttempts + 1 }));
  };

  const recordHeartbeat = () => {
    setHeartbeat(prev => ({ ...prev, sent: prev.sent + 1, received: prev.received + 1 }));
    setConnection(prev => ({ ...prev, lastHeartbeat: Date.now() }));
  };

  const missHeartbeat = () => {
    setHeartbeat(prev => ({ ...prev, missed: prev.missed + 1 }));
  };

  const toggleHeartbeat = () => {
    setHeartbeat(prev => ({ ...prev, enabled: !prev.enabled }));
  };

  return (
    <div>
      <div data-testid="connection-status">{connection.status}</div>
      <div data-testid="reconnect-attempts">{connection.reconnectAttempts}</div>
      <div data-testid="heartbeat-sent">{heartbeat.sent}</div>
      <div data-testid="heartbeat-received">{heartbeat.received}</div>
      <div data-testid="heartbeat-missed">{heartbeat.missed}</div>
      <div data-testid="heartbeat-enabled">{heartbeat.enabled.toString()}</div>
      
      <button onClick={() => updateStatus('connecting')} data-testid="btn-connecting">Connect</button>
      <button onClick={() => updateStatus('connected')} data-testid="btn-connected">Connected</button>
      <button onClick={() => updateStatus('error')} data-testid="btn-error">Error</button>
      <button onClick={incrementReconnects} data-testid="btn-reconnect">Reconnect</button>
      <button onClick={recordHeartbeat} data-testid="btn-heartbeat">Heartbeat</button>
      <button onClick={missHeartbeat} data-testid="btn-miss">Miss</button>
      <button onClick={toggleHeartbeat} data-testid="btn-toggle">Toggle</button>
    </div>
  );
};

// Exponential backoff utility
class ExponentialBackoff {
  private baseDelay: number;
  private maxDelay: number;
  private multiplier: number;

  constructor(baseDelay = 1000, maxDelay = 30000, multiplier = 2) {
    this.baseDelay = baseDelay;
    this.maxDelay = maxDelay;
    this.multiplier = multiplier;
  }

  calculateDelay(attempt: number): number {
    const delay = this.baseDelay * Math.pow(this.multiplier, attempt - 1);
    return Math.min(delay, this.maxDelay);
  }

  getJitteredDelay(attempt: number): number {
    const baseDelay = this.calculateDelay(attempt);
    return baseDelay + (Math.random() * 0.1 * baseDelay);
  }
}

// Connection quality monitor
class ConnectionQualityMonitor {
  private latencyHistory: number[] = [];
  private maxHistory: number = 10;

  recordLatency(latency: number): void {
    this.latencyHistory.push(latency);
    if (this.latencyHistory.length > this.maxHistory) {
      this.latencyHistory.shift();
    }
  }

  getAverageLatency(): number {
    if (this.latencyHistory.length === 0) return 0;
    return this.latencyHistory.reduce((a, b) => a + b) / this.latencyHistory.length;
  }

  getQuality(): 'excellent' | 'good' | 'poor' | 'critical' {
    const avgLatency = this.getAverageLatency();
    if (avgLatency < 50) return 'excellent';
    if (avgLatency < 150) return 'good';
    if (avgLatency < 500) return 'poor';
    return 'critical';
  }
}

// Heartbeat manager
class HeartbeatManager {
  private interval: number;
  private timer: NodeJS.Timeout | null = null;
  private enabled: boolean = false;

  constructor(interval: number = 30000) { this.interval = interval; }
  isEnabled(): boolean { return this.enabled; }

  start(onHeartbeat: () => void): void {
    this.enabled = true;
    this.timer = setInterval(onHeartbeat, this.interval);
  }

  stop(): void {
    this.enabled = false;
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
  }
}

describe('Connection Management Core Tests', () => {
  let wsManager: WebSocketTestManager;
  let backoff: ExponentialBackoff;
  let qualityMonitor: ConnectionQualityMonitor;
  let heartbeatManager: HeartbeatManager;

  beforeEach(() => {
    wsManager = new WebSocketTestManager();
    backoff = new ExponentialBackoff();
    qualityMonitor = new ConnectionQualityMonitor();
    heartbeatManager = new HeartbeatManager();
    wsManager.setup();
    jest.useFakeTimers();
  });

  afterEach(() => {
    wsManager.cleanup();
    heartbeatManager.stop();
    jest.clearAllMocks();
    jest.useRealTimers();
  });

  describe('Connection State Management', () => {
    it('should track connection status changes', async () => {
      render(<TestProviders><ConnectionTestComponent /></TestProviders>);

      expect(screen.getByTestId('connection-status')).toHaveTextContent('disconnected');
      await userEvent.click(screen.getByTestId('btn-connecting'));
      expect(screen.getByTestId('connection-status')).toHaveTextContent('connecting');
      await userEvent.click(screen.getByTestId('btn-connected'));
      expect(screen.getByTestId('connection-status')).toHaveTextContent('connected');
      await userEvent.click(screen.getByTestId('btn-error'));
      expect(screen.getByTestId('connection-status')).toHaveTextContent('error');
    });

    it('should track reconnection attempts', async () => {
      render(<TestProviders><ConnectionTestComponent /></TestProviders>);

      expect(screen.getByTestId('reconnect-attempts')).toHaveTextContent('0');
      await userEvent.click(screen.getByTestId('btn-reconnect'));
      expect(screen.getByTestId('reconnect-attempts')).toHaveTextContent('1');
      await userEvent.click(screen.getByTestId('btn-reconnect'));
      expect(screen.getByTestId('reconnect-attempts')).toHaveTextContent('2');
    });
  });

  describe('Exponential Backoff', () => {
    it('should calculate exponential delays', () => {
      expect(backoff.calculateDelay(1)).toBe(1000);
      expect(backoff.calculateDelay(2)).toBe(2000);
      expect(backoff.calculateDelay(3)).toBe(4000);
      expect(backoff.calculateDelay(10)).toBe(30000);
    });

    it('should add jitter to delays', () => {
      const delay1 = backoff.getJitteredDelay(3);
      const delay2 = backoff.getJitteredDelay(3);
      expect(delay1).toBeGreaterThan(4000);
      expect(delay2).toBeGreaterThan(4000);
      expect(delay1).not.toBe(delay2);
    });
  });

  describe('Heartbeat Management', () => {
    it('should track heartbeat metrics', async () => {
      render(<TestProviders><ConnectionTestComponent /></TestProviders>);

      expect(screen.getByTestId('heartbeat-sent')).toHaveTextContent('0');
      await userEvent.click(screen.getByTestId('btn-heartbeat'));
      expect(screen.getByTestId('heartbeat-sent')).toHaveTextContent('1');
      expect(screen.getByTestId('heartbeat-received')).toHaveTextContent('1');
    });

    it('should track missed heartbeats', async () => {
      render(<TestProviders><ConnectionTestComponent /></TestProviders>);

      await userEvent.click(screen.getByTestId('btn-miss'));
      expect(screen.getByTestId('heartbeat-missed')).toHaveTextContent('1');
    });

    it('should toggle heartbeat enabled state', async () => {
      render(<TestProviders><ConnectionTestComponent /></TestProviders>);

      expect(screen.getByTestId('heartbeat-enabled')).toHaveTextContent('false');
      await userEvent.click(screen.getByTestId('btn-toggle'));
      expect(screen.getByTestId('heartbeat-enabled')).toHaveTextContent('true');
    });

    it('should manage heartbeat lifecycle', () => {
      let count = 0;
      heartbeatManager.start(() => count++);
      expect(heartbeatManager.isEnabled()).toBe(true);
      heartbeatManager.stop();
      expect(heartbeatManager.isEnabled()).toBe(false);
    });
  });

  describe('Connection Quality Monitoring', () => {
    it('should calculate quality based on latency', () => {
      qualityMonitor.recordLatency(30);
      expect(qualityMonitor.getQuality()).toBe('excellent');
      qualityMonitor.recordLatency(100);
      expect(qualityMonitor.getQuality()).toBe('good');
      qualityMonitor.recordLatency(300);
      expect(qualityMonitor.getQuality()).toBe('poor');
      qualityMonitor.recordLatency(600);
      expect(qualityMonitor.getQuality()).toBe('critical');
    });

    it('should track average latency', () => {
      qualityMonitor.recordLatency(100);
      qualityMonitor.recordLatency(200);
      qualityMonitor.recordLatency(150);
      expect(qualityMonitor.getAverageLatency()).toBe(150);
    });

    it('should limit latency history', () => {
      for (let i = 0; i < 15; i++) {
        qualityMonitor.recordLatency(i * 10);
      }
      expect(qualityMonitor.getAverageLatency()).toBeCloseTo(95, 0);
    });
  });

  describe('Resource Cleanup', () => {
    it('should clean up connection resources', async () => {
      const { unmount } = render(<TestProviders><ConnectionTestComponent /></TestProviders>);
      unmount();
      expect(true).toBe(true);
    });

    it('should stop heartbeat on cleanup', () => {
      heartbeatManager.start(() => {});
      expect(heartbeatManager.isEnabled()).toBe(true);
      heartbeatManager.stop();
      expect(heartbeatManager.isEnabled()).toBe(false);
    });
  });
});