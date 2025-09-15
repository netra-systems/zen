// Store types for unified chat system
// Modular state management types

import type {
  FastLayerData,
  MediumLayerData,
  SlowLayerData
} from './layer-types';
import type { UnifiedWebSocketEvent, ChatMessage } from './websocket-event-types';
import type { MCPUIState } from './mcp-types';
import type { OptimisticMessage } from '@/services/optimistic-updates';
import type { StoreThreadState } from '@shared/types/frontend_types';

// ============================================
// Agent Execution Tracking
// ============================================

export interface AgentExecution {
  name: string;
  iteration: number;
  status: 'running' | 'completed' | 'failed';
  startTime: number;
  endTime?: number;
  result?: unknown;
}

export interface WebSocketEventBuffer {
  push: (event: unknown) => void;
  getEvents: () => unknown[];
  clear: () => void;
  size: number;
}

// ============================================
// Store State Types
// ============================================

export interface LayerState {
  fastLayerData: FastLayerData | null;
  mediumLayerData: MediumLayerData | null;
  slowLayerData: SlowLayerData | null;
}

export interface ProcessingState {
  isProcessing: boolean;
  currentRunId: string | null;
}

// ThreadState moved to shared/types/frontend_types.ts for SSOT compliance
// SSOT import for store-specific thread state with actions
// NOTE: Renamed from ThreadState to avoid namespace collision with canonical ThreadState
export type { StoreThreadState as StoreThreadSliceState } from '@shared/types/frontend_types';

export interface ConnectionState {
  isConnected: boolean;
  connectionError: string | null;
}

export interface ConnectionActions {
  setConnectionStatus: (isConnected: boolean, error?: string) => void;
}

export interface AgentTrackingState {
  executedAgents: Map<string, AgentExecution>;
  agentIterations: Map<string, number>;
}

export interface OptimisticState {
  optimisticMessages: Map<string, OptimisticMessage>;
  pendingUserMessage: OptimisticMessage | null;
  pendingAiMessage: OptimisticMessage | null;
}

export interface DebugState {
  wsEventBuffer: WebSocketEventBuffer;
  wsEventBufferVersion: number;
}

export interface PerformanceState {
  performanceMetrics: {
    renderCount: number;
    lastRenderTime: number;
    averageResponseTime: number;
    memoryUsage: number;
  };
}

export interface LegacySubAgentState {
  subAgentName: string | null;
  subAgentStatus: string | null;
  subAgentTools: string[];
  subAgentProgress: { current: number; total: number; message?: string } | null;
  subAgentError: string | null;
  subAgentDescription: string | null;
  subAgentExecutionTime: number | null;
  queuedSubAgents: string[];
}

export interface MCPState {
  mcpState?: MCPUIState;
}

// ============================================
// Store Actions Types
// ============================================

export interface LayerActions {
  updateFastLayer: (data: Partial<FastLayerData>) => void;
  updateMediumLayer: (data: Partial<MediumLayerData>) => void;
  updateSlowLayer: (data: Partial<SlowLayerData>) => void;
  resetLayers: () => void;
}

export interface WebSocketActions {
  handleWebSocketEvent: (event: UnifiedWebSocketEvent) => void;
  setConnectionStatus: (isConnected: boolean, error?: string) => void;
}

export interface ProcessingActions {
  setProcessing: (isProcessing: boolean) => void;
}

export interface MessageActions {
  addMessage: (message: ChatMessage) => void;
  clearMessages: () => void;
  loadMessages: (messages: ChatMessage[]) => void;
}

export interface ThreadActions {
  setActiveThread: (threadId: string | null) => void;
  setThreadLoading: (isLoading: boolean) => void;
  startThreadLoading: (threadId: string) => void;
  completeThreadLoading: (threadId: string, messages: ChatMessage[]) => void;
}

export interface LegacySubAgentActions {
  setSubAgentName: (name: string | null) => void;
  setSubAgentStatus: (statusData: { 
    status: string; 
    tools?: string[]; 
    progress?: { current: number; total: number; message?: string }; 
    error?: string; 
    description?: string; 
    executionTime?: number; 
  } | null) => void;
}

export interface AgentTrackingActions {
  updateExecutedAgent: (agentId: string, execution: AgentExecution) => void;
  incrementAgentIteration: (agentId: string) => void;
  resetAgentTracking: () => void;
}

export interface OptimisticActions {
  addOptimisticMessage: (message: OptimisticMessage) => void;
  updateOptimisticMessage: (localId: string, updates: Partial<OptimisticMessage>) => void;
  removeOptimisticMessage: (localId: string) => void;
  clearOptimisticMessages: () => void;
}

export interface StoreManagementActions {
  resetStore: () => void; // Comprehensive store reset for logout
}

// ============================================
// Combined Store Types
// ============================================

export interface UnifiedChatState extends
  LayerState,
  ProcessingState,
  StoreThreadState,
  ConnectionState,
  AgentTrackingState,
  OptimisticState,
  DebugState,
  PerformanceState,
  LegacySubAgentState,
  MCPState,
  LayerActions,
  WebSocketActions,
  ProcessingActions,
  MessageActions,
  ThreadActions,
  LegacySubAgentActions,
  AgentTrackingActions,
  OptimisticActions,
  StoreManagementActions {}

// ============================================
// Store Configuration
// ============================================

export interface StoreConfig {
  name: string;
  enableDevtools?: boolean;
  eventBufferSize?: number;
}

export const DEFAULT_STORE_CONFIG: StoreConfig = {
  name: 'unified-chat-store',
  enableDevtools: true,
  eventBufferSize: 1000,
};
