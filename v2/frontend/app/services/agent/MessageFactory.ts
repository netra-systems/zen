
import {
    UserMessage,
    ThinkingMessage,
    TextMessage,
    ToolStartMessage,
    ToolEndMessage,
    StateUpdateMessage,
    AgentMessage,
    ErrorMessage,
    EventMessage,
    MessageRole,
    StateUpdate,
    Tool,
    Todo,
    Reference
} from '@/app/types/index';

export class MessageFactory {
    static createUserMessage(content: string, references?: Reference[]): UserMessage {
        return {
            type: 'user',
            id: `user_${Date.now()}`,
            role: 'user' as MessageRole,
            content: content,
            references: references
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

    static createToolStartMessage(tool: string, toolInput: Record<string, unknown>): ToolStartMessage {
        return {
            type: 'tool_start',
            id: `tool_start_${Date.now()}`,
            role: 'agent' as MessageRole,
            content: `Starting tool: ${tool}`,
            tool: tool,
            toolInput: toolInput,
        };
    }

    static createToolEndMessage(tool: string, toolInput: Record<string, unknown>, toolOutput: Record<string, unknown>): ToolEndMessage {
        return {
            type: 'tool_end',
            id: `tool_end_${Date.now()}`,
            role: 'agent' as MessageRole,
            content: `Tool finished: ${tool}`,
            tool: tool,
            toolInput: toolInput,
            toolOutput: toolOutput,
        };
    }

    static createStateUpdateMessage(state: StateUpdate): StateUpdateMessage {
        return {
            type: 'state_update',
            id: `state_update_${Date.now()}`,
            role: 'agent' as MessageRole,
            content: 'Updating state...',
            state: state,
        };
    }

    static createAgentMessage(subAgentName: string, tools: Tool[], todos: Todo[], toolErrors: string[], content?: string): AgentMessage {
        return {
            type: 'agent',
            id: `agent_${Date.now()}`,
            role: 'agent' as MessageRole,
            subAgentName: subAgentName,
            tools: tools,
            todos: todos,
            toolErrors: toolErrors,
            content: content,
        };
    }

    static createErrorMessage(content: string): ErrorMessage {
        return {
            type: 'error',
            id: `error_${Date.now()}`,
            role: 'agent' as MessageRole,
            content: content,
            isError: true,
        };
    }

    static createEventMessage(eventName: string): EventMessage {
        return {
            type: 'event',
            id: `event_${Date.now()}`,
            role: 'agent' as MessageRole,
            content: `Event: ${eventName}`,
            eventName: eventName,
        };
    }
}
