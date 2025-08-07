
export interface User {
    id: number;
    full_name?: string;
    email: string;
    picture?: string;
}

export type MessageRole = 'user' | 'assistant' | 'agent';

export interface StateUpdate {
  todo_list: string[];
  completed_steps: string[];
}

export interface ToolCall {
  name: string;
  args: Record<string, any>;
  id: string;
  type?: 'tool_call';
}

export interface ToolCallChunk {
  name: string;
  args: string;
  id: string;
  index?: number;
  type?: 'tool_call_chunk';
}

export interface UsageMetadata {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  input_token_details?: any;
  output_token_details?: any;
}

export interface ResponseMetadata {
  finish_reason?: string;
  model_name?: string;
  safety_ratings?: any[];
}

export interface AIMessageChunk {
  content?: string;
  additional_kwargs?: {
    function_call?: {
      name: string;
      arguments: string;
    };
  };
  response_metadata?: ResponseMetadata;
  id?: string;
  tool_calls?: ToolCall[];
  usage_metadata?: UsageMetadata;
  tool_call_chunks?: ToolCallChunk[];
}

// This represents the raw message from the server
export interface ServerEvent {
  event: string;
  data: StreamEventData;
  run_id?: string;
}

export interface StateData {
  todo_list: string[];
  completed_steps: string[];
}

export interface StreamEventData {
  run_id: string;
  input?: any;
  chunk?: any;
  messages?: any[];
}


// Specific data types for each event
export interface AgentStartedData {
  status: 'agent_started';
  run_id: string;
}

export interface ChainStartData {
  input: {
    messages: any[]; // Can be more specific if needed
  };
}

export interface ChatModelStartData {
  input: {
    messages: any[]; // Can be more specific if needed
  };
}

export interface ChatModelStreamData {
  chunk: AIMessageChunk;
}

export interface RunCompleteData {
  status: 'complete';
}

export interface ToolEndData {
  output: any;
}

export interface ToolErrorData {
  error: any;
}

export interface UpdateStateData {
  data: StateUpdate;
}

// Base interface for all message types
export interface BaseMessage {
  id: string;
  role: MessageRole;
  rawServerEvent?: ServerEvent;
}

export interface UserMessage extends BaseMessage {
  type: 'user';
  content: string;
}

export interface EventMessage extends BaseMessage {
  type: 'event';
  content: string;
  eventName: string;
}

export interface TextMessage extends BaseMessage {
  type: 'text';
  content: string;
  usageMetadata?: UsageMetadata;
  responseMetadata?: ResponseMetadata;
}

export interface ToolStartMessage extends BaseMessage {
  type: 'tool_start';
  content: string;
  tool: string;
  toolInput: any;
  usageMetadata?: UsageMetadata;
  responseMetadata?: ResponseMetadata;
}

export interface ToolEndMessage extends BaseMessage {
  type: 'tool_end';
  content: string;
  tool: string;
  toolInput: any;
  toolOutput: any;
  usageMetadata?: UsageMetadata;
  responseMetadata?: ResponseMetadata;
}

export interface ToolEndErrorMessage extends BaseMessage {
  type: 'tool_end';
  content: string;
  tool: string;
  toolInput: any;
  toolOutput: {
    content: string;
    is_error: true;
  };
  usageMetadata?: UsageMetadata;
  responseMetadata?: ResponseMetadata;
}

export interface ErrorMessage extends BaseMessage {
  type: 'error';
  content: string;
  isError: true;
  tool?: string;
  toolInput?: any;
  toolOutput?: any;
}

export interface ThinkingMessage extends BaseMessage {
    type: 'thinking';
    content: string;
}

export interface StateUpdateMessage extends BaseMessage {
    type: 'state_update';
    content: string;
    state: StateUpdate;
}

export type Message =
  | UserMessage
  | EventMessage
  | TextMessage
  | ToolStartMessage
  | ToolEndMessage
  | ErrorMessage
  | ThinkingMessage
  | StateUpdateMessage;


export interface MessageFilter {
  [key: string]: boolean;
}


export interface Reference {
  id: string;
  name: string;
  friendly_name: string;
  description: string | null;
  type: string;
  value: string;
  version: string;
}

export interface ChatState {
  messages: Message[];
  isLoading: boolean;
  error: Error | null;
  filter: MessageFilter;
  isAutoLoad: boolean;
}

export interface ChatActions {
  addMessage: (message: Message) => void;
  setError: (error: Error | null) => void;
  setFilter: (filter: MessageFilter) => void;
  toggleAutoLoad: () => void;
}

export type ChatStore = ChatState & ChatActions;

export interface AnalysisRequest {
    settings: {
        debug_mode: boolean;
    };
    request: {
        user_id: string;
        query: string;
        workloads: any[];
    };
}

export interface AgentRun {
    run_id: string;
    status: 'in_progress' | 'awaiting_confirmation' | 'complete' | 'failed';
    current_step: number;
    total_steps: number;
    last_step_result?: Record<string, unknown>;
    final_report?: string;
    error?: Record<string, unknown>;
}

export interface AgentEvent {
    event: string;
    data: Record<string, unknown>;
}
