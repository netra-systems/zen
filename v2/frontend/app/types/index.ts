
export interface User {
    id: number;
    full_name?: string;
    email: string;
    picture?: string;
}

// --- Message Types ---

export type MessageRole = 'user' | 'assistant' | 'agent';

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


// --- Agent and Chat State ---

export interface MessageFilter {
    [key: string]: boolean;
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

export interface AgentState {
    messages: Message[];
    isThinking: boolean;
    error: Error | null;
}


// --- API and Server Communication ---

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

export interface ChatAnalysisRequest extends AnalysisRequest {
    request: {
        user_id: string;
        query: string;
        workloads: [
            {
                run_id: string;
                query: string;
                data_source: {
                    source_table: string;
                };
                time_range: {
                    start_time: string;
                    end_time: string;
                };
            }
        ];
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

export interface ToolOutputMessage {
    type: 'tool';
    content: string | { [key: string]: any };
    tool_call_id: string;
}

export interface StreamEvent {
    event: string;
    data: any;
    run_id: string;
}


// --- WebSocket Service Types ---

export enum WebSocketStatus {
    Connecting,
    Open,
    Closing,
    Closed,
    Error,
}

export interface WebSocketMessage {
    action: string;
    payload: any;
}

// --- Reference Picker ---

export interface Reference {
    id: string;
    name: string;
    friendly_name: string;
    description: string | null;
    type: string;
    value: string;
    version: string;
}

export interface AutoLoadSwitchProps {
  isAutoLoad: boolean;
  onAutoLoadChange: (value: boolean) => void;
}

export interface ChatHistoryProps {
  messages: Message[];
}

export interface MessageCardProps {
  message: Message;
  user?: {
    name?: string;
    picture?: string;
  }
}

export interface MessageFilterProps {
  onFilterChange: (filter: string) => void;
}

export interface InputField {
    id: string;
    name: string;
    label: string;
    type: string;
    required?: boolean;
    defaultValue?: string | number;
    options?: string[];
    step?: number;
}

export interface GenericInputProps {
    title: string;
    description: string;
    inputFields: InputField[];
    onSubmit: (data: Record<string, any>) => void;
    isLoading: boolean;
    submitButtonText: string;
    onClear?: () => void;
}

export interface ErrorDisplayProps {
  error: Error | string | null | undefined;
}

export interface ChatWindowProps {
    messages: Message[];
    onSendMessage: (message: string) => void;
    isLoading: boolean;
    initialQuery?: string;
    messageFilters: MessageFilter;
    setMessageFilters: (filters: MessageFilter) => void;
    exampleQueries?: string[];
}

export interface ChatMessageProps {
    message: Message;
}

export interface MessageContentProps {
    message: Message;
}

export interface MessageFilterControlProps {
    messageFilters: Set<MessageFilter>;
    setMessageFilters: React.Dispatch<React.SetStateAction<Set<MessageFilter>>>;
    showThinking: boolean;
    setShowThinking: React.Dispatch<React.SetStateAction<boolean>>;
}

export interface TodoListViewProps {
  todoList: StateUpdate;
}

export interface JsonTreeViewProps {
    data: any;
}

export interface Job {
    job_id: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    type: string;
    params: Record<string, unknown>;
    result_path?: string;
    summary?: { message: string };
    error?: string;
    last_updated?: number;
    progress?: number;
    total_tasks?: number;
    records_ingested?: number;
}

export interface JobStatusViewProps {
  job: Job | null;
}

export interface SyntheticDataGeneratorProps {
  onGenerationComplete: (destinationTable: string) => void;
}

export interface HeaderProps {
  toggleSidebar: () => void;
}

export interface RootLayoutProps {
  children: React.ReactNode;
}

export interface ControlButton {
    text: string;
    icon: React.ReactNode;
    onClick: () => void;
    variant: 'outline' | 'default' | 'destructive' | 'ghost' | 'link' | 'secondary';
}

export interface MessageOrchestratorProps {
    message: Message;
}
