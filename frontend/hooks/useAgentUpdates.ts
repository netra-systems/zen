/**
 * useAgentUpdates - React hook for consuming continuous agent updates
 * Provides auto-subscription management and performance monitoring
 */
'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { agentUpdateStream, type AgentUpdate, type StreamBatch } from '@/services/agent-update-stream';
import { logger } from '@/lib/logger';

export interface UseAgentUpdatesOptions {
  agentId?: string;
  batchSize?: number;
  enablePerformanceMonitoring?: boolean;
  onUpdate?: (update: AgentUpdate) => void;
  onBatch?: (batch: StreamBatch) => void;
}

export interface AgentUpdatesState {
  latestUpdate: AgentUpdate | null;
  updateHistory: AgentUpdate[];
  isStreaming: boolean;
  streamMetrics: ReturnType<typeof agentUpdateStream.getMetrics>;
}

export interface AgentUpdatesControls {
  startStreaming: () => void;
  stopStreaming: () => void;
  clearHistory: () => void;
  getUpdatesByAgent: (agentId: string) => AgentUpdate[];
  getLatestUpdateForAgent: (agentId: string) => AgentUpdate | null;
}

export interface UseAgentUpdatesReturn {
  state: AgentUpdatesState;
  controls: AgentUpdatesControls;
}

export const useAgentUpdates = (options: UseAgentUpdatesOptions = {}): UseAgentUpdatesReturn => {
  const {
    agentId,
    batchSize = 10,
    enablePerformanceMonitoring = false,
    onUpdate,
    onBatch
  } = options;

  // ============================================
  // State Management
  // ============================================

  const [state, setState] = useState<AgentUpdatesState>({
    latestUpdate: null,
    updateHistory: [],
    isStreaming: false,
    streamMetrics: agentUpdateStream.getMetrics()
  });

  const subscriptionIdRef = useRef<string | null>(null);
  const performanceTimerRef = useRef<NodeJS.Timeout | null>(null);

  // ============================================
  // Stream Event Handlers
  // ============================================

  const handleStreamBatch = useCallback((batch: StreamBatch) => {
    const filteredUpdates = filterUpdatesForAgent(batch.updates, agentId);
    
    if (filteredUpdates.length === 0) return;
    
    setState(prev => ({
      ...prev,
      latestUpdate: filteredUpdates[filteredUpdates.length - 1],
      updateHistory: mergeUpdatesWithHistory(prev.updateHistory, filteredUpdates, batchSize),
      streamMetrics: agentUpdateStream.getMetrics()
    }));
    
    // Trigger callbacks
    filteredUpdates.forEach(update => onUpdate?.(update));
    onBatch?.(batch);
    
    logBatchProcessing(batch, filteredUpdates.length);
  }, [agentId, batchSize, onUpdate, onBatch]);

  // ============================================
  // Stream Controls
  // ============================================

  const startStreaming = useCallback(() => {
    if (subscriptionIdRef.current) return;
    
    subscriptionIdRef.current = agentUpdateStream.subscribe(
      handleStreamBatch,
      agentId ? createAgentFilter(agentId) : undefined
    );
    
    agentUpdateStream.start();
    
    setState(prev => ({ ...prev, isStreaming: true }));
    
    if (enablePerformanceMonitoring) {
      startPerformanceMonitoring();
    }
    
    logStreamStart();
  }, [handleStreamBatch, agentId, enablePerformanceMonitoring]);

  const stopStreaming = useCallback(() => {
    if (!subscriptionIdRef.current) return;
    
    agentUpdateStream.unsubscribe(subscriptionIdRef.current);
    subscriptionIdRef.current = null;
    
    setState(prev => ({ ...prev, isStreaming: false }));
    
    stopPerformanceMonitoring();
    logStreamStop();
  }, []);

  const clearHistory = useCallback(() => {
    setState(prev => ({
      ...prev,
      updateHistory: [],
      latestUpdate: null
    }));
  }, []);

  // ============================================
  // Query Functions
  // ============================================

  const getUpdatesByAgent = useCallback((targetAgentId: string): AgentUpdate[] => {
    return state.updateHistory.filter(update => update.agentId === targetAgentId);
  }, [state.updateHistory]);

  const getLatestUpdateForAgent = useCallback((targetAgentId: string): AgentUpdate | null => {
    const updates = getUpdatesByAgent(targetAgentId);
    return updates.length > 0 ? updates[updates.length - 1] : null;
  }, [getUpdatesByAgent]);

  // ============================================
  // Performance Monitoring
  // ============================================

  const startPerformanceMonitoring = (): void => {
    performanceTimerRef.current = setInterval(() => {
      setState(prev => ({
        ...prev,
        streamMetrics: agentUpdateStream.getMetrics()
      }));
    }, 1000);
  };

  const stopPerformanceMonitoring = (): void => {
    if (performanceTimerRef.current) {
      clearInterval(performanceTimerRef.current);
      performanceTimerRef.current = null;
    }
  };

  // ============================================
  // Lifecycle Management
  // ============================================

  useEffect(() => {
    startStreaming();
    
    return () => {
      stopStreaming();
    };
  }, [startStreaming, stopStreaming]);

  // Auto-restart when agentId changes
  useEffect(() => {
    if (subscriptionIdRef.current) {
      stopStreaming();
      startStreaming();
    }
  }, [agentId]);

  // ============================================
  // Return Interface
  // ============================================

  return {
    state,
    controls: {
      startStreaming,
      stopStreaming,
      clearHistory,
      getUpdatesByAgent,
      getLatestUpdateForAgent
    }
  };
};

// ============================================
// Utility Functions
// ============================================

const createAgentFilter = (targetAgentId: string) => (update: AgentUpdate): boolean => {
  return update.agentId === targetAgentId;
};

const filterUpdatesForAgent = (updates: AgentUpdate[], agentId?: string): AgentUpdate[] => {
  if (!agentId) return updates;
  return updates.filter(update => update.agentId === agentId);
};

const mergeUpdatesWithHistory = (
  history: AgentUpdate[], 
  newUpdates: AgentUpdate[], 
  maxSize: number
): AgentUpdate[] => {
  const merged = [...history, ...newUpdates];
  
  // Keep only the most recent updates within size limit
  return merged.slice(-maxSize);
};

const logBatchProcessing = (batch: StreamBatch, filteredCount: number): void => {
  logger.debug('Processed agent update batch', undefined, {
    component: 'useAgentUpdates',
    action: 'batch_processed',
    metadata: {
      batchSize: batch.updates.length,
      filteredCount,
      frameId: batch.frameId
    }
  });
};

const logStreamStart = (): void => {
  logger.debug('Agent updates stream started', undefined, {
    component: 'useAgentUpdates',
    action: 'stream_started'
  });
};

const logStreamStop = (): void => {
  logger.debug('Agent updates stream stopped', undefined, {
    component: 'useAgentUpdates',
    action: 'stream_stopped'
  });
};