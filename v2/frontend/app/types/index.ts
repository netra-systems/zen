
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
    references?: Reference[];
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

export interface Tool {
    name: string;
    input: Record<string, unknown>;
    output?: Record<string, unknown>;
    error?: string;
}

export interface Todo {
    description: string;
    state: 'pending' | 'in_progress' | 'completed' | 'error';
}

export interface AgentMessage extends BaseMessage {
    type: 'agent';
    subAgentName: string;
    content?: string;
    tools: Tool[];
    todos: Todo[];
    toolErrors: string[];
}

export interface ToolStartMessage extends BaseMessage {
    type: 'tool_start';
    content: string;
    tool: string;
    toolInput: Record<string, unknown>;
    usageMetadata?: UsageMetadata;
    responseMetadata?: ResponseMetadata;
}

export interface ToolEndMessage extends BaseMessage {
    type: 'tool_end';
    content: string;
    tool: string;
    toolInput: Record<string, unknown>;
    toolOutput: Record<string, unknown>;
    usageMetadata?: UsageMetadata;
    responseMetadata?: ResponseMetadata;
}

export interface ToolEndErrorMessage extends BaseMessage {
    type: 'tool_end';
    content: string;
    tool: string;
    toolInput: Record<string, unknown>;
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
    toolInput?: Record<string, unknown>;
    toolOutput?: Record<string, unknown>;
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
    | StateUpdateMessage
    | AgentMessage;


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
    toolArgBuffers: { [key: string]: string };
}

export interface UseAgentReturn {
    startAgent: (message: string, references?: Reference[]) => void;
    stopAgent: () => void;
    messages: Message[];
    showThinking: boolean;
    error: Error | null;
}

export type AgentListener = (state: AgentState) => void;


// --- API and Server Communication ---

export interface Workload {
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

export interface AnalysisRequest {
    settings: {
        debug_mode: boolean;
    };
    request: {
        user_id: string;
        query: string;
        workloads: Workload[];
        references: Reference[];
    };
}

export interface ChatAnalysisRequest extends AnalysisRequest {
    request: {
        user_id: string;
        query: string;
        workloads: Workload[];
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
    args: Record<string, unknown>;
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
    response_metadata?: ResponseMetadata;
    id?: string;
    tool_calls?: ToolCall[];
    usage_metadata?: UsageMetadata;
    tool_call_chunks?: ToolCallChunk[];
}

export interface StreamData {
    run_id: string;
    name: string;
    input?: Record<string, unknown>;
    chunk?: AIMessageChunk;
    messages?: Record<string, unknown>[];
}

export interface ServerEvent {
    event: string;
    data: StreamData;
    run_id?: string;
}

export interface StateData {
    todo_list: string[];
    completed_steps: string[];
}

export interface StreamEventData {
    run_id: string;
    input?: Record<string, unknown>;
    chunk?: Record<string, unknown>;
    messages?: Record<string, unknown>[];
}

export interface ToolOutputMessage {
    type: 'tool';
    content: string | { [key: string]: unknown };
    tool_call_id: string;
}

export interface StreamEvent {
    event: string;
    data: StreamData;
    run_id: string;
}


// --- WebSocket Service Types ---

export enum WebSocketStatus {
    Connecting = 'Connecting',
    Open = 'Open',
    Closing = 'Closing',
    Closed = 'Closed',
    Error = 'Error',
}

export interface WebSocketMessage {
    type: string;
    payload: Record<string, unknown>;
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
    onSubmit: (data: Record<string, string | number>) => void;
    isLoading: boolean;
    submitButtonText: string;
    onClear?: () => void;
}

export interface ErrorDisplayProps {
  error: Error | string | null | undefined;
}

export interface ChatWindowProps {
    messages: Message[];
    onSendMessage: (message: string, references?: Reference[]) => void;
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
    messageFilters: MessageFilter;
    setMessageFilters: (filters: MessageFilter) => void;
    showThinking: boolean;
    setShowThinking: React.Dispatch<React.SetStateAction<boolean>>;
}

export interface TodoListViewProps {
  todoList: StateUpdate;
}

export interface JsonTreeViewProps {
    data: Record<string, unknown>;
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

export interface AppWithLayoutProps {
  children: React.ReactNode;
}

export interface ControlButton {
    text: string;
    icon: React.ReactNode;
    onClick: () => void;
    variant: 'outline' | 'default' | 'destructive' | 'ghost' | 'link' | 'secondary';
}

export interface NavItem {
    href: string;
    icon: React.ReactNode;
    label: string;
    disabled?: boolean;
}

export interface MessageOrchestratorProps {
    messages: Message[];
}

export interface MessageOrchestratorProps {
    message: Message;
}

export interface AgentMessageCardProps {
    message: AgentMessage;
}

export interface UserMessageCardProps {
    message: UserMessage;
}

export interface ThinkingProps {
    message: ThinkingMessage;
}

export interface ErrorCardProps {
    message: ErrorMessage;
}

export interface EventCardProps {
    message: EventMessage;
}

export interface TextCardProps {
    message: TextMessage;
}

export interface ToolStartCardProps {
    message: ToolStartMessage;
}

export interface ToolEndCardProps {
    message: ToolEndMessage;
}

export interface StateUpdateCardProps {
    message: StateUpdateMessage;
}
