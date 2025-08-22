/**
 * Heartbeat Timing Fix Utilities
 */

export function setupHeartbeatMocks(): void {
  jest.useFakeTimers();
}

export function cleanupHeartbeatMocks(): void {
  jest.useRealTimers();
}