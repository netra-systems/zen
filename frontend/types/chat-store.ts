/**
 * Strong type definitions for Chat Store and message handling.
 * 
 * AUTHORITATIVE SOURCE FOR FRONTEND UI TYPES
 * - This file contains frontend-specific UI types and state management types
 * - For backend schema types, import from './backend_schema_base'
 * - These types are optimized for React state management and UI interactions
 */

// Import consolidated types from single source of truth (registry)
import type { 
  Message,
  BaseMessage,
  MessageRole, 
  MessageMetadata,
  MessageAttachment,
  MessageReaction,
  Thread,
  ThreadMetadata
} from '@/types/unified';
import { MessageType } from '@/types/unified';

// Re-export for backwards compatibility
export type { Message, BaseMessage, MessageRole, MessageMetadata, MessageAttachment, MessageReaction, Thread, ThreadMetadata };
export { MessageType };

// Sub-agent types
export type SubAgentStatus = 
  | 'idle'
  | 'starting'
  | 'running'
  | 'thinking'
  | 'processing'
  | 'using_tool'
  | 'completed'
  | 'error'
  | 'stopped'
  | 'paused'
  | 'cancelled';

export interface SubAgentProgress {
  current: number;
  total: number;
  message?: string;
  percentage?: number;
  estimated_completion?: string;
  stage?: string;
}

export interface SubAgentState {
  name: string;
  status: SubAgentStatus;
  description?: string;
  tools?: string[];
  progress?: SubAgentProgress;
  error?: string;
  execution_time?: number;
  started_at?: string;
  completed_at?: string;
  capabilities?: string[];
  current_task?: string;
  last_update?: string;
}

export interface SubAgentStatusData {
  status: string;
  tools?: string[];
  progress?: SubAgentProgress;
  error?: string;
  description?: string;
  execution_time?: number;
  current_task?: string;
  stage?: string;
}

// Thread management types - Use unified types from registry
// Import Thread and ThreadMetadata from '@/types/unified' for consistent typing

// Chat state mutations
export type ChatAction = 
  | { type: 'ADD_MESSAGE'; payload: Message }
  | { type: 'UPDATE_MESSAGE'; payload: { messageId: string; updates: Partial<Message> } }
  | { type: 'DELETE_MESSAGE'; payload: { messageId: string } }
  | { type: 'SET_SUB_AGENT_STATUS'; payload: SubAgentStatus | SubAgentStatusData }
  | { type: 'SET_SUB_AGENT_NAME'; payload: string }
  | { type: 'SET_PROCESSING'; payload: boolean }
  | { type: 'CLEAR_MESSAGES'; payload: void }
  | { type: 'CLEAR_SUB_AGENT'; payload: void }
  | { type: 'SET_ACTIVE_THREAD'; payload: string | null }
  | { type: 'LOAD_THREAD_MESSAGES'; payload: Message[] }
  | { type: 'LOAD_MESSAGES'; payload: any[] }
  | { type: 'ADD_ERROR'; payload: string }
  | { type: 'ADD_ERROR_MESSAGE'; payload: string }
  | { type: 'RESET'; payload: void }
  | { type: 'SET_QUEUED_SUB_AGENTS'; payload: string[] }
  | { type: 'ADD_QUEUED_SUB_AGENT'; payload: string }
  | { type: 'REMOVE_QUEUED_SUB_AGENT'; payload: string }
  | { type: 'UPDATE_SUB_AGENT_PROGRESS'; payload: SubAgentProgress }
  | { type: 'SET_THINKING_MODE'; payload: boolean }
  | { type: 'SET_STREAMING_MODE'; payload: boolean };

// Complete chat state interface
export interface ChatState {
  // Messages
  messages: Message[];
  currentMessageIndex: number;
  totalMessages: number;
  hasMoreMessages: boolean;
  
  // Sub-agent state
  subAgentName: string;
  currentSubAgent: string | null;
  subAgentStatus: SubAgentStatus | string | null;
  subAgentTools: string[];
  subAgentProgress: SubAgentProgress | null;
  subAgentError: string | null;
  subAgentDescription: string | null;
  subAgentExecutionTime: number | null;
  queuedSubAgents: string[];
  
  // Processing state
  isProcessing: boolean;
  isThinking: boolean;
  isStreaming: boolean;
  streamingMessageId: string | null;
  
  // Thread management
  activeThreadId: string | null;
  threads: Thread[];
  currentThread: Thread | null;
  
  // UI state
  showThinking: boolean;
  typingIndicator: boolean;
  lastUserMessage: string | null;
  
  // Performance metrics
  responseTime: number | null;
  tokenCount: number | null;
  modelUsed: string | null;
}

// Chat store actions interface
export interface ChatActions {
  // Message management
  addMessage: (message: Message) => void;
  updateMessage: (messageId: string, updates: Partial<Message>) => void;
  deleteMessage: (messageId: string) => void;
  clearMessages: () => void;
  loadMessages: (messages: any[]) => void;
  
  // Sub-agent management
  setSubAgentName: (name: string) => void;
  setSubAgentStatus: (status: SubAgentStatus | SubAgentStatusData) => void;
  setSubAgent: (name: string, status: string) => void;
  clearSubAgent: () => void;
  updateSubAgentProgress: (progress: SubAgentProgress) => void;
  addQueuedSubAgent: (agentName: string) => void;
  removeQueuedSubAgent: (agentName: string) => void;
  
  // Processing state
  setProcessing: (isProcessing: boolean) => void;
  setThinking: (isThinking: boolean) => void;
  setStreaming: (isStreaming: boolean, messageId?: string) => void;
  
  // Thread management
  setActiveThread: (threadId: string | null) => void;
  loadThreadMessages: (messages: Message[]) => void;
  createThread: (title?: string) => Thread;
  deleteThread: (threadId: string) => void;
  updateThread: (threadId: string, updates: Partial<Thread>) => void;
  archiveThread: (threadId: string) => void;
  
  // Error handling
  addError: (error: string) => void;
  addErrorMessage: (error: string) => void;
  clearErrors: () => void;
  
  // Utility functions
  reset: () => void;
  getMessageById: (messageId: string) => Message | undefined;
  getMessagesByThread: (threadId: string) => Message[];
  searchMessages: (query: string) => Message[];
  exportMessages: (format: 'json' | 'txt' | 'markdown') => string;
  
  // Performance tracking
  updatePerformanceMetrics: (metrics: {
    responseTime?: number;
    tokenCount?: number;
    modelUsed?: string;
  }) => void;
}

// Combined interface for the chat store
export interface ChatStore extends ChatState, ChatActions {}

// Message builder utilities
export interface MessageBuilder {
  user: (content: string, options?: Partial<Message>) => Message;
  assistant: (content: string, options?: Partial<Message>) => Message;
  system: (content: string, options?: Partial<Message>) => Message;
  error: (error: string, options?: Partial<Message>) => Message;
  toolCall: (toolName: string, args: any, options?: Partial<Message>) => Message;
  toolResult: (toolName: string, result: any, options?: Partial<Message>) => Message;
}

// Message filtering and sorting types
export type MessageFilter = {
  type?: MessageType[];
  role?: MessageRole[];
  sub_agent?: string[];
  dateRange?: {
    start: string;
    end: string;
  };
  hasError?: boolean;
  hasAttachments?: boolean;
  searchTerm?: string;
};

export type MessageSortBy = 'created_at' | 'updated_at' | 'relevance' | 'thread_id';
export type SortOrder = 'asc' | 'desc';

export interface MessageQuery {
  filter?: MessageFilter;
  sortBy?: MessageSortBy;
  sortOrder?: SortOrder;
  limit?: number;
  offset?: number;
}

// Pagination types
export interface MessagePagination {
  currentPage: number;
  totalPages: number;
  pageSize: number;
  totalCount: number;
  hasNextPage: boolean;
  hasPreviousPage: boolean;
}

// Message statistics
export interface MessageStats {
  totalMessages: number;
  messagesByType: Record<MessageType, number>;
  messagesByRole: Record<MessageRole, number>;
  messagesBySubAgent: Record<string, number>;
  averageResponseTime: number;
  totalTokensUsed: number;
  averageMessageLength: number;
  errorRate: number;
  mostActiveHour: number;
  threadsCreated: number;
  messagesPerThread: number;
}

// Export configuration
export interface ExportConfig {
  format: 'json' | 'txt' | 'markdown' | 'csv';
  includeMetadata: boolean;
  includeErrors: boolean;
  includeSystem: boolean;
  dateRange?: {
    start: string;
    end: string;
  };
  threads?: string[];
  compression?: boolean;
}