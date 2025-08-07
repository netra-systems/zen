import {
    UserMessage,
    ThinkingMessage,
    TextMessage,
    ToolStartMessage,
    ToolEndMessage,
    StateUpdateMessage,
    MessageRole,
    StateUpdate
} from '@/app/types/index';

export class MessageFactory {
    static createUserMessage(content: string): UserMessage {
        return {
            type: 'user',
            id: `user_${Date.now()}`,
            role: 'user' as MessageRole,
            content: content,
        };
    }

    static createThinkingMessage(): ThinkingMessage {
        return {
            type: 'thinking',
            id: `thinking_${Date.now()}`,
            role: 'agent' as MessageRole,
            content: 'Thinking...',
        };
    }

    static createTextMessage(content: string, id?: string): TextMessage {
        return {
            type: 'text',
            id: id || `text_${Date.now()}`,
            role: 'agent'as MessageRole,
            content: content,
        };
    }

    static createToolStartMessage(content: string, tool: string, toolInput: Record<string, unknown>, id?: string): ToolStartMessage {
        return {
            type: 'tool_start',
            id: id || `tool_start_${Date.now()}`,
            role: 'agent' as MessageRole,
            content: content,
            tool: tool,
            toolInput: toolInput,
        };
    }

    static createToolEndMessage(content: string, tool: string, toolInput: Record<string, unknown>, toolOutput: Record<string, unknown>, id?: string): ToolEndMessage {
        return {
            type: 'tool_end',
            id: id || `tool_end_${Date.now()}`,
            role: 'agent' as MessageRole,
            content: content,
            tool: tool,
            toolInput: toolInput,
            toolOutput: toolOutput,
        };
    }

    static createStateUpdateMessage(content: string, state: StateUpdate, id?: string): StateUpdateMessage {
        return {
            type: 'state_update',
            id: id || `state_update_${Date.now()}`,
            role: 'agent' as MessageRole,
            content: content,
            state: state,
        };
    }
}