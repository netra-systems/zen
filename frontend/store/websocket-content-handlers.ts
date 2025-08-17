// Content-specific WebSocket event handlers - Modular 8-line functions
// Handles partial results, final reports, streaming content

import { generateUniqueId } from '@/lib/utils';
import { mapEventPayload } from '@/utils/event-payload-mapper';
import type { 
  UnifiedWebSocketEvent,
  MediumLayerData,
  FinalReport
} from '@/types/websocket-event-types';
import type { ChatMessage } from '@/types/chat';
import type { UnifiedChatState } from '@/types/store-types';

/**
 * Extracts partial result data from payload
 */
export const extractPartialResultData = (payload: any) => {
  const mappedPayload = mapEventPayload('partial_result', payload);
  return {
    content: mappedPayload.content || '',
    agentId: mappedPayload.agent_id || 'Agent',
    isComplete: mappedPayload.is_complete || false
  };
};

/**
 * Creates partial result message for chat
 */
export const createPartialResultMessage = (resultData: any, get: () => UnifiedChatState): void => {
  const message: ChatMessage = {
    id: generateUniqueId('partial'),
    role: 'assistant',
    content: resultData.content,
    timestamp: Date.now(),
    metadata: { agentName: resultData.agentId }
  };
  get().addMessage(message);
};

/**
 * Calculates accumulated partial content
 */
export const calculatePartialContent = (resultData: any, currentMedium: any): string => {
  if (resultData.isComplete) return resultData.content;
  return (currentMedium?.partialContent || '') + resultData.content;
};

/**
 * Updates medium layer with partial content
 */
export const updateMediumLayerWithPartialContent = (
  resultData: any,
  state: UnifiedChatState,
  set: (partial: Partial<UnifiedChatState>) => void
): void => {
  const currentMedium = state.mediumLayerData;
  const mediumLayerData: MediumLayerData = {
    thought: currentMedium?.thought || '',
    partialContent: calculatePartialContent(resultData, currentMedium),
    stepNumber: currentMedium?.stepNumber || 0,
    totalSteps: currentMedium?.totalSteps || 0,
    agentName: resultData.agentId
  };
  set({ mediumLayerData });
};

/**
 * Handles partial result event
 */
export const handlePartialResult = (
  event: UnifiedWebSocketEvent,
  state: UnifiedChatState,
  set: (partial: Partial<UnifiedChatState>) => void,
  get: () => UnifiedChatState
): void => {
  const resultData = extractPartialResultData(event.payload as any);
  if (resultData.isComplete && resultData.content) {
    createPartialResultMessage(resultData, get);
  }
  updateMediumLayerWithPartialContent(resultData, state, set);
};

/**
 * Extracts final report data from payload
 */
export const extractFinalReportData = (payload: any) => ({
  report: payload.report,
  recommendations: payload.recommendations,
  actionPlan: payload.action_plan,
  agentMetrics: payload.agent_metrics,
  executive_summary: payload.executive_summary,
  cost_analysis: payload.cost_analysis,
  performance_comparison: payload.performance_comparison,
  confidence_scores: payload.confidence_scores,
  technical_details: payload.technical_details,
  total_duration_ms: payload.total_duration_ms
});

/**
 * Creates final report message for chat
 */
export const createFinalReportMessage = (reportData: any, get: () => UnifiedChatState): void => {
  const message: ChatMessage = {
    id: generateUniqueId('final-report'),
    role: 'assistant',
    content: reportData.executive_summary || 
      `📊 Analysis complete! Found ${reportData.recommendations?.length || 0} recommendations.`,
    timestamp: Date.now(),
    metadata: { runId: get().currentRunId || undefined }
  };
  get().addMessage(message);
};

/**
 * Updates slow layer with final report
 */
export const updateSlowLayerWithFinalReport = (
  reportData: any,
  state: UnifiedChatState,
  set: (partial: Partial<UnifiedChatState>) => void
): void => {
  const finalReport: FinalReport = {
    report: reportData.report,
    recommendations: reportData.recommendations,
    actionPlan: reportData.actionPlan,
    agentMetrics: reportData.agentMetrics,
    executive_summary: reportData.executive_summary,
    cost_analysis: reportData.cost_analysis,
    performance_comparison: reportData.performance_comparison,
    confidence_scores: reportData.confidence_scores,
    technical_details: reportData.technical_details
  };
  
  set({
    isProcessing: false,
    slowLayerData: {
      completedAgents: state.slowLayerData?.completedAgents || [],
      finalReport,
      totalDuration: reportData.total_duration_ms,
      metrics: { total_tokens: 0, total_duration_ms: reportData.total_duration_ms, ...reportData }
    },
    subAgentStatus: 'completed'
  });
};

/**
 * Handles final report event
 */
export const handleFinalReport = (
  event: UnifiedWebSocketEvent,
  state: UnifiedChatState,
  set: (partial: Partial<UnifiedChatState>) => void,
  get: () => UnifiedChatState
): void => {
  const reportData = extractFinalReportData(event.payload as any);
  createFinalReportMessage(reportData, get);
  updateSlowLayerWithFinalReport(reportData, state, set);
};