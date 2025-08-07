export type MessageRole = 'user' | 'agent';

export interface Artifact {
    type: string;
    content: any;
    data: any;
}

export interface BaseMessage {
    id: string;
    role: MessageRole;
    timestamp: string;
    artifact?: Artifact;
}

export interface TextMessage extends BaseMessage {
    type: 'text';
    content: string;
}

export interface ThinkingMessage extends BaseMessage {
    type: 'thinking';
}

export type EventName =
  | 'on_chain_start'
  | 'on_chain_end'
  | 'on_chain_stream'
  | 'on_prompt_start'
  | 'on_prompt_end'
  | 'on_chat_model_start'
  | 'on_chat_model_stream'
  | 'on_chat_model_end'
  | 'on_tool_start'
  | 'on_tool_end'
  | 'on_agent_action'
  | 'on_agent_finish'
  | 'run_complete';

export interface EventMessage extends BaseMessage {
    type: 'event';
    name: EventName;
    data: Record<string, unknown>;
}

export interface ToolCall {
    name: string;
    args: Record<string, unknown>;
    id: string;
    type: 'tool_call';
}

export interface ToolOutput {
    tool_call_id: string;
    content: string;
    is_error: boolean;
}

export interface StateUpdate {
    todo_list: string[];
    completed_steps: string[];
}

export interface ArtifactMessage extends BaseMessage {
    type: 'artifact';
    name: EventName;
    data: any;
    content?: string;
    tool_calls?: ToolCall[];
    tool_outputs?: ToolOutput[];
    state_updates?: StateUpdate;
}

export type Message = TextMessage | ThinkingMessage | EventMessage | ArtifactMessage;

export interface ChatState {
    messages: Message[];
    isLoading: boolean;
    error: Error | null;
}