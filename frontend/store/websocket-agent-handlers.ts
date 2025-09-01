// Agent-specific WebSocket event handlers - Modular 25-line functions
// Handles agent start, complete, thinking events

import { generateUniqueId } from '@/lib/utils';
import { 
  generateAgentDisplayName,
  createAgentExecution,
  completeAgentExecution,
  deduplicateAgentResults
} from '@/utils/agentTracker';
import { mapEventPayload } from '@/utils/event-payload-mapper';
import { parseTimestamp } from './websocket-event-handlers-core';
import { cleanupToolsOnAgentComplete } from './websocket-tool-handlers-enhanced';
import { MessageFormatterService } from '@/services/messageFormatter';
import type { 
  UnifiedWebSocketEvent,
  ChatMessage,
  FastLayerData,
  MediumLayerData
} from '@/types/websocket-event-types';
import type { 
  AgentResult,
  AgentMetrics,
  AgentResultData
} from '@/types/layer-types';
import type { UnifiedChatState } from '@/types/store-types';

/**
 * Extracts agent started data from payload
 */
export const extractAgentStartedData = (payload: any) => {
  const mappedPayload = mapEventPayload('agent_started', payload);
  const agentId = mappedPayload.agent_id || `agent-${mappedPayload.run_id}` || 'unknown';
  const timestamp = mappedPayload.timestamp ? parseTimestamp(mappedPayload.timestamp) : Date.now();
  const runId = mappedPayload.run_id || generateUniqueId('run');
  return { agentId, timestamp, runId };
};

/**
 * Processes agent iteration tracking
 */
export const processAgentIteration = (
  agentData: { agentId: string },
  state: UnifiedChatState
) => {
  const executedAgents = new Map(state.executedAgents);
  const agentIterations = new Map(state.agentIterations);
  const currentIteration = (agentIterations.get(agentData.agentId) || 0) + 1;
  const displayName = generateAgentDisplayName(agentData.agentId, currentIteration);
  
  agentIterations.set(agentData.agentId, currentIteration);
  executedAgents.set(agentData.agentId, createAgentExecution(agentData.agentId, currentIteration));
  
  return { displayName, executedAgents, agentIterations };
};

/**
 * Creates agent started message for chat with formatting
 */
export const createAgentStartedMessage = (displayName: string, runId: string, get: () => UnifiedChatState): void => {
  const baseMessage: ChatMessage = {
    id: generateUniqueId('agent-start'),
    role: 'assistant',
    content: `🚀 Starting ${displayName}...`,
    timestamp: Date.now(),
    metadata: { agentName: displayName, runId }
  };
  const enrichedMessage = MessageFormatterService.enrich(baseMessage);
  get().addMessage(enrichedMessage);
};

/**
 * Creates fast layer data for agent started
 */
export const createFastLayerData = (displayName: string, agentData: any): FastLayerData => ({
  agentName: displayName,
  timestamp: agentData.timestamp,
  runId: agentData.runId,
  activeTools: []
});

/**
 * Updates state when agent starts
 */
export const updateAgentStartedState = (
  displayName: string,
  agentData: any,
  executedAgents: Map<string, any>,
  agentIterations: Map<string, number>,
  set: (partial: Partial<UnifiedChatState>) => void,
  state: UnifiedChatState
): void => {
  const currentIteration = agentIterations.get(agentData.agentId) || 1;
  set({
    isProcessing: true,
    currentRunId: agentData.runId,
    fastLayerData: createFastLayerData(displayName, agentData),
    mediumLayerData: currentIteration > 1 ? state.mediumLayerData : null,
    slowLayerData: currentIteration > 1 ? state.slowLayerData : null,
    executedAgents,
    agentIterations,
    subAgentName: displayName,
    subAgentStatus: 'running'
  });
};

/**
 * Handles agent started event
 */
export const handleAgentStarted = (
  event: UnifiedWebSocketEvent,
  state: UnifiedChatState,
  set: (partial: Partial<UnifiedChatState>) => void,
  get: () => UnifiedChatState
): void => {
  const agentData = extractAgentStartedData(event.payload as any);
  const { displayName, executedAgents, agentIterations } = processAgentIteration(agentData, state);
  createAgentStartedMessage(displayName, agentData.runId, get);
  updateAgentStartedState(displayName, agentData, executedAgents, agentIterations, set, state);
};

/**
 * Extracts agent thinking data from payload
 */
export const extractThinkingData = (payload: any) => {
  const mappedPayload = mapEventPayload('agent_thinking', payload);
  return {
    thought: mappedPayload.thought || 'Processing...',
    agentId: mappedPayload.agent_id || 'Agent',
    stepNumber: mappedPayload.step_number || 0,
    totalSteps: mappedPayload.total_steps || 0
  };
};

/**
 * Creates thinking message for chat with formatting
 */
export const createThinkingMessage = (thinkingData: any, get: () => UnifiedChatState): void => {
  const baseMessage: ChatMessage = {
    id: generateUniqueId('thinking'),
    role: 'assistant',
    content: `🤔 ${thinkingData.agentId}: ${thinkingData.thought}`,
    timestamp: Date.now(),
    metadata: { agentName: thinkingData.agentId }
  };
  const enrichedMessage = MessageFormatterService.enrich(baseMessage);
  get().addMessage(enrichedMessage);
};

/**
 * Updates medium layer with thinking data
 */
export const updateMediumLayerWithThinking = (
  thinkingData: any,
  state: UnifiedChatState,
  set: (partial: Partial<UnifiedChatState>) => void
): void => {
  const mediumLayerData: MediumLayerData = {
    thought: thinkingData.thought,
    partialContent: state.mediumLayerData?.partialContent || '',
    stepNumber: thinkingData.stepNumber,
    totalSteps: thinkingData.totalSteps,
    agentName: thinkingData.agentId
  };
  set({ mediumLayerData });
};

/**
 * Handles agent thinking event
 */
export const handleAgentThinking = (
  event: UnifiedWebSocketEvent,
  state: UnifiedChatState,
  set: (partial: Partial<UnifiedChatState>) => void,
  get: () => UnifiedChatState
): void => {
  const thinkingData = extractThinkingData(event.payload as any);
  createThinkingMessage(thinkingData, get);
  updateMediumLayerWithThinking(thinkingData, state, set);
};

/**
 * Extracts agent completed data from payload
 */
export const extractAgentCompletedData = (payload: any) => {
  const mappedPayload = mapEventPayload('agent_completed', payload);
  const agentId = mappedPayload.agent_id || 'unknown';
  const durationMs = mappedPayload.duration_ms || 0;
  const result = mappedPayload.result || {};
  const metrics = mappedPayload.metrics || {};
  const iteration = mappedPayload.iteration || 1;
  return { agentId, durationMs, result, metrics, iteration };
};

/**
 * Updates agent execution when completed
 */
export const updateAgentExecution = (
  agentData: { agentId: string; result: any },
  state: UnifiedChatState
) => {
  const executedAgents = new Map(state.executedAgents);
  const execution = executedAgents.get(agentData.agentId);
  const iteration = state.agentIterations.get(agentData.agentId) || 1;
  const displayName = generateAgentDisplayName(agentData.agentId, iteration);
  
  if (execution) {
    const completed = completeAgentExecution(execution, agentData.result);
    executedAgents.set(agentData.agentId, completed);
  }
  
  return { displayName, executedAgents };
};

/**
 * Creates agent completed message for chat with formatting
 */
export const createAgentCompletedMessage = (
  displayName: string,
  agentData: { durationMs: number },
  get: () => UnifiedChatState
): void => {
  const durationInSeconds = agentData.durationMs > 0 ? (agentData.durationMs / 1000).toFixed(2) : '0.00';
  const baseMessage: ChatMessage = {
    id: generateUniqueId('agent-complete'),
    role: 'assistant',
    content: `✅ ${displayName} completed in ${durationInSeconds}s`,
    timestamp: Date.now(),
    metadata: { agentName: displayName, duration: agentData.durationMs }
  };
  const enrichedMessage = MessageFormatterService.enrich(baseMessage);
  get().addMessage(enrichedMessage);
};

/**
 * Updates slow layer with completed agent
 */
export const updateSlowLayerWithCompletedAgent = (
  displayName: string,
  agentData: any,
  state: UnifiedChatState,
  set: (partial: Partial<UnifiedChatState>) => void
): void => {
  const newAgentResult = createCompletedAgentResult(displayName, agentData, state);
  updateSlowLayerWithAgentResult(newAgentResult, agentData, state, set);
};

/**
 * Handles agent completed event
 */
export const handleAgentCompleted = (
  event: UnifiedWebSocketEvent,
  state: UnifiedChatState,
  set: (partial: Partial<UnifiedChatState>) => void,
  get: () => UnifiedChatState
): void => {
  const agentData = extractAgentCompletedData(event.payload as any);
  const { displayName, executedAgents } = updateAgentExecution(agentData, state);
  createAgentCompletedMessage(displayName, agentData, get);
  updateSlowLayerWithCompletedAgent(displayName, agentData, state, set);
  cleanupToolsOnAgentComplete(state.fastLayerData, set);
};

/**
 * Extracts agent response data from payload
 */
export const extractAgentResponseData = (payload: any) => {
  const content = payload.content || payload.message || payload.data?.content || payload.data?.message || '';
  const threadId = payload.thread_id || payload.threadId;
  const userId = payload.user_id || payload.userId;
  const timestamp = payload.timestamp ? parseTimestamp(payload.timestamp) : Date.now();
  const agentData = payload.data || {};
  return { content, threadId, userId, timestamp, agentData };
};

/**
 * Creates agent response message for chat with formatting
 */
export const createAgentResponseMessage = (
  responseData: any,
  get: () => UnifiedChatState
): void => {
  if (!responseData.content) {
    console.warn('Agent response missing content:', responseData);
    return;
  }
  
  const baseMessage: ChatMessage = {
    id: generateUniqueId('agent-resp'),
    role: 'assistant',
    content: responseData.content,
    timestamp: responseData.timestamp,
    metadata: {
      source: 'agent_response',
      threadId: responseData.threadId,
      userId: responseData.userId,
      ...responseData.agentData
    }
  };
  const enrichedMessage = MessageFormatterService.enrich(baseMessage);
  get().addMessage(enrichedMessage);
};

/**
 * Handles agent response event
 */
export const handleAgentResponse = (
  event: UnifiedWebSocketEvent,
  state: UnifiedChatState,
  set: (partial: Partial<UnifiedChatState>) => void,
  get: () => UnifiedChatState
): void => {
  const responseData = extractAgentResponseData(event.payload as any);
  createAgentResponseMessage(responseData, get);
};

// Helper functions for agent completion (≤8 lines each)
const createCompletedAgentResult = (
  displayName: string,
  agentData: any,
  state: UnifiedChatState
): AgentResult => {
  const iteration = state.agentIterations.get(agentData.agentId) || 1;
  return {
    agentName: displayName,
    duration: agentData.durationMs,
    result: agentData.result as AgentResultData,
    metrics: agentData.metrics as AgentMetrics,
    iteration
  };
};

const updateSlowLayerWithAgentResult = (
  newAgentResult: AgentResult,
  agentData: any,
  state: UnifiedChatState,
  set: (partial: Partial<UnifiedChatState>) => void
): void => {
  const currentSlow = state.slowLayerData;
  const updatedCompletedAgents = deduplicateAgentResults(currentSlow?.completedAgents, newAgentResult, agentData.agentId);
  
  set({
    slowLayerData: createUpdatedSlowLayerData(currentSlow, updatedCompletedAgents),
    fastLayerData: state.fastLayerData ? { ...state.fastLayerData, activeTools: [] } : null,
    executedAgents: updateAgentExecution(agentData, state).executedAgents
  });
};

const createUpdatedSlowLayerData = (currentSlow: any, updatedCompletedAgents: any) => ({
  completedAgents: updatedCompletedAgents,
  finalReport: currentSlow?.finalReport || null,
  totalDuration: currentSlow?.totalDuration || 0,
  metrics: currentSlow?.metrics || { total_duration_ms: 0, total_tokens: 0 }
});