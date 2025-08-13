/**
 * Strong type definitions for Agent operations following Netra conventions.
 */

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
  metadata?: {
    model?: string;
    tokensUsed?: number;
    processingTime?: number;
    [key: string]: any;
  };
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
  metadata?: Record<string, any>;
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
  result?: any;
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
  metadata?: Record<string, any>;
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
  details?: any;
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
  metadata?: Record<string, any>;
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
  sendWsMessage: (type: string, payload: any) => void;
  subscribeToUpdates: (callback: (update: any) => void) => () => void;
  
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