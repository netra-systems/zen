/**
 * WebSocket Component Utilities
 * Reusable WebSocket test components with 8-line function limit enforcement
 */

import React from 'react';
import {
  WebSocketConnectionLifecycle,
  MessageMetrics
} from '../../helpers/websocket-test-utilities';

// Types for WebSocket test components
export interface WebSocketTestComponentProps {
  lifecycle: WebSocketConnectionLifecycle;
  metrics: MessageMetrics;
  updateLifecycle: (state: keyof WebSocketConnectionLifecycle) => void;
  updateMetrics: (metric: keyof MessageMetrics) => void;
}

// Custom hooks for WebSocket test state (≤8 lines each)
export const useWebSocketLifecycle = () => {
  const [lifecycle, setLifecycle] = React.useState<WebSocketConnectionLifecycle>({
    connecting: false,
    connected: false,
    disconnected: true,
    error: false,
    reconnecting: false
  });
  
  const updateLifecycle = (state: keyof WebSocketConnectionLifecycle) => {
    setLifecycle(prev => ({ ...prev, [state]: true }));
  };
  
  return { lifecycle, updateLifecycle };
};

export const useWebSocketMetrics = () => {
  const [metrics, setMetrics] = React.useState<MessageMetrics>({
    sent: 0,
    received: 0,
    queued: 0,
    failed: 0,
    largeMessages: 0
  });
  
  const updateMetrics = (metric: keyof MessageMetrics) => {
    setMetrics(prev => ({ ...prev, [metric]: prev[metric] + 1 }));
  };
  
  return { metrics, updateMetrics };
};

// WebSocket test component factory (≤8 lines)
export const createWebSocketTestComponent = (props: WebSocketTestComponentProps) => {
  return (
    <div>
      {createLifecycleDisplay(props.lifecycle)}
      {createMetricsDisplay(props.metrics)}
      {createLifecycleButtons(props.updateLifecycle)}
      {createMetricsButtons(props.updateMetrics)}
    </div>
  );
};

// Component builders (≤8 lines each)
const createLifecycleDisplay = (lifecycle: WebSocketConnectionLifecycle) => (
  <div>
    <div data-testid="ws-connecting">{lifecycle.connecting.toString()}</div>
    <div data-testid="ws-connected">{lifecycle.connected.toString()}</div>
    <div data-testid="ws-disconnected">{lifecycle.disconnected.toString()}</div>
    <div data-testid="ws-error">{lifecycle.error.toString()}</div>
    <div data-testid="ws-reconnecting">{lifecycle.reconnecting.toString()}</div>
  </div>
);

const createMetricsDisplay = (metrics: MessageMetrics) => (
  <div>
    <div data-testid="metrics-sent">{metrics.sent}</div>
    <div data-testid="metrics-received">{metrics.received}</div>
    <div data-testid="metrics-queued">{metrics.queued}</div>
    <div data-testid="metrics-failed">{metrics.failed}</div>
    <div data-testid="metrics-large">{metrics.largeMessages}</div>
  </div>
);

const createLifecycleButtons = (updateLifecycle: (state: keyof WebSocketConnectionLifecycle) => void) => (
  <div>
    <button onClick={() => updateLifecycle('connecting')} data-testid="btn-connecting">
      Start Connecting
    </button>
    <button onClick={() => updateLifecycle('connected')} data-testid="btn-connected">
      Connected
    </button>
    <button onClick={() => updateLifecycle('disconnected')} data-testid="btn-disconnected">
      Disconnected
    </button>
    <button onClick={() => updateLifecycle('error')} data-testid="btn-error">
      Error
    </button>
    <button onClick={() => updateLifecycle('reconnecting')} data-testid="btn-reconnecting">
      Reconnecting
    </button>
  </div>
);

const createMetricsButtons = (updateMetrics: (metric: keyof MessageMetrics) => void) => (
  <div>
    <button onClick={() => updateMetrics('sent')} data-testid="btn-send">
      Send Message
    </button>
    <button onClick={() => updateMetrics('received')} data-testid="btn-receive">
      Receive Message
    </button>
    <button onClick={() => updateMetrics('queued')} data-testid="btn-queue">
      Queue Message
    </button>
    <button onClick={() => updateMetrics('failed')} data-testid="btn-fail">
      Fail Message
    </button>
    <button onClick={() => updateMetrics('largeMessages')} data-testid="btn-large">
      Large Message
    </button>
  </div>
);