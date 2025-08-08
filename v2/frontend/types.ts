export interface WebSocketMessage {
    event: string;
    data: any;
    run_id: string;
}

export interface RunCompleteMessage extends WebSocketMessage {
    event: "run_complete";
}

export interface ErrorData {
    type: string;
    message: string;
}

export interface ErrorMessage extends WebSocketMessage {
    event: "error";
    data: ErrorData;
}

export interface StreamEventMessage extends WebSocketMessage {
    event: "stream_event";
    event_type: string;
}

export interface ToolStatus {
    tool_name: string;
    status: string;
    message?: string;
}

export interface AgentUpdateData {
    agent: string;
    messages: any[];
    tools_status: ToolStatus[];
    todos: any[];
}

export interface AgentUpdateMessage extends WebSocketMessage {
    event: "agent_update";
    data: AgentUpdateData;
}

export interface ToolError {
    tool_name: string;
    error_message: string;
}

export interface ChatMessageData {
    sub_agent_name?: string;
    tools_used?: string[];
    ai_message?: string;
    tool_todo_list?: any[];
    tool_errors?: ToolError[];
    user_message?: string;
    user_references?: any[];
}

export interface ChatMessage extends WebSocketMessage {
    event: "chat_message";
    data: ChatMessageData;
}