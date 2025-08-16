// Connection status utilities for WebSocket state management
// Modular utilities for connection state calculation and metrics

import { WebSocketStatus } from '@/services/webSocketService';

// Connection state types
export type ConnectionState = 'connected' | 'connecting' | 'reconnecting' | 'disconnected' | 'error';

export interface ConnectionMetrics {
  latency: number | null;
  reconnectionCount: number;
  lastReconnectTime: number | null;
  connectionDuration: number;
  messagesSent: number;
  messagesReceived: number;
}

export interface ConnectionStatusInfo {
  state: ConnectionState;
  status: WebSocketStatus;
  displayText: string;
  colorClass: string;
  iconClass: string;
}

// Convert WebSocket status to connection state
export const getConnectionState = (
  status: WebSocketStatus,
  isReconnecting: boolean = false
): ConnectionState => {
  if (isReconnecting) return 'reconnecting';
  
  switch (status) {
    case 'OPEN': return 'connected';
    case 'CONNECTING': return 'connecting';
    case 'CLOSED': return 'disconnected';
    case 'CLOSING': return 'disconnected';
    default: return 'error';
  }
};

// Get status info for display
export const getStatusInfo = (state: ConnectionState): Omit<ConnectionStatusInfo, 'state' | 'status'> => {
  switch (state) {
    case 'connected':
      return {
        displayText: 'Connected',
        colorClass: 'text-emerald-600',
        iconClass: 'bg-emerald-500'
      };
    case 'connecting':
      return {
        displayText: 'Connecting...',
        colorClass: 'text-zinc-600',
        iconClass: 'bg-zinc-400'
      };
    case 'reconnecting':
      return {
        displayText: 'Reconnecting...',
        colorClass: 'text-yellow-600',
        iconClass: 'bg-yellow-500'
      };
    case 'disconnected':
      return {
        displayText: 'Disconnected',
        colorClass: 'text-zinc-500',
        iconClass: 'bg-zinc-400'
      };
    case 'error':
      return {
        displayText: 'Connection Error',
        colorClass: 'text-red-600',
        iconClass: 'bg-red-500'
      };
    default:
      return {
        displayText: 'Unknown',
        colorClass: 'text-zinc-500',
        iconClass: 'bg-zinc-400'
      };
  }
};

// Format connection duration
export const formatDuration = (ms: number): string => {
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  
  if (hours > 0) {
    return `${hours}h ${minutes % 60}m`;
  }
  if (minutes > 0) {
    return `${minutes}m ${seconds % 60}s`;
  }
  return `${seconds}s`;
};

// Format latency display
export const formatLatency = (latency: number | null): string => {
  if (latency === null) return 'N/A';
  
  if (latency < 1000) {
    return `${Math.round(latency)}ms`;
  }
  
  return `${(latency / 1000).toFixed(1)}s`;
};

// Get connection quality based on latency
export const getConnectionQuality = (latency: number | null): {
  quality: 'excellent' | 'good' | 'fair' | 'poor' | 'unknown';
  color: string;
} => {
  if (latency === null) {
    return { quality: 'unknown', color: 'text-zinc-500' };
  }
  
  if (latency < 100) {
    return { quality: 'excellent', color: 'text-emerald-600' };
  }
  if (latency < 300) {
    return { quality: 'good', color: 'text-emerald-500' };
  }
  if (latency < 500) {
    return { quality: 'fair', color: 'text-yellow-600' };
  }
  
  return { quality: 'poor', color: 'text-red-600' };
};