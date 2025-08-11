import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
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

const initialState = {
  // Layer data
  fastLayerData: null,
  mediumLayerData: null,
  slowLayerData: null,
  
  // Processing state
  isProcessing: false,
  currentRunId: null,
  
  // Message history
  messages: [],
  
  // WebSocket connection
  isConnected: false,
  connectionError: null,
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
              // Accumulate partial content rather than replace
              partialContent: data.partialContent.startsWith(currentData.partialContent)
                ? data.partialContent
                : currentData.partialContent + data.partialContent
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
        
        switch (event.type) {
          case 'agent_started':
            set({
              isProcessing: true,
              currentRunId: event.payload.run_id,
              fastLayerData: {
                agentName: event.payload.agent_name,
                timestamp: event.payload.timestamp,
                runId: event.payload.run_id,
                activeTools: []
              },
              // Reset medium and slow layers for new run
              mediumLayerData: null,
              slowLayerData: null
            }, false, 'agent_started');
            break;
            
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
            
          case 'agent_thinking':
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
            
          case 'partial_result':
            const currentMedium = state.mediumLayerData;
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
            
          case 'agent_completed':
            const newAgentResult: AgentResult = {
              agentName: event.payload.agent_name,
              duration: event.payload.duration_ms,
              result: event.payload.result,
              metrics: event.payload.metrics
            };
            
            const currentSlow = state.slowLayerData;
            set({
              slowLayerData: {
                completedAgents: currentSlow?.completedAgents
                  ? [...currentSlow.completedAgents, newAgentResult]
                  : [newAgentResult],
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
                : null
            }, false, 'agent_completed');
            break;
            
          case 'final_report':
            const finalReport: FinalReport = {
              report: event.payload.report,
              recommendations: event.payload.recommendations,
              actionPlan: event.payload.action_plan,
              agentMetrics: event.payload.agent_metrics
            };
            
            set({
              isProcessing: false,
              slowLayerData: {
                completedAgents: state.slowLayerData?.completedAgents || [],
                finalReport,
                totalDuration: event.payload.total_duration_ms,
                metrics: {
                  total_duration_ms: event.payload.total_duration_ms,
                  total_tokens: 0, // Will be populated from agent_metrics
                  ...event.payload
                }
              }
            }, false, 'final_report');
            
            // Add final message to history
            const finalMessage: ChatMessage = {
              id: `msg_${Date.now()}`,
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
              id: `error_${Date.now()}`,
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
        messages: []
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
    }),
    {
      name: 'unified-chat-store',
    }
  )
);