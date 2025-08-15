import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { generateUniqueId } from '@/lib/utils';
import { WebSocketEventBuffer, WSEvent } from '@/lib/circular-buffer';
import { logger } from '@/lib/logger';
import type {
  UnifiedChatState,
  UnifiedWebSocketEvent,
  FastLayerData,
  MediumLayerData,
  SlowLayerData,
  ChatMessage,
  AgentResult,
  FinalReport,
} from '@/types/unified-chat';

// Agent execution tracking for deduplication
interface AgentExecution {
  name: string;
  iteration: number;
  status: 'running' | 'completed' | 'failed';
  startTime: number;
  endTime?: number;
  result?: any;
}

const initialState = {
  // Layer data
  fastLayerData: null,
  mediumLayerData: null,
  slowLayerData: null,
  
  // Processing state
  isProcessing: false,
  currentRunId: null,
  
  // Thread management
  activeThreadId: null,
  threads: new Map(),
  
  // Message history
  messages: [],
  
  // WebSocket connection
  isConnected: false,
  connectionError: null,
  
  // Agent deduplication
  executedAgents: new Map<string, AgentExecution>(),
  agentIterations: new Map<string, number>(),
  
  // WebSocket event debugging
  wsEventBuffer: new WebSocketEventBuffer(1000),
  
  // Performance metrics
  performanceMetrics: {
    renderCount: 0,
    lastRenderTime: 0,
    averageResponseTime: 0,
    memoryUsage: 0
  },
  
  // Sub-agent status (for compatibility with old chatStore)
  subAgentName: null,
  subAgentStatus: null,
  subAgentTools: [],
  subAgentProgress: null,
  subAgentError: null,
  subAgentDescription: null,
  subAgentExecutionTime: null,
  queuedSubAgents: []
};

export const useUnifiedChatStore = create<UnifiedChatState>()(
  devtools(
    (set, get) => ({
      ...initialState,
      
      // Update fast layer data
      updateFastLayer: (data) => set((state) => ({
        fastLayerData: state.fastLayerData 
          ? { ...state.fastLayerData, ...data }
          : (data as FastLayerData)
      }), false, 'updateFastLayer'),
      
      // Update medium layer data
      updateMediumLayer: (data) => set((state) => {
        const currentData = state.mediumLayerData;
        
        // If we have partial content updates, accumulate them
        if (data.partialContent && currentData?.partialContent) {
          return {
            mediumLayerData: {
              ...currentData,
              ...data,
              // Accumulate partial content with deduplication
              partialContent: (() => {
                // If new content already contains old content, use new only
                if (data.partialContent.includes(currentData.partialContent)) return data.partialContent;
                // Otherwise append new to old
                return currentData.partialContent + data.partialContent;
              })()
            }
          };
        }
        
        return {
          mediumLayerData: currentData
            ? { ...currentData, ...data }
            : (data as MediumLayerData)
        };
      }, false, 'updateMediumLayer'),
      
      // Update slow layer data
      updateSlowLayer: (data) => set((state) => {
        const currentData = state.slowLayerData;
        
        // Handle adding completed agents
        if (data.completedAgents && currentData?.completedAgents) {
          return {
            slowLayerData: {
              ...currentData,
              ...data,
              completedAgents: [...currentData.completedAgents, ...data.completedAgents]
            }
          };
        }
        
        return {
          slowLayerData: currentData
            ? { ...currentData, ...data }
            : (data as SlowLayerData)
        };
      }, false, 'updateSlowLayer'),
      
      // Handle WebSocket events
      handleWebSocketEvent: (event: UnifiedWebSocketEvent) => {
        const state = get();
        
        // Buffer event for debugging
        const wsEvent: WSEvent = {
          type: event.type,
          payload: event.payload,
          timestamp: Date.now(),
          threadId: state.activeThreadId || undefined,
          runId: (event.payload as any)?.run_id,
          agentName: (event.payload as any)?.agent_name
        };
        state.wsEventBuffer.push(wsEvent);
        
        // Debug logging to track layer updates
        logger.debug('WebSocket Event received', {
          component: 'UnifiedChatStore',
          action: 'websocket_event',
          metadata: {
            event_type: event.type,
            payload: event.payload,
            has_fast_layer: !!state.fastLayerData,
            has_medium_layer: !!state.mediumLayerData,
            has_slow_layer: !!state.slowLayerData
          }
        });
        
        switch (event.type) {
          case 'agent_started': {
            const agentName = event.payload.agent_name;
            const executedAgents = new Map(state.executedAgents);
            const agentIterations = new Map(state.agentIterations);
            
            // Track agent iteration
            const currentIteration = (agentIterations.get(agentName) || 0) + 1;
            agentIterations.set(agentName, currentIteration);
            
            // Track execution
            executedAgents.set(agentName, {
              name: agentName,
              iteration: currentIteration,
              status: 'running',
              startTime: Date.now()
            });
            
            // Display agent name with iteration if > 1
            const displayName = currentIteration > 1 
              ? `${agentName} (${currentIteration})` 
              : agentName;
            
            // Create agent started message
            const startMessage: ChatMessage = {
              id: generateUniqueId('agent-start'),
              role: 'assistant',
              content: `🚀 Starting ${displayName}...`,
              timestamp: Date.now(),
              metadata: {
                agentName: agentName,
                runId: event.payload.run_id
              }
            };
            get().addMessage(startMessage);
            
            set({
              isProcessing: true,
              currentRunId: event.payload.run_id,
              fastLayerData: {
                agentName: displayName,
                timestamp: event.payload.timestamp,
                runId: event.payload.run_id,
                activeTools: []
              },
              // Don't reset layers if same agent reruns
              mediumLayerData: currentIteration > 1 ? state.mediumLayerData : null,
              slowLayerData: currentIteration > 1 ? state.slowLayerData : null,
              executedAgents,
              agentIterations,
              // Update sub-agent status for compatibility
              subAgentName: displayName,
              subAgentStatus: 'running'
            }, false, 'agent_started');
            break;
          }
            
          case 'tool_executing':
            if (state.fastLayerData) {
              const activeTools = state.fastLayerData.activeTools || [];
              const toolName = event.payload.tool_name;
              
              // Add tool if not already active
              if (!activeTools.includes(toolName)) {
                set({
                  fastLayerData: {
                    ...state.fastLayerData,
                    activeTools: [...activeTools, toolName]
                  }
                }, false, 'tool_executing');
              }
            }
            break;
            
          case 'agent_thinking': {
            // Create thinking message for display
            const thinkingMessage: ChatMessage = {
              id: generateUniqueId('thinking'),
              role: 'assistant',
              content: `🤔 ${event.payload.agent_name}: ${event.payload.thought}`,
              timestamp: Date.now(),
              metadata: {
                agentName: event.payload.agent_name
              }
            };
            get().addMessage(thinkingMessage);
            
            set({
              mediumLayerData: {
                thought: event.payload.thought,
                partialContent: state.mediumLayerData?.partialContent || '',
                stepNumber: event.payload.step_number,
                totalSteps: event.payload.total_steps,
                agentName: event.payload.agent_name
              }
            }, false, 'agent_thinking');
            break;
          }
            
          case 'partial_result': {
            const currentMedium = state.mediumLayerData;
            
            // Create partial result message for display
            if (event.payload.content) {
              const partialMessage: ChatMessage = {
                id: generateUniqueId('partial'),
                role: 'assistant',
                content: event.payload.content,
                timestamp: Date.now(),
                metadata: {
                  agentName: event.payload.agent_name
                }
              };
              get().addMessage(partialMessage);
            }
            
            set({
              mediumLayerData: {
                thought: currentMedium?.thought || '',
                partialContent: event.payload.is_complete
                  ? event.payload.content
                  : (currentMedium?.partialContent || '') + event.payload.content,
                stepNumber: currentMedium?.stepNumber || 0,
                totalSteps: currentMedium?.totalSteps || 0,
                agentName: event.payload.agent_name
              }
            }, false, 'partial_result');
            break;
          }
            
          case 'agent_completed': {
            const agentName = event.payload.agent_name;
            const executedAgents = new Map(state.executedAgents);
            const execution = executedAgents.get(agentName);
            
            // Update execution status
            if (execution) {
              execution.status = 'completed';
              execution.endTime = Date.now();
              execution.result = event.payload.result;
              executedAgents.set(agentName, execution);
            }
            
            // Include iteration in display name
            const iteration = state.agentIterations.get(agentName) || 1;
            const displayName = iteration > 1 ? `${agentName} (iteration ${iteration})` : agentName;
            
            const newAgentResult: AgentResult = {
              agentName: displayName,
              duration: event.payload.duration_ms,
              result: event.payload.result,
              metrics: event.payload.metrics,
              iteration: (event.payload as any).iteration || iteration
            };
            
            // Create agent completed message
            const completedMessage: ChatMessage = {
              id: generateUniqueId('agent-complete'),
              role: 'assistant',
              content: `✅ ${displayName} completed in ${(event.payload.duration_ms / 1000).toFixed(2)}s`,
              timestamp: Date.now(),
              metadata: {
                agentName: agentName,
                duration: event.payload.duration_ms
              }
            };
            get().addMessage(completedMessage);
            
            const currentSlow = state.slowLayerData;
            
            // Check if this agent already exists in completed agents (deduplication)
            const existingAgentIndex = currentSlow?.completedAgents?.findIndex(
              agent => agent.agentName.startsWith(agentName)
            ) ?? -1;
            
            let updatedCompletedAgents;
            if (existingAgentIndex >= 0 && currentSlow?.completedAgents) {
              // Update existing agent result
              updatedCompletedAgents = [...currentSlow.completedAgents];
              updatedCompletedAgents[existingAgentIndex] = newAgentResult;
            } else {
              // Add new agent result
              updatedCompletedAgents = currentSlow?.completedAgents
                ? [...currentSlow.completedAgents, newAgentResult]
                : [newAgentResult];
            }
            
            set({
              slowLayerData: {
                completedAgents: updatedCompletedAgents,
                finalReport: currentSlow?.finalReport || null,
                totalDuration: currentSlow?.totalDuration || 0,
                metrics: currentSlow?.metrics || {
                  total_duration_ms: 0,
                  total_tokens: 0
                }
              },
              // Remove completed tool from active tools
              fastLayerData: state.fastLayerData
                ? { ...state.fastLayerData, activeTools: [] }
                : null,
              executedAgents
            }, false, 'agent_completed');
            break;
          }
            
          case 'thread_renamed':
            // Handle thread renaming event
            set((state) => {
              // Update messages if they contain thread info
              const updatedMessages = state.messages.map(msg => {
                if (msg.threadId === event.payload.thread_id) {
                  return { 
                    ...msg, 
                    threadTitle: event.payload.new_title 
                  };
                }
                return msg;
              });
              
              return { messages: updatedMessages };
            }, false, 'thread_renamed');
            break;
            
          case 'thread_loaded':
            // Handle thread loading event - load messages from thread
            if (event.payload.messages && Array.isArray(event.payload.messages)) {
              set({
                messages: event.payload.messages,
                activeThreadId: event.payload.thread_id
              }, false, 'thread_loaded');
            }
            break;
            
          case 'final_report':
            const finalReport: FinalReport = {
              report: event.payload.report,
              recommendations: event.payload.recommendations,
              actionPlan: event.payload.action_plan,
              agentMetrics: event.payload.agent_metrics,
              // Add new comprehensive reporting fields
              executive_summary: event.payload.executive_summary,
              cost_analysis: event.payload.cost_analysis,
              performance_comparison: event.payload.performance_comparison,
              confidence_scores: event.payload.confidence_scores,
              technical_details: event.payload.technical_details
            };
            
            // Create final report message
            const reportMessage: ChatMessage = {
              id: generateUniqueId('final-report'),
              role: 'assistant',
              content: event.payload.executive_summary || 
                `📊 Analysis complete! Found ${event.payload.recommendations?.length || 0} recommendations.`,
              timestamp: Date.now(),
              metadata: {
                runId: state.currentRunId || undefined
              }
            };
            get().addMessage(reportMessage);
            
            set({
              isProcessing: false,
              slowLayerData: {
                completedAgents: state.slowLayerData?.completedAgents || [],
                finalReport,
                totalDuration: event.payload.total_duration_ms,
                metrics: {
                  total_tokens: 0, // Will be populated from agent_metrics
                  ...event.payload
                }
              },
              // Clear sub-agent status when processing is complete
              subAgentStatus: 'completed'
            }, false, 'final_report');
            
            // Add final message to history
            const finalMessage: ChatMessage = {
              id: generateUniqueId('msg'),
              role: 'assistant',
              content: 'Analysis complete. View the results above.',
              timestamp: Date.now(),
              metadata: {
                runId: state.currentRunId || undefined,
                duration: event.payload.total_duration_ms
              }
            };
            get().addMessage(finalMessage);
            break;
            
          case 'error':
            set({
              isProcessing: !event.payload.recoverable ? false : state.isProcessing
            }, false, 'error');
            
            // Add error message
            const errorMessage: ChatMessage = {
              id: generateUniqueId('error'),
              role: 'system',
              content: event.payload.error_message,
              timestamp: Date.now(),
              metadata: {
                agentName: event.payload.agent_name
              }
            };
            get().addMessage(errorMessage);
            break;
        }
      },
      
      // Reset all layers
      resetLayers: () => set({
        fastLayerData: null,
        mediumLayerData: null,
        slowLayerData: null,
        currentRunId: null,
        isProcessing: false,
        messages: [],
        // Reset sub-agent status
        subAgentName: null,
        subAgentStatus: null,
        subAgentTools: [],
        subAgentProgress: null,
        subAgentError: null,
        subAgentDescription: null,
        subAgentExecutionTime: null,
        queuedSubAgents: []
      }, false, 'resetLayers'),
      
      // Add message to history
      addMessage: (message) => set((state) => ({
        messages: [...state.messages, message]
      }), false, 'addMessage'),
      
      // Set processing state
      setProcessing: (isProcessing) => set({ isProcessing }, false, 'setProcessing'),
      
      // Set connection status
      setConnectionStatus: (isConnected, error) => set({
        isConnected,
        connectionError: error || null
      }, false, 'setConnectionStatus'),
      
      // Thread management
      setActiveThread: (threadId) => set({ 
        activeThreadId: threadId 
      }, false, 'setActiveThread'),
      
      clearMessages: () => set({ 
        messages: [] 
      }, false, 'clearMessages'),
      
      loadMessages: (messages) => set({ 
        messages 
      }, false, 'loadMessages'),
      
      // Sub-agent actions (for compatibility with old chatStore)
      setSubAgentName: (name) => set((state) => ({
        subAgentName: name,
        // Also update fastLayerData if it exists for consistency
        fastLayerData: state.fastLayerData
          ? { ...state.fastLayerData, agentName: name || '' }
          : state.fastLayerData
      }), false, 'setSubAgentName'),
      
      setSubAgentStatus: (statusData) => set({
        subAgentStatus: statusData?.status || null,
        subAgentTools: statusData?.tools || [],
        subAgentProgress: statusData?.progress || null,
        subAgentError: statusData?.error || null,
        subAgentDescription: statusData?.description || null,
        subAgentExecutionTime: statusData?.executionTime || null
      }, false, 'setSubAgentStatus'),
    }),
    {
      name: 'unified-chat-store',
    }
  )
);