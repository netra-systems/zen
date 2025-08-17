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

// Agent execution tracking
export interface AgentExecution {
  name: string;
  iteration: number;
  status: 'running' | 'completed' | 'failed';
  startTime: number;
  endTime?: number;
  result?: any;
}

// Performance metrics
export interface PerformanceMetrics {
  renderCount: number;
  lastRenderTime: number;
  averageResponseTime: number;
  memoryUsage: number;
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

// Thread management slice state
export interface ThreadState {
  activeThreadId: string | null;
  threads: Map<string, unknown>;
  isThreadLoading: boolean;
  setActiveThread: (threadId: string | null) => void;
  setThreadLoading: (isLoading: boolean) => void;
}

// Connection state slice
export interface ConnectionState {
  isConnected: boolean;
  connectionError: string | null;
  setConnectionStatus: (isConnected: boolean, error?: string) => void;
}

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