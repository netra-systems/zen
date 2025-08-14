/**
 * Strong type definitions for Agent operations following Netra conventions.
 */

// Strong type definitions for metadata
export interface AgentMessageMetadata {
  model?: string;
  tokensUsed?: number;
  processingTime?: number;
  agentName?: string;
  runId?: string;
  stepId?: string;
  toolCalls?: ToolCall[];
}

export interface TaskResult {
  output?: string;
  data?: Record<string, unknown>;
  artifacts?: Artifact[];
  status: 'success' | 'partial' | 'failed';
}

export interface ToolCall {
  id: string;
  name: string;
  arguments?: Record<string, unknown>;
  result?: unknown;
  duration?: number;
}

export interface Artifact {
  id: string;
  type: string;
  name: string;
  content?: unknown;
  url?: string;
}

export interface AgentStateMetadata {
  priority?: 'low' | 'medium' | 'high';
  dependencies?: string[];
  tags?: string[];
  version?: string;
}

export interface ThreadMetadata {
  userId: string;
  createdAt: string;
  lastActivity: string;
  messageCount: number;
  tags?: string[];
  priority?: 'low' | 'medium' | 'high';
  archived?: boolean;
}

export interface ErrorDetails {
  errorType: string;
  context?: Record<string, unknown>;
  originalError?: unknown;
  metadata?: Record<string, string | number | boolean>;
}

export interface OptimizationMetadata {
  algorithm?: string;
  iterations?: number;
  constraints?: Record<string, unknown>;
  parameters?: Record<string, unknown>;
}

export interface WebSocketPayload {
  [key: string]: string | number | boolean | null | WebSocketPayload | Array<unknown>;
}

export interface AgentUpdate {
  type: string;
  agentId?: string;
  data: Record<string, unknown>;
  timestamp: number;
}

export enum MessageRole {
  USER = 'user',
  ASSISTANT = 'assistant',
  SYSTEM = 'system',
  AGENT = 'agent',
  TOOL = 'tool'
}

export enum MessageStatus {
  PENDING = 'pending',
  SENT = 'sent',
  DELIVERED = 'delivered',
  READ = 'read',
  FAILED = 'failed'
}

export interface MessageAttachment {
  id: string;
  filename: string;
  mimeType: string;
  size: number;
  url?: string;
  thumbnailUrl?: string;
}

export interface MessageReaction {
  emoji: string;
  userId: string;
  timestamp: Date;
}

export interface Message {
  id: string;
  threadId: string;
  role: MessageRole;
  content: string;
  timestamp: Date;
  status: MessageStatus;
  attachments?: MessageAttachment[];
  reactions?: MessageReaction[];
  editedAt?: Date;
  deletedAt?: Date;
  metadata?: AgentMessageMetadata;
  parentMessageId?: string;
  references?: string[];
}

export enum OptimizationType {
  PERFORMANCE = 'performance',
  COST = 'cost',
  QUALITY = 'quality',
  BALANCED = 'balanced'
}

export interface OptimizationMetric {
  name: string;
  value: number;
  unit: string;
  trend: 'up' | 'down' | 'stable';
  changePercent?: number;
}

export interface OptimizationRecommendation {
  id: string;
  title: string;
  description: string;
  impact: 'high' | 'medium' | 'low';
  effort: 'high' | 'medium' | 'low';
  estimatedSavings?: number;
  implementationSteps?: string[];
  risks?: string[];
}

export interface OptimizationResults {
  id: string;
  type: OptimizationType;
  timestamp: Date;
  status: 'analyzing' | 'completed' | 'failed';
  metrics: OptimizationMetric[];
  recommendations: OptimizationRecommendation[];
  summary: string;
  confidence: number; // 0-1
  processingTimeMs: number;
  metadata?: OptimizationMetadata;
}

export enum SubAgentStatus {
  IDLE = 'idle',
  INITIALIZING = 'initializing',
  RUNNING = 'running',
  WAITING = 'waiting',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled'
}

export interface SubAgentTask {
  id: string;
  name: string;
  description?: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress?: number; // 0-1
  startedAt?: Date;
  completedAt?: Date;
  result?: TaskResult;
  error?: string;
}

export interface SubAgentState {
  id: string;
  name: string;
  type: string;
  status: SubAgentStatus;
  currentTask?: SubAgentTask;
  tasks: SubAgentTask[];
  progress: number; // 0-1
  startedAt?: Date;
  completedAt?: Date;
  lastUpdateAt: Date;
  metadata?: AgentStateMetadata;
  capabilities?: string[];
  resourceUsage?: {
    cpu?: number;
    memory?: number;
    apiCalls?: number;
  };
}

export interface AgentError {
  code: string;
  message: string;
  details?: ErrorDetails;
  timestamp: Date;
  recoverable: boolean;
  suggestedAction?: string;
  affectedAgents?: string[];
  stackTrace?: string;
}

export interface Thread {
  id: string;
  name?: string;
  createdAt: Date;
  updatedAt: Date;
  messageCount: number;
  lastMessage?: Message;
  participants?: string[];
  tags?: string[];
  archived?: boolean;
  metadata?: ThreadMetadata;
}

export interface AgentConfiguration {
  maxConcurrentAgents?: number;
  timeoutMs?: number;
  retryAttempts?: number;
  enableCaching?: boolean;
  enableStreaming?: boolean;
  logLevel?: 'debug' | 'info' | 'warn' | 'error';
  customTools?: string[];
}

export interface AgentContextValue {
  // State
  messages: Message[];
  optimizationResults: OptimizationResults | null;
  subAgentStates: SubAgentState[];
  currentThread: Thread | null;
  threads: Thread[];
  isConnected: boolean;
  isProcessing: boolean;
  error: AgentError | null;
  
  // Actions
  sendMessage: (content: string, attachments?: MessageAttachment[]) => Promise<void>;
  startOptimization: (type: OptimizationType) => Promise<void>;
  stopAgent: (agentId: string) => Promise<void>;
  createThread: (name?: string) => Promise<Thread>;
  switchThread: (threadId: string) => Promise<void>;
  deleteThread: (threadId: string) => Promise<void>;
  clearError: () => void;
  
  // WebSocket
  sendWsMessage: (type: string, payload: WebSocketPayload) => void;
  subscribeToUpdates: (callback: (update: AgentUpdate) => void) => () => void;
  
  // Configuration
  configuration: AgentConfiguration;
  updateConfiguration: (config: Partial<AgentConfiguration>) => void;
}

export interface AgentProviderProps {
  children: React.ReactNode;
  configuration?: Partial<AgentConfiguration>;
  onConnectionChange?: (connected: boolean) => void;
  onError?: (error: AgentError) => void;
  autoReconnect?: boolean;
  reconnectInterval?: number;
}