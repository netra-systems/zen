// Tool-specific WebSocket event handlers - Modular 25-line functions
// Handles tool executing, completed events

import { mapEventPayload } from '@/utils/event-payload-mapper';
import type { 
  UnifiedWebSocketEvent,
  FastLayerData
} from '@/types/websocket-event-types';
import type { UnifiedChatState } from '@/types/store-types';

/**
 * Extracts tool data from payload
 */
export const extractToolData = (payload: any) => {
  const mappedPayload = mapEventPayload('tool_executing', payload);
  return {
    toolName: mappedPayload.tool_name || 'unknown-tool',
    timestamp: mappedPayload.timestamp || Date.now()
  };
};

/**
 * Updates active tools list with new tool
 */
export const getUpdatedActiveTools = (currentTools: string[], toolName: string): string[] => {
  return currentTools.includes(toolName) ? currentTools : [...currentTools, toolName];
};

/**
 * Updates fast layer data with tool information
 */
export const updateFastLayerWithTool = (
  fastLayerData: FastLayerData,
  activeTools: string[],
  timestamp: number,
  set: (partial: Partial<UnifiedChatState>) => void
): void => {
  set({
    fastLayerData: {
      ...fastLayerData,
      activeTools,
      timestamp
    }
  });
};

/**
 * Handles tool executing event
 */
export const handleToolExecuting = (
  event: UnifiedWebSocketEvent,
  state: UnifiedChatState,
  set: (partial: Partial<UnifiedChatState>) => void
): void => {
  const { toolName, timestamp } = extractToolData(event.payload as any);
  if (!state.fastLayerData) return;
  
  const activeTools = getUpdatedActiveTools(state.fastLayerData.activeTools, toolName);
  updateFastLayerWithTool(state.fastLayerData, activeTools, timestamp, set);
};

/**
 * Extracts completed tool name from payload
 */
export const extractCompletedToolName = (payload: any): string => {
  const mappedPayload = mapEventPayload('tool_completed', payload);
  return mappedPayload.tool_name || mappedPayload.name || 'unknown-tool';
};

/**
 * Removes tool from active tools list
 */
export const removeToolFromActive = (activeTools: string[], toolName: string): string[] => {
  return activeTools.filter(tool => tool !== toolName);
};

/**
 * Updates fast layer data when tool completes
 */
export const updateFastLayerData = (
  fastLayerData: FastLayerData,
  activeTools: string[],
  set: (partial: Partial<UnifiedChatState>) => void
): void => {
  set({ fastLayerData: { ...fastLayerData, activeTools } });
};

/**
 * Handles tool completed event
 */
export const handleToolCompleted = (
  event: UnifiedWebSocketEvent,
  state: UnifiedChatState,
  set: (partial: Partial<UnifiedChatState>) => void
): void => {
  const toolName = extractCompletedToolName(event.payload as any);
  if (!state.fastLayerData) return;
  
  const updatedTools = removeToolFromActive(state.fastLayerData.activeTools, toolName);
  updateFastLayerData(state.fastLayerData, updatedTools, set);
};