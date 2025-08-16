import { generateUniqueId } from '@/lib/utils';
import type {
  ChatMessage,
  AgentResult,
  FinalReport,
  AgentResultData,
  AgentMetrics
} from '@/types/unified-chat';
import type { WebSocketHandlerState, AgentExecution } from './websocketHandlers';

export const handleAgentCompleted = (
  event: any,
  state: WebSocketHandlerState,
  setState: (updates: any) => void
) => {
  const payload = event.payload;
  const agentName = payload.agent_id || payload.agent_type || 'Unknown Agent';
  const durationMs = payload.duration_ms || 0;
  const result = payload.result || {};
  const metrics = payload.metrics || {};
  
  const executedAgents = new Map(state.executedAgents);
  const execution = executedAgents.get(agentName);
  
  // Update execution status
  if (execution) {
    execution.status = 'completed';
    execution.endTime = Date.now();
    execution.result = result;
    executedAgents.set(agentName, execution);
  }
  
  // Include iteration in display name
  const iteration = state.agentIterations.get(agentName) || 1;
  const displayName = iteration > 1 ? `${agentName} (iteration ${iteration})` : agentName;
  
  const newAgentResult: AgentResult = {
    agentName: displayName,
    duration: durationMs,
    result: result as AgentResultData,
    metrics: metrics as AgentMetrics,
    iteration: payload.iteration || iteration
  };
  
  // Create agent completed message
  const durationInSeconds = durationMs > 0 ? (durationMs / 1000).toFixed(2) : '0.00';
  const completedMessage: ChatMessage = {
    id: generateUniqueId('agent-complete'),
    role: 'assistant',
    content: `✅ ${displayName} completed in ${durationInSeconds}s`,
    timestamp: Date.now(),
    metadata: {
      agentName: agentName,
      duration: durationMs
    }
  };
  state.addMessage(completedMessage);
  
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
  
  setState({
    slowLayerData: {
      completedAgents: updatedCompletedAgents,
      finalReport: currentSlow?.finalReport || null,
      totalDuration: currentSlow?.totalDuration || 0,
      metrics: currentSlow?.metrics || {
        total_duration_ms: 0,
        total_tokens: 0
      }
    },
    fastLayerData: state.fastLayerData
      ? { ...state.fastLayerData, activeTools: [] }
      : null,
    executedAgents
  });
};

export const handleFinalReport = (
  event: any,
  state: WebSocketHandlerState,
  setState: (updates: any) => void
) => {
  const finalReport: FinalReport = {
    report: event.payload.report,
    recommendations: event.payload.recommendations,
    actionPlan: event.payload.action_plan,
    agentMetrics: event.payload.agent_metrics,
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
  state.addMessage(reportMessage);
  
  setState({
    isProcessing: false,
    slowLayerData: {
      completedAgents: state.slowLayerData?.completedAgents || [],
      finalReport,
      totalDuration: event.payload.total_duration_ms,
      metrics: {
        total_tokens: 0,
        ...event.payload
      }
    },
    subAgentStatus: 'completed'
  });
  
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
  state.addMessage(finalMessage);
};

export const handleThreadRenamed = (
  event: any,
  state: WebSocketHandlerState,
  setState: (updates: any) => void
) => {
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
  
  setState({ messages: updatedMessages });
};

export const handleThreadLoaded = (
  event: any,
  state: WebSocketHandlerState,
  setState: (updates: any) => void
) => {
  if (event.payload.messages && Array.isArray(event.payload.messages)) {
    // Ensure messages are in correct ChatMessage format
    const formattedMessages: ChatMessage[] = event.payload.messages.map((msg: any) => ({
      id: msg.id || generateUniqueId('msg'),
      role: msg.role || 'assistant',
      content: msg.content || '',
      timestamp: typeof msg.timestamp === 'number' ? msg.timestamp : 
                typeof msg.created_at === 'number' ? msg.created_at * 1000 : Date.now(),
      threadId: event.payload.thread_id,
      metadata: msg.metadata
    }));
    
    setState({
      messages: formattedMessages,
      activeThreadId: event.payload.thread_id,
      isThreadLoading: false
    });
  }
};

export const handleError = (
  event: any,
  state: WebSocketHandlerState,
  setState: (updates: any) => void
) => {
  const payload = event.payload;
  const errorMessage = payload.error_message || 'An error occurred';
  const recoverable = payload.recoverable !== undefined ? payload.recoverable : true;
  const agentId = payload.agent_id || payload.agent_type || 'Agent';
  const errorCode = payload.error_code || 'unknown';
  
  setState({
    isProcessing: !recoverable ? false : state.isProcessing
  });
  
  // Add error message
  const errorChatMessage: ChatMessage = {
    id: generateUniqueId('error'),
    role: 'system',
    content: `❌ Error in ${agentId}: ${errorMessage}`,
    timestamp: Date.now(),
    metadata: {
      agentName: agentId,
      errorCode: errorCode,
      recoverable: recoverable
    }
  };
  state.addMessage(errorChatMessage);
};