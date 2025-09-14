// Store Slice Types
import type {
  FastLayerData,
  MediumLayerData,
  SlowLayerData,
  ChatMessage,
  UnifiedWebSocketEvent,
  AgentResult,
  FinalReport,
  ExecutionMetrics
} from '@/types/unified-chat';
import type { WebSocketEventBuffer } from '@/lib/circular-buffer';
import type { ConnectionState, ConnectionActions } from '@/types/store-types';
import type { PerformanceMetrics } from '@/types/unified';
import type { StoreThreadState } from '@shared/types/frontend_types';

// Agent execution tracking
export interface AgentExecution {
  name: string;
  iteration: number;
  status: 'running' | 'completed' | 'failed';
  startTime: number;
  endTime?: number;
  result?: any;
}

// Layer data slice state
export interface LayerDataState {
  fastLayerData: FastLayerData | null;
  mediumLayerData: MediumLayerData | null;
  slowLayerData: SlowLayerData | null;
  updateFastLayer: (data: Partial<FastLayerData>) => void;
  updateMediumLayer: (data: Partial<MediumLayerData>) => void;
  updateSlowLayer: (data: Partial<SlowLayerData>) => void;
  resetLayers: () => void;
}

// Message management slice state
export interface MessageState {
  messages: ChatMessage[];
  addMessage: (message: ChatMessage) => void;
  clearMessages: () => void;
  loadMessages: (messages: ChatMessage[]) => void;
}

// Agent tracking slice state
export interface AgentTrackingState {
  executedAgents: Map<string, AgentExecution>;
  agentIterations: Map<string, number>;
  isProcessing: boolean;
  currentRunId: string | null;
  setProcessing: (isProcessing: boolean) => void;
}

// Thread management slice state - SSOT import eliminates local ThreadState definition
// Use StoreThreadState directly to avoid namespace collision with canonical ThreadState
export type ThreadSliceState = StoreThreadState;

// Connection state slice - import from consolidated types
export interface ConnectionSlice extends ConnectionState, ConnectionActions {}

// Sub-agent UI slice state (frontend-specific, different from backend SubAgentState)
export interface SubAgentUIState {
  subAgentName: string | null;
  subAgentStatus: string | null;
  subAgentTools: string[];
  subAgentProgress: { current: number; total: number; message?: string } | null;
  subAgentError: string | null;
  subAgentDescription: string | null;
  subAgentExecutionTime: number | null;
  queuedSubAgents: string[];
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

// Performance slice state
export interface PerformanceState {
  performanceMetrics: PerformanceMetrics;
  wsEventBuffer: WebSocketEventBuffer;
}