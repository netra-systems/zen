// Enhanced tool handlers with lifecycle management - 8-line functions max
// Replaces websocket-tool-handlers.ts with proper tool tracking

import { mapEventPayload } from '@/utils/event-payload-mapper';
import { getGlobalToolTracker } from '@/services/tool-tracking-service';
import type { 
  UnifiedWebSocketEvent,
  FastLayerData
} from '@/types/websocket-event-types';
import type { ToolExecutionStatus } from '@/types/layer-types';
import type { UnifiedChatState } from '@/types/store-types';

/**
 * Extracts tool data from payload with enhanced validation
 */
export const extractToolData = (payload: any) => {
  const mappedPayload = mapEventPayload('tool_executing', payload);
  return {
    toolName: mappedPayload.tool_name || 'unknown-tool',
    timestamp: mappedPayload.timestamp || Date.now(),
    agentId: mappedPayload.agent_id
  };
};

/**
 * Creates tool status from tool data
 */
export const createToolExecutionStatus = (
  toolName: string, 
  timestamp: number
): ToolExecutionStatus => {
  return {
    name: toolName,
    startTime: timestamp,
    isActive: true
  };
};

/**
 * Updates tool statuses array with new tool
 */
export const updateToolExecutionStatuses = (
  currentStatuses: ToolExecutionStatus[], 
  newTool: ToolExecutionStatus
): ToolExecutionStatus[] => {
  const filtered = currentStatuses.filter(status => status.name !== newTool.name);
  return [...filtered, newTool];
};

/**
 * Converts tool statuses to active tools array (legacy support)
 */
export const getActiveToolsFromStatuses = (statuses: ToolExecutionStatus[]): string[] => {
  return statuses
    .filter(status => status.isActive)
    .map(status => status.name);
};

/**
 * Updates fast layer with enhanced tool tracking
 */
export const updateFastLayerWithEnhancedTools = (
  fastLayerData: FastLayerData,
  toolStatuses: ToolExecutionStatus[],
  timestamp: number,
  set: (partial: Partial<UnifiedChatState>) => void
): void => {
  const activeTools = getActiveToolsFromStatuses(toolStatuses);
  set({
    fastLayerData: {
      ...fastLayerData,
      toolStatuses,
      activeTools,
      timestamp
    }
  });
};

/**
 * Enhanced tool executing handler with lifecycle management
 */
export const handleToolExecutingEnhanced = (
  event: UnifiedWebSocketEvent,
  state: UnifiedChatState,
  set: (partial: Partial<UnifiedChatState>) => void
): void => {
  const { toolName, timestamp } = extractToolData(event.payload as any);
  const currentFastLayer = ensureFastLayerExists(state.fastLayerData);
  startToolExecution(toolName, timestamp, currentFastLayer, set);
};

/**
 * Extracts completed tool name with enhanced validation
 */
export const extractCompletedToolName = (payload: any): string => {
  const mappedPayload = mapEventPayload('tool_completed', payload);
  return mappedPayload.tool_name || mappedPayload.name || 'unknown-tool';
};

/**
 * Removes tool from statuses array
 */
export const removeToolFromStatuses = (
  statuses: ToolExecutionStatus[], 
  toolName: string
): ToolExecutionStatus[] => {
  return statuses.filter(status => status.name !== toolName);
};

/**
 * Enhanced tool completed handler with lifecycle management
 */
export const handleToolCompletedEnhanced = (
  event: UnifiedWebSocketEvent,
  state: UnifiedChatState,
  set: (partial: Partial<UnifiedChatState>) => void
): void => {
  const toolName = extractCompletedToolName(event.payload as any);
  const currentFastLayer = ensureFastLayerExists(state.fastLayerData);
  completeToolExecution(toolName, currentFastLayer, set);
};

/**
 * Initializes fast layer data with empty tool tracking
 */
export const initializeFastLayerData = (
  agentName: string, 
  runId: string, 
  timestamp: number
): FastLayerData => {
  return {
    agentName,
    runId,
    timestamp,
    activeTools: [],
    toolStatuses: []
  };
};

/**
 * Cleanup tools for agent completion
 */
export const cleanupToolsOnAgentComplete = (
  fastLayerData: FastLayerData | null,
  set: (partial: Partial<UnifiedChatState>) => void
): void => {
  if (!fastLayerData) return;
  
  const toolTracker = getGlobalToolTracker();
  fastLayerData.toolStatuses?.forEach(status => {
    if (status.isActive) {
      toolTracker.completeTool(status.name);
    }
  });
  
  set({
    fastLayerData: {
      ...fastLayerData,
      activeTools: [],
      toolStatuses: []
    }
  });
};

// Helper functions for tool execution (≤8 lines each)
const ensureFastLayerExists = (fastLayerData: FastLayerData | null): FastLayerData => {
  return fastLayerData || {
    agentName: '', 
    runId: '', 
    timestamp: Date.now(),
    activeTools: [], 
    toolStatuses: []
  };
};

const startToolExecution = (
  toolName: string,
  timestamp: number,
  currentFastLayer: FastLayerData,
  set: (partial: Partial<UnifiedChatState>) => void
): void => {
  const toolTracker = getGlobalToolTracker();
  toolTracker.startTool(toolName);
  const newToolExecutionStatus = createToolExecutionStatus(toolName, timestamp);
  const updatedStatuses = updateToolExecutionStatuses(currentFastLayer.toolStatuses || [], newToolExecutionStatus);
  updateFastLayerWithEnhancedTools(currentFastLayer, updatedStatuses, timestamp, set);
};

const completeToolExecution = (
  toolName: string,
  currentFastLayer: FastLayerData,
  set: (partial: Partial<UnifiedChatState>) => void
): void => {
  const toolTracker = getGlobalToolTracker();
  toolTracker.completeTool(toolName);
  const updatedStatuses = removeToolFromStatuses(currentFastLayer.toolStatuses || [], toolName);
  updateFastLayerWithEnhancedTools(currentFastLayer, updatedStatuses, Date.now(), set);
};