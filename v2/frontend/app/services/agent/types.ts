
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
}

export interface ResponseMetadata {
    finish_reason?: string;
    model_name?: string;
}

export interface AIMessageChunk {
    content?: string;
    tool_calls?: ToolCall[];
    tool_call_chunks?: ToolCallChunk[];
}

export interface StreamEvent {
    event: string;
    data: any;
    run_id: string;
    name: string;
    tags: string[];
    metadata: Record<string, unknown>;
}

export interface BaseMessage {
    id: string;
    role: MessageRole;
    timestamp: string;
    type: MessageType;
    content: string;
}

export type MessageType =
    | 'text'
    | 'thinking'
    | 'tool_start'
    | 'tool_end'
    | 'state_update'
    | 'error'
    | 'user';

export interface TextMessage extends BaseMessage {
    type: 'text';
}

export interface ThinkingMessage extends BaseMessage {
    type: 'thinking';
}

export interface ToolStartMessage extends BaseMessage {
    type: 'tool_start';
    tool?: string;
    toolInput?: any;
    tool_calls?: ToolCall[];
}

export interface ToolEndMessage extends BaseMessage {
    type: 'tool_end';
    tool_outputs?: any[];
}

export interface StateUpdateMessage extends BaseMessage {
    type: 'state_update';
    state: StateUpdate;
}

export interface ErrorMessage extends BaseMessage {
    type: 'error';
    isError: true;
}

export interface UserMessage extends BaseMessage {
    type: 'user';
}

export type Message =
    | TextMessage
    | ThinkingMessage
    | ToolStartMessage
    | ToolEndMessage
    | StateUpdateMessage
    | ErrorMessage
    | UserMessage;

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
