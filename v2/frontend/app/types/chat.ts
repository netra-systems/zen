export type MessageRole = 'user' | 'assistant';

export interface StateUpdate {
  todo_list: string[];
  completed_steps: string[];
}

export interface ToolCall {
  name: string;
  args: Record<string, any>;
  id: string;
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
}
