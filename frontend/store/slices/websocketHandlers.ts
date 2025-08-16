import { generateUniqueId } from '@/lib/utils';
import { logger } from '@/lib/logger';
import type {
  UnifiedWebSocketEvent,
  ChatMessage,
  AgentResult,
  FinalReport,
  AgentResultData,
  AgentMetrics
} from '@/types/unified-chat';
import type { WSEvent } from '@/lib/circular-buffer';
import type { AgentExecution } from './types';

// Combined state interface for handlers
export interface WebSocketHandlerState {
  addMessage: (message: ChatMessage) => void;
  updateFastLayer: (data: any) => void;
  updateMediumLayer: (data: any) => void;
  updateSlowLayer: (data: any) => void;
  setProcessing: (isProcessing: boolean) => void;
  setThreadLoading: (isLoading: boolean) => void;
  fastLayerData: any;
  mediumLayerData: any;
  slowLayerData: any;
  isProcessing: boolean;
  currentRunId: string | null;
  activeThreadId: string | null;
  messages: ChatMessage[];
  executedAgents: Map<string, AgentExecution>;
  agentIterations: Map<string, number>;
  wsEventBuffer: any;
}

export const handleAgentStarted = (
  event: any,
  state: WebSocketHandlerState,
  setState: (updates: any) => void
) => {
  const payload = event.payload;
  const agentId = payload.agent_id || payload.agent_type || `agent-${payload.run_id}` || 'unknown';
  const agentType = payload.agent_type || payload.agent_id || 'generic';
  const timestamp = payload.timestamp ? 
    (typeof payload.timestamp === 'string' ? Date.parse(payload.timestamp) : payload.timestamp) : 
    Date.now();
  const runId = payload.run_id || generateUniqueId('run');
  
  const agentName = agentId;
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
      runId: runId
    }
  };
  state.addMessage(startMessage);
  
  setState({
    isProcessing: true,
    currentRunId: runId,
    fastLayerData: {
      agentName: displayName,
      timestamp: timestamp,
      runId: runId,
      activeTools: []
    },
    mediumLayerData: currentIteration > 1 ? state.mediumLayerData : null,
    slowLayerData: currentIteration > 1 ? state.slowLayerData : null,
    executedAgents,
    agentIterations,
    subAgentName: displayName,
    subAgentStatus: 'running'
  });
};

export const handleToolExecuting = (
  event: any,
  state: WebSocketHandlerState
) => {
  const payload = event.payload;
  const toolName = payload.tool_name || 'unknown-tool';
  const timestamp = payload.timestamp || Date.now();
  
  if (state.fastLayerData) {
    const activeTools = state.fastLayerData.activeTools || [];
    
    // Add tool if not already active
    if (!activeTools.includes(toolName)) {
      state.updateFastLayer({
        activeTools: [...activeTools, toolName],
        timestamp: timestamp
      });
    }
  }
};

export const handleAgentThinking = (
  event: any,
  state: WebSocketHandlerState
) => {
  const payload = event.payload;
  const thought = payload.thought || 'Processing...';
  const agentId = payload.agent_id || payload.agent_type || 'Agent';
  const stepNumber = payload.step_number || 0;
  const totalSteps = payload.total_steps || 0;
  
  // Create thinking message for display
  const thinkingMessage: ChatMessage = {
    id: generateUniqueId('thinking'),
    role: 'assistant',
    content: `🤔 ${agentId}: ${thought}`,
    timestamp: Date.now(),
    metadata: {
      agentName: agentId
    }
  };
  state.addMessage(thinkingMessage);
  
  state.updateMediumLayer({
    thought: thought,
    partialContent: state.mediumLayerData?.partialContent || '',
    stepNumber: stepNumber,
    totalSteps: totalSteps,
    agentName: agentId
  });
};

export const handlePartialResult = (
  event: any,
  state: WebSocketHandlerState
) => {
  const payload = event.payload;
  const content = payload.content || '';
  const agentId = payload.agent_id || payload.agent_type || 'Agent';
  const isComplete = payload.is_complete || false;
  
  const currentMedium = state.mediumLayerData;
  
  // Create partial result message for display
  if (content) {
    const partialMessage: ChatMessage = {
      id: generateUniqueId('partial'),
      role: 'assistant',
      content: content,
      timestamp: Date.now(),
      metadata: {
        agentName: agentId
      }
    };
    state.addMessage(partialMessage);
  }
  
  state.updateMediumLayer({
    thought: currentMedium?.thought || '',
    partialContent: isComplete
      ? content
      : (currentMedium?.partialContent || '') + content,
    stepNumber: currentMedium?.stepNumber || 0,
    totalSteps: currentMedium?.totalSteps || 0,
    agentName: agentId
  });
};