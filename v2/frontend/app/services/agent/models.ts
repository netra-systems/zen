import { v4 as uuidv4 } from 'uuid';
import { Message, MessageRole, MessageType, StateUpdate, ToolCall } from './types';

export class BaseMessage implements Message {
    id: string;
    role: MessageRole;
    timestamp: string;
    type: MessageType;
    content: string;

    constructor(role: MessageRole, type: MessageType, content: string = '') {
        this.id = uuidv4();
        this.role = role;
        this.timestamp = new Date().toISOString();
        this.type = type;
        this.content = content;
    }
}

export class UserMessage extends BaseMessage {
    constructor(content: string) {
        super('user', 'user', content);
    }
}

export class ThinkingMessage extends BaseMessage {
    constructor() {
        super('agent', 'thinking');
    }
}

export class TextMessage extends BaseMessage {
    constructor(content: string) {
        super('agent', 'text', content);
    }
}

export class ToolStartMessage extends BaseMessage {
    tool?: string;
    toolInput?: any;
    tool_calls?: ToolCall[];

    constructor(tool?: string, toolInput?: any, tool_calls?: ToolCall[]) {
        super('agent', 'tool_start');
        this.tool = tool;
        this.toolInput = toolInput;
        this.tool_calls = tool_calls;
    }
}

export class ToolEndMessage extends BaseMessage {
    tool_outputs?: any[];

    constructor(tool_outputs?: any[]) {
        super('agent', 'tool_end');
        this.tool_outputs = tool_outputs;
    }
}

export class StateUpdateMessage extends BaseMessage {
    state: StateUpdate;

    constructor(state: StateUpdate) {
        super('agent', 'state_update');
        this.state = state;
    }
}