export type MessageRole = 'user' | 'assistant';

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
  data: any;
  run_id?: string;
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

export interface Message {
  id: string;
  role: MessageRole;
  type: 'text' | 'thinking' | 'error' | 'tool_start' | 'tool_end' | 'state_update' | 'tool_code' | 'user' | 'assistant' | 'event';
  content: string;
  tool?: string;
  toolInput?: any;
  toolOutput?: any;
  isError?: boolean;
  state?: StateUpdate;

  // To store all data from the server event
  rawServerEvent?: ServerEvent;

  // For easier access to common data points
  usageMetadata?: UsageMetadata;
  responseMetadata?: ResponseMetadata;
  toolCalls?: ToolCall[];
}

export interface MessageFilter {
  [key: string]: boolean;
}
