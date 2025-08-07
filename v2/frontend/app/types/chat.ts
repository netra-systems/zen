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
        }
    };
    response_metadata?: ResponseMetadata;
    id?: string;
    tool_calls?: ToolCall[];
    usage_metadata?: UsageMetadata;
    tool_call_chunks?: ToolCallChunk[];
}

export interface Message {
  id: string;
  role: MessageRole;
  type: 'text' | 'thinking' | 'error' | 'tool_start' | 'tool_end' | 'state_update' | 'tool_code';
  content: string;
  tool?: string;
  toolInput?: any;
  toolOutput?: any;
  isError?: boolean;
  state?: StateUpdate;
  rawChunk?: AIMessageChunk;
}