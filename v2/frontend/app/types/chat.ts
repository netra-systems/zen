export type MessageRole = 'user' | 'agent';

export interface Artifact {
    type: string;
    content: string;
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
    content: string;
}

export interface EventMessage extends BaseMessage {
    type: 'event';
    name: string;
    data: Record<string, unknown>;
}

export interface ArtifactMessage extends BaseMessage {
    type: 'artifact';
    name: 'on_chain_start' | 'on_chain_end' | 'on_tool_start' | 'on_tool_end' | 'on_llm_start' | 'on_llm_end' | 'on_chat_model_start' | 'on_agent_action' | 'on_agent_finish';
    data: Record<string, unknown>;
}

export type Message = TextMessage | ThinkingMessage | EventMessage | ArtifactMessage;