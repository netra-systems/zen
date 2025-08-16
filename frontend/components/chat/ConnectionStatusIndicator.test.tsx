// Basic test for connection status utilities
// Testing connection state logic and utility functions

import { 
  getConnectionState, 
  getStatusInfo, 
  formatDuration, 
  formatLatency, 
  getConnectionQuality 
} from '@/utils/connection-status-utils';

describe('Connection Status Utils', () => {
  test('getConnectionState converts WebSocket status correctly', () => {
    expect(getConnectionState('OPEN')).toBe('connected');
    expect(getConnectionState('CONNECTING')).toBe('connecting');
    expect(getConnectionState('CLOSED')).toBe('disconnected');
    expect(getConnectionState('CLOSING')).toBe('disconnected');
    expect(getConnectionState('OPEN', true)).toBe('reconnecting');
  });

  test('getStatusInfo returns correct display info', () => {
    const connectedInfo = getStatusInfo('connected');
    expect(connectedInfo.displayText).toBe('Connected');
    expect(connectedInfo.colorClass).toContain('emerald');
    
    const disconnectedInfo = getStatusInfo('disconnected');
    expect(disconnectedInfo.displayText).toBe('Disconnected');
    expect(disconnectedInfo.colorClass).toContain('zinc');
  });

  test('formatDuration formats time correctly', () => {
    expect(formatDuration(30000)).toBe('30s');
    expect(formatDuration(90000)).toBe('1m 30s');
    expect(formatDuration(3700000)).toBe('1h 1m');
  });

  test('formatLatency formats latency correctly', () => {
    expect(formatLatency(null)).toBe('N/A');
    expect(formatLatency(50)).toBe('50ms');
    expect(formatLatency(1500)).toBe('1.5s');
  });

  test('getConnectionQuality categorizes latency correctly', () => {
    expect(getConnectionQuality(50).quality).toBe('excellent');
    expect(getConnectionQuality(200).quality).toBe('good');
    expect(getConnectionQuality(400).quality).toBe('fair');
    expect(getConnectionQuality(800).quality).toBe('poor');
    expect(getConnectionQuality(null).quality).toBe('unknown');
  });
});