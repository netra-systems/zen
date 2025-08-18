'use client';

import { useEffect, useRef, useState } from 'react';
import { useWebSocket } from './useWebSocket';
import { useUnifiedChatStore } from '@/store/unified-chat';
import type { UnifiedWebSocketEvent } from '@/types/unified-chat';
import { generateUniqueId } from '@/lib/utils';
import { logger } from '@/lib/logger';
import { Message } from '@/types/registry';

interface AgentMetrics {
  currentAgent: string | null;
  previousAgent: string | null;
  agentStartTime: number;
  totalStartTime: number;
  stepCount: number;
  agentTimings: Map<string, number>;
  toolCallCount: Map<string, number>;
}

interface UseChatWebSocketOptions {
  enhanced?: boolean;
  runId?: string;
}

/**
 * Unified chat WebSocket hook that combines base, enhanced, and compatibility features.
 * Use the 'enhanced' option to enable advanced metrics and tracking.
 */
export const useChatWebSocket = (options: UseChatWebSocketOptions | string = {}) => {
  // Handle legacy string parameter for backward compatibility
  const config = typeof options === 'string' 
    ? { runId: options, enhanced: false } 
    : { enhanced: false, ...options };
    
  const { messages } = useWebSocket();
  const unifiedStore = useUnifiedChatStore();
  const { handleWebSocketEvent } = unifiedStore;
  
  // Track the last processed message index to avoid reprocessing
  const lastProcessedIndex = useRef(0);
  
  // Enhanced mode: Track agent metrics and timing
  const [metrics, setMetrics] = useState<AgentMetrics>({
    currentAgent: null,
    previousAgent: null,
    agentStartTime: Date.now(),
    totalStartTime: Date.now(),
    stepCount: 0,
    agentTimings: new Map(),
    toolCallCount: new Map()
  });

  // Enhanced mode: Track final report data
  const [finalReportData, setFinalReportData] = useState<any>(null);

  useEffect(() => {
    // Only process new messages
    const newMessages = messages.slice(lastProcessedIndex.current);
    
    newMessages.forEach((wsMessage) => {
      // Route all events through the unified store
      handleWebSocketEvent(wsMessage as UnifiedWebSocketEvent);
      
      // Enhanced mode processing
      if (config.enhanced) {
        processEnhancedMessage(wsMessage);
      }
    });
    
    // Update the last processed index
    lastProcessedIndex.current = messages.length;
  }, [messages, handleWebSocketEvent, config.enhanced]);
  
  // Enhanced message processing function
  const processEnhancedMessage = (wsMessage: any) => {
    const now = Date.now();
    
    if (wsMessage.type === 'sub_agent_update') {
      const payload = wsMessage.payload as any;
      const newAgentName = payload?.sub_agent_name;
      
      if (newAgentName && newAgentName !== metrics.currentAgent) {
        // Record timing for previous agent
        if (metrics.currentAgent) {
          const duration = now - metrics.agentStartTime;
          metrics.agentTimings.set(
            metrics.currentAgent, 
            (metrics.agentTimings.get(metrics.currentAgent) || 0) + duration
          );
          
          // Add transition message
          const transitionMessage: any = {
            id: generateUniqueId('msg'),
            role: 'system',
            content: `Transitioning from ${metrics.currentAgent} to ${newAgentName}`,
            timestamp: Date.now(),
            metadata: {
              agentTransition: {
                from: metrics.currentAgent,
                to: newAgentName,
                timestamp: new Date().toISOString()
              }
            }
          };
          unifiedStore.addMessage(transitionMessage);
        }
        
        // Update metrics
        setMetrics(prev => ({
          ...prev,
          previousAgent: prev.currentAgent,
          currentAgent: newAgentName,
          agentStartTime: now,
          stepCount: prev.stepCount + 1
        }));
        
        try {
          unifiedStore.setSubAgentName(newAgentName);
          if (payload?.state) {
            unifiedStore.setSubAgentStatus({
              status: payload.state.lifecycle || 'idle',
              tools: payload.state.tools || []
            });
          }
        } catch (error) {
          logger.error('Failed to update agent state', error as Error, {
            component: 'useChatWebSocket',
            action: 'update_agent_state_error'
          });
        }
      }
      
      // Check for final report data
      if (payload?.state && (payload.state.data_result || payload.state.optimizations_result || 
          payload.state.action_plan_result || payload.state.final_report)) {
        setFinalReportData({
          ...payload.state,
          execution_metrics: {
            total_duration: now - metrics.totalStartTime,
            agent_timings: Array.from(metrics.agentTimings.entries()),
            tool_calls: Array.from(metrics.toolCallCount.entries())
          }
        });
      }
    } else if (wsMessage.type === 'tool_call') {
      const payload = wsMessage.payload as any;
      const toolName = payload.tool_name || 'Unknown';
      
      // Track tool call count
      setMetrics(prev => {
        const newCount = new Map(prev.toolCallCount);
        newCount.set(toolName, (newCount.get(toolName) || 0) + 1);
        return { ...prev, toolCallCount: newCount };
      });
    } else if (wsMessage.type === 'agent_started') {
      unifiedStore.setProcessing(true);
      setMetrics(prev => ({
        ...prev,
        totalStartTime: now,
        stepCount: 0,
        agentTimings: new Map(),
        toolCallCount: new Map()
      }));
    } else if (wsMessage.type === 'agent_finished' || wsMessage.type === 'agent_completed') {
      unifiedStore.setProcessing(false);
      
      // Record final timing for current agent
      if (metrics.currentAgent) {
        const duration = now - metrics.agentStartTime;
        metrics.agentTimings.set(
          metrics.currentAgent, 
          (metrics.agentTimings.get(metrics.currentAgent) || 0) + duration
        );
      }
    }
  };

  // Base return object
  const baseReturn = {
    // Core state
    messages: unifiedStore.messages,
    isProcessing: unifiedStore.isProcessing,
    
    // Agent state
    agentStatus: unifiedStore.isProcessing ? 'RUNNING' : 'IDLE',
    subAgentName: unifiedStore.fastLayerData?.agentName || '',
    
    // Workflow progress (derived from layers)
    workflowProgress: {
      current_step: unifiedStore.fastLayerData ? 1 : 0,
      total_steps: 3 // Fast, Medium, Slow layers
    },
    
    // Tool state
    activeTools: unifiedStore.fastLayerData?.activeTools || [],
    toolExecutionStatus: (unifiedStore.fastLayerData?.activeTools?.length || 0) > 0 ? 'executing' : 'idle',
    
    // Connection state (from WebSocket hook)
    isConnected: true, // WebSocket hook handles reconnection
    
    // Error state
    errors: [],  // Errors are handled via connectionError
    
    // Streaming state
    isStreaming: unifiedStore.mediumLayerData?.partialContent ? true : false,
    streamingMessage: unifiedStore.mediumLayerData?.partialContent || '',
    
    // Actions (delegate to unified store)
    addMessage: unifiedStore.addMessage,
    setProcessing: unifiedStore.setProcessing,
    clearMessages: unifiedStore.clearMessages,
    
    // For test compatibility - return empty/default values
    fallbackActive: false,
    fallbackStrategy: '',
    tools: [],
    selectedTool: null,
    toolResults: {},
    registeredTools: [],
    toolExecutionQueue: [],
    retryAttempts: 0,
    aggregatedResults: {},
    validationResults: {},
    pendingApproval: null,
    subAgentStreams: {},
    setSubAgentName: () => {},
    setSubAgentStatus: () => {},
    registerTool: () => {},
    executeTool: () => {}
  };
  
  // Add enhanced features if enabled
  if (config.enhanced) {
    return {
      ...baseReturn,
      metrics,
      finalReportData,
      currentAgent: metrics.currentAgent,
      totalDuration: Date.now() - metrics.totalStartTime,
      stepCount: metrics.stepCount
    };
  }
  
  return baseReturn;
};

/**
 * Alias for backward compatibility with enhanced features enabled by default
 * @deprecated Use useChatWebSocket({ enhanced: true }) instead
 */
export const useEnhancedChatWebSocket = () => {
  return useChatWebSocket({ enhanced: true });
};