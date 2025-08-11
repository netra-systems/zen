// Unified Chat UI/UX Types - Exact match with backend WebSocket event payloads
// Version 4.0 - Strict backend-frontend data coherence

// ============================================
// Fast Layer Types (0-100ms updates)
// ============================================

export interface AgentStartedEvent {
  type: 'agent_started';
  payload: {
    agent_name: string;
    timestamp: number;
    run_id: string;
  };
}

export interface ToolExecutingEvent {
  type: 'tool_executing';
  payload: {
    tool_name: string;
    agent_name: string;
    timestamp: number;
  };
}

export interface FastLayerData {
  agentName: string;        // From agent_started event
  activeTools: string[];    // From tool_executing events
  timestamp: number;        // From backend
  runId: string;           // From backend
}

// ============================================
// Medium Layer Types (100ms-1s updates)
// ============================================

export interface AgentThinkingEvent {
  type: 'agent_thinking';
  payload: {
    thought: string;
    agent_name: string;
    step_number: number;
    total_steps: number;
  };
}

export interface PartialResultEvent {
  type: 'partial_result';
  payload: {
    content: string;
    agent_name: string;
    is_complete: boolean;
  };
}

export interface MediumLayerData {
  thought: string;          // From agent_thinking event
  partialContent: string;   // From partial_result events (accumulated)
  stepNumber: number;       // From backend
  totalSteps: number;       // From backend
  agentName: string;        // From backend
}

// ============================================
// Slow Layer Types (1s+ updates)
// ============================================

export interface AgentCompletedEvent {
  type: 'agent_completed';
  payload: {
    agent_name: string;
    duration_ms: number;
    result: Record<string, unknown>;  // Agent-specific result data
    metrics: Record<string, unknown>; // Performance metrics
  };
}

export interface FinalReportEvent {
  type: 'final_report';
  payload: {
    report: Record<string, unknown>;      // Complete analysis report
    total_duration_ms: number;
    agent_metrics: AgentMetric[];
    recommendations: Recommendation[];
    action_plan: ActionStep[];
    executive_summary?: string;
    cost_analysis?: any;
    performance_comparison?: any;
    confidence_scores?: any;
    technical_details?: any;
  };
}

export interface SlowLayerData {
  completedAgents: AgentResult[];     // From agent_completed events
  finalReport: FinalReport | null;    // From final_report event
  totalDuration: number;               // From backend
  metrics: ExecutionMetrics;          // From backend
}

// ============================================
// Error Handling Types
// ============================================

export interface ErrorEvent {
  type: 'error';
  payload: {
    error_message: string;
    error_code: string;
    agent_name?: string;
    recoverable: boolean;
  };
}

// ============================================
// Supporting Types
// ============================================

export interface AgentResult {
  agentName: string;
  duration: number;
  result: any;  // Agent-specific, from backend
  metrics: any; // Agent-specific, from backend
  iteration?: number; // Iteration count for repeated agents
}

export interface FinalReport {
  report: any;                        // Complete report object
  recommendations: Recommendation[];   // From backend
  actionPlan: ActionStep[];           // From backend
  agentMetrics: AgentMetric[];       // From backend
  executive_summary?: string;
  cost_analysis?: any;
  performance_comparison?: any;
  confidence_scores?: any;
  technical_details?: any;
}

export interface Recommendation {
  id: string;
  title: string;
  description: string;
  impact: 'high' | 'medium' | 'low';
  effort: 'high' | 'medium' | 'low';
  category: string;
  metrics?: {
    potential_savings?: number;
    latency_reduction?: number;
    throughput_increase?: number;
  };
}

export interface ActionStep {
  id: string;
  step_number: number;
  description: string;
  command?: string;
  expected_outcome: string;
  dependencies?: string[];
  estimated_duration?: string;
}

export interface AgentMetric {
  agent_name: string;
  duration_ms: number;
  tokens_used?: number;
  tools_executed?: number;
  cache_hits?: number;
  cache_misses?: number;
}

export interface ExecutionMetrics {
  total_duration_ms: number;
  total_tokens: number;
  total_cost?: number;
  cache_efficiency?: number;
  parallel_executions?: number;
  sequential_executions?: number;
}

// ============================================
// Thread Management Events
// ============================================

export interface ThreadCreatedEvent {
  type: 'thread_created';
  payload: {
    thread_id: string;
    user_id: string;
    created_at: number;
  };
}

export interface ThreadLoadedEvent {
  type: 'thread_loaded';
  payload: {
    thread_id: string;
    messages: ChatMessage[];
    metadata: Record<string, unknown>;
  };
}

export interface ThreadRenamedEvent {
  type: 'thread_renamed';
  payload: {
    thread_id: string;
    new_title: string;
  };
}

// ============================================
// Run and Step Events
// ============================================

export interface RunStartedEvent {
  type: 'run_started';
  payload: {
    run_id: string;
    thread_id: string;
    assistant_id: string;
    model: string;
  };
}

export interface StepCreatedEvent {
  type: 'step_created';
  payload: {
    step_id: string;
    run_id: string;
    type: 'tool_call' | 'message' | 'function';
    details: Record<string, unknown>;
  };
}

// ============================================
// Union Types for WebSocket Events
// ============================================

export type UnifiedWebSocketEvent = 
  | AgentStartedEvent
  | ToolExecutingEvent
  | AgentThinkingEvent
  | PartialResultEvent
  | AgentCompletedEvent
  | FinalReportEvent
  | ErrorEvent
  | ThreadCreatedEvent
  | ThreadLoadedEvent
  | ThreadRenamedEvent
  | RunStartedEvent
  | StepCreatedEvent;

export type LayerUpdateEvent = 
  | { layer: 'fast'; data: FastLayerData }
  | { layer: 'medium'; data: MediumLayerData }
  | { layer: 'slow'; data: SlowLayerData };

// ============================================
// Component Props Types
// ============================================

export interface PersistentResponseCardProps {
  fastLayerData: FastLayerData | null;
  mediumLayerData: MediumLayerData | null;
  slowLayerData: SlowLayerData | null;
  isProcessing: boolean;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

export interface FastLayerProps {
  data: FastLayerData | null;
  isProcessing: boolean;
}

export interface MediumLayerProps {
  data: MediumLayerData | null;
}

export interface SlowLayerProps {
  data: SlowLayerData | null;
  isCollapsed?: boolean;
}

// ============================================
// Store Types
// ============================================

export interface UnifiedChatState {
  // Layer data
  fastLayerData: FastLayerData | null;
  mediumLayerData: MediumLayerData | null;
  slowLayerData: SlowLayerData | null;
  
  // Processing state
  isProcessing: boolean;
  currentRunId: string | null;
  
  // Thread management
  activeThreadId: string | null;
  threads: Map<string, unknown>;
  
  // Message history
  messages: ChatMessage[];
  
  // WebSocket connection
  isConnected: boolean;
  connectionError: string | null;
  
  // Agent deduplication
  executedAgents: Map<string, any>;
  agentIterations: Map<string, number>;
  
  // WebSocket event debugging
  wsEventBuffer: any;
  
  // Performance metrics
  performanceMetrics: {
    renderCount: number;
    lastRenderTime: number;
    averageResponseTime: number;
    memoryUsage: number;
  };
  
  // Actions
  updateFastLayer: (data: Partial<FastLayerData>) => void;
  updateMediumLayer: (data: Partial<MediumLayerData>) => void;
  updateSlowLayer: (data: Partial<SlowLayerData>) => void;
  handleWebSocketEvent: (event: UnifiedWebSocketEvent) => void;
  resetLayers: () => void;
  addMessage: (message: ChatMessage) => void;
  setProcessing: (isProcessing: boolean) => void;
  setConnectionStatus: (isConnected: boolean, error?: string) => void;
  setActiveThread: (threadId: string | null) => void;
  clearMessages: () => void;
  loadMessages: (messages: ChatMessage[]) => void;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
  threadId?: string;
  threadTitle?: string;
  metadata?: {
    runId?: string;
    agentName?: string;
    duration?: number;
  };
}

// ============================================
// Animation and Transition Types
// ============================================

export interface LayerTransition {
  duration: number;  // in ms
  easing: 'linear' | 'ease-in' | 'ease-out' | 'ease-in-out';
  delay?: number;    // in ms
}

export interface StreamingConfig {
  charactersPerSecond: number;
  useRequestAnimationFrame: boolean;
  debounceMs: number;
}

// ============================================
// Performance Monitoring Types
// ============================================

export interface PerformanceMetrics {
  renderTime: number;
  updateTime: number;
  memoryUsage?: number;
  frameRate?: number;
  eventProcessingTime: number;
}

// ============================================
// Configuration Types
// ============================================

export interface UnifiedChatConfig {
  maxMessages: number;              // Maximum messages to keep in memory
  messagePaginationSize: number;    // Number of messages to load at once
  streamingConfig: StreamingConfig;
  layerTransitions: {
    fast: LayerTransition;
    medium: LayerTransition;
    slow: LayerTransition;
  };
  autoCollapseDelay: number;       // ms after completion to auto-collapse
  performanceMonitoring: boolean;   // Enable performance tracking
}

// Default configuration
export const DEFAULT_UNIFIED_CHAT_CONFIG: UnifiedChatConfig = {
  maxMessages: 1000,
  messagePaginationSize: 50,
  streamingConfig: {
    charactersPerSecond: 30,
    useRequestAnimationFrame: true,
    debounceMs: 100,
  },
  layerTransitions: {
    fast: { duration: 0, easing: 'linear' },
    medium: { duration: 300, easing: 'ease-out' },
    slow: { duration: 400, easing: 'ease-out', delay: 100 },
  },
  autoCollapseDelay: 2000,
  performanceMonitoring: true,
};