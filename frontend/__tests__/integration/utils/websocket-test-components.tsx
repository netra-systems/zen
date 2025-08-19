/**
 * WebSocket Test Components - Shared test utilities and components
 * Extracted from oversized websocket-complete.test.tsx for modularity
 * Maintains all shared components for WebSocket testing modules
 */

import React from 'react';

// Type definitions for WebSocket testing
export interface WebSocketConnectionLifecycle {
  connecting: boolean;
  connected: boolean;
  disconnected: boolean;
  error: boolean;
  reconnecting: boolean;
}

export interface MessageMetrics {
  sent: number;
  received: number;
  queued: number;
  failed: number;
  largeMessages: number;
}

// Test component for WebSocket lifecycle
export const WebSocketLifecycleTest: React.FC = () => {
  const [lifecycle, setLifecycle] = React.useState<WebSocketConnectionLifecycle>({
    connecting: false,
    connected: false,
    disconnected: true,
    error: false,
    reconnecting: false
  });

  const [metrics, setMetrics] = React.useState<MessageMetrics>({
    sent: 0,
    received: 0,
    queued: 0,
    failed: 0,
    largeMessages: 0
  });

  const updateLifecycle = (state: keyof WebSocketConnectionLifecycle) => {
    setLifecycle(prev => ({ ...prev, [state]: true }));
  };

  const updateMetrics = (metric: keyof MessageMetrics) => {
    setMetrics(prev => ({ ...prev, [metric]: prev[metric] + 1 }));
  };

  return (
    <div>
      <div data-testid="ws-connecting">{lifecycle.connecting.toString()}</div>
      <div data-testid="ws-connected">{lifecycle.connected.toString()}</div>
      <div data-testid="ws-disconnected">{lifecycle.disconnected.toString()}</div>
      <div data-testid="ws-error">{lifecycle.error.toString()}</div>
      <div data-testid="ws-reconnecting">{lifecycle.reconnecting.toString()}</div>
      
      <div data-testid="metrics-sent">{metrics.sent}</div>
      <div data-testid="metrics-received">{metrics.received}</div>
      <div data-testid="metrics-queued">{metrics.queued}</div>
      <div data-testid="metrics-failed">{metrics.failed}</div>
      <div data-testid="metrics-large">{metrics.largeMessages}</div>
      
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
};

// Common test setup helper functions
export const setupWebSocketTest = () => {
  // Common setup logic that can be reused across test modules
  return {
    cleanup: () => {
      // Common cleanup logic
    }
  };
};

export const getTestProviderWrapper = () => {
  // Returns wrapper component for consistent test provider setup
  return ({ children }: { children: React.ReactNode }) => (
    <div data-testid="test-provider-wrapper">
      {children}
    </div>
  );
};