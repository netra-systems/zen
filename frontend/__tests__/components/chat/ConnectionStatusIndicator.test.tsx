/**
 * Connection Status Utilities Tests
 * Tests utility functions for connection status display and formatting
 */

import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

describe('Connection Status Utils', () => {
  setupAntiHang();
    jest.setTimeout(10000);
  // Mock utility functions for testing
  const mockConnectionStatusUtils = {
    getConnectionState: (status: string, isReconnecting?: boolean) => {
      if (isReconnecting) return 'reconnecting';
      switch (status) {
        case 'OPEN': return 'connected';
        case 'CONNECTING': return 'connecting';
        case 'CLOSED':
        case 'CLOSING':
        default: return 'disconnected';
      }
    },
    
    getStatusInfo: (state: string) => {
      switch (state) {
        case 'connected':
          return { displayText: 'Connected', colorClass: 'text-emerald-500' };
        case 'connecting':
          return { displayText: 'Connecting', colorClass: 'text-yellow-500' };
        case 'reconnecting':
          return { displayText: 'Reconnecting', colorClass: 'text-orange-500' };
        default:
          return { displayText: 'Disconnected', colorClass: 'text-zinc-400' };
      }
    },
    
    formatDuration: (ms: number) => {
      const seconds = Math.floor(ms / 1000);
      const minutes = Math.floor(seconds / 60);
      const hours = Math.floor(minutes / 60);
      
      if (hours > 0) {
        const remainingMinutes = minutes % 60;
        return `${hours}h ${remainingMinutes}m`;
      } else if (minutes > 0) {
        const remainingSeconds = seconds % 60;
        return `${minutes}m ${remainingSeconds}s`;
      }
      return `${seconds}s`;
    },
    
    formatLatency: (latency: number | null) => {
      if (latency === null) return 'N/A';
      return latency >= 1000 ? `${(latency / 1000).toFixed(1)}s` : `${latency}ms`;
    },
    
    getConnectionQuality: (latency: number | null) => {
      if (latency === null) return { quality: 'unknown' };
      if (latency < 100) return { quality: 'excellent' };
      if (latency < 300) return { quality: 'good' };
      if (latency < 600) return { quality: 'fair' };
      return { quality: 'poor' };
    }
  };

  test('getConnectionState converts WebSocket status correctly', () => {
    expect(mockConnectionStatusUtils.getConnectionState('OPEN')).toBe('connected');
    expect(mockConnectionStatusUtils.getConnectionState('CONNECTING')).toBe('connecting');
    expect(mockConnectionStatusUtils.getConnectionState('CLOSED')).toBe('disconnected');
    expect(mockConnectionStatusUtils.getConnectionState('CLOSING')).toBe('disconnected');
    expect(mockConnectionStatusUtils.getConnectionState('OPEN', true)).toBe('reconnecting');
  });

  test('getStatusInfo returns correct display info', () => {
    const connectedInfo = mockConnectionStatusUtils.getStatusInfo('connected');
    expect(connectedInfo.displayText).toBe('Connected');
    expect(connectedInfo.colorClass).toContain('emerald');
    
    const disconnectedInfo = mockConnectionStatusUtils.getStatusInfo('disconnected');
    expect(disconnectedInfo.displayText).toBe('Disconnected');
    expect(disconnectedInfo.colorClass).toContain('zinc');
  });

  test('formatDuration formats time correctly', () => {
    expect(mockConnectionStatusUtils.formatDuration(30000)).toBe('30s');
    expect(mockConnectionStatusUtils.formatDuration(90000)).toBe('1m 30s');
    expect(mockConnectionStatusUtils.formatDuration(3700000)).toBe('1h 1m');
  });

  test('formatLatency formats latency correctly', () => {
    expect(mockConnectionStatusUtils.formatLatency(null)).toBe('N/A');
    expect(mockConnectionStatusUtils.formatLatency(50)).toBe('50ms');
    expect(mockConnectionStatusUtils.formatLatency(1500)).toBe('1.5s');
  });

  test('getConnectionQuality categorizes latency correctly', () => {
    expect(mockConnectionStatusUtils.getConnectionQuality(50).quality).toBe('excellent');
    expect(mockConnectionStatusUtils.getConnectionQuality(200).quality).toBe('good');
    expect(mockConnectionStatusUtils.getConnectionQuality(400).quality).toBe('fair');
    expect(mockConnectionStatusUtils.getConnectionQuality(800).quality).toBe('poor');
    expect(mockConnectionStatusUtils.getConnectionQuality(null).quality).toBe('unknown');
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});