export type MessageRole = 'user' | 'agent';

export interface BaseMessage {
  id: string;
  role: MessageRole;
  timestamp: string;
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
  | 'run_complete'
  | 'update_state';

export interface ToolCall {
  name: string;
  args: Record<string, any>;
  id: string;
  type: 'tool_call';
  is_error?: boolean;
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

export interface OnChainStartData {
  input?: {
    messages?: any[];
    workloads?: any[];
    todo_list?: string[];
    completed_steps?: string[];
    status?: string;
    events?: any[];
  };
}

export interface OnToolStartData {
  input?: Record<string, any>;
}

export interface OnToolEndData {
  output?: string;
  is_error?: boolean;
}

export interface OnChatModelStreamData {
  chunk?: {
    content?: string;
    tool_calls?: ToolCall[];
  };
}

export interface RunCompleteData {
  status: string;
}

export interface StreamEvent {
  event: EventName;
  data:
    | OnChainStartData
    | OnToolStartData
    | OnToolEndData
    | OnChatModelStreamData
    | RunCompleteData
    | Record<string, any>;
  run_id: string;
  name?: string;
  tags?: string[];
  metadata?: Record<string, any>;
}

export interface EventMessage extends BaseMessage {
  type: 'event';
  event: 'agent_started';
}

export type Message = TextMessage | ThinkingMessage | ArtifactMessage | EventMessage;

export interface ChatState {
  messages: Message[];
  isLoading: boolean;
  error: Error | null;
}

export interface ChatContextType extends ChatState {
  sendMessage: (message: string) => void;
}