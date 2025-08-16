import type { StateCreator } from 'zustand';
import { WebSocketEventBuffer } from '@/lib/circular-buffer';
import type { PerformanceState } from './types';

export const createPerformanceSlice: StateCreator<
  PerformanceState,
  [],
  [],
  PerformanceState
> = () => ({
  performanceMetrics: {
    renderCount: 0,
    lastRenderTime: 0,
    averageResponseTime: 0,
    memoryUsage: 0
  },
  wsEventBuffer: new WebSocketEventBuffer(1000)
});