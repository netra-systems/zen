import { getToken, getUserId } from '../../lib/user';
import { produce } from 'immer';
import { WebSocketClient, WebSocketStatus } from './WebSocketClient';
import { Message, StreamEvent, AnalysisRequest, TextMessage } from './types';
import { UserMessage, ThinkingMessage, ToolStartMessage, ToolEndMessage, StateUpdateMessage } from './models';

type AgentListener = (state: AgentState) => void;

interface AgentState {
    messages: Message[];
    isThinking: boolean;
    error: Error | null;
}

class Agent {
    private webSocketClient: WebSocketClient;
    private listeners: AgentListener[] = [];
    private state: AgentState = {
        messages: [],
        isThinking: false,
        error: null,
    };
    private isInitialized = false;

    constructor() {
        this.webSocketClient = new WebSocketClient();
        this.webSocketClient.onMessage = this.handleMessage.bind(this);
        this.webSocketClient.onStatusChange = this.handleStatusChange.bind(this);
    }

    public subscribe(listener: AgentListener): () => void {
        this.listeners.push(listener);
        listener(this.state);
        return () => {
            this.listeners = this.listeners.filter(l => l !== listener);
        };
    }

    private notify(): void {
        this.listeners.forEach(listener => listener(this.state));
    }

    private setState(updater: (draft: AgentState) => void): void {
        this.state = produce(this.state, updater);
        this.notify();
    }

    public async initialize(): Promise<void> {
        if (this.isInitialized) return;
        this.isInitialized = true;

        const token = await getToken();
        if (!token) {
            this.setState(draft => {
                draft.error = new Error('Authentication token not found.');
            });
            this.isInitialized = false; // Allow re-initialization
            return;
        }
        const runId = `run_${Date.now()}`;
        this.webSocketClient.connect(token, runId);
    }

    public start(message: string): void {
        this.addUserMessage(message);
        this.sendStartAgentRequest(message);
    }

    public stop(): void {
        this.webSocketClient.disconnect();
    }

    private addUserMessage(message: string): void {
        this.setState(draft => {
            draft.messages.push(new UserMessage(message));
        });
    }

    private sendStartAgentRequest(message: string): void {
        const userId = getUserId();
        if (!userId) {
            this.setState(draft => {
                draft.error = new Error('User ID not found.');
            });
            return;
        }
        const analysisRequest: AnalysisRequest = {
            settings: { debug_mode: false },
            request: { user_id: userId, query: message, workloads: [] },
        };
        this.webSocketClient.sendMessage({ action: 'start_agent', payload: analysisRequest });
        this.setState(draft => {
            draft.isThinking = true;
        });
    }

    private handleMessage(event: MessageEvent): void {
        const streamEvent: StreamEvent = event;
        if (streamEvent.event === 'run_complete') {
            this.setState(draft => {
                draft.isThinking = false;
            });
            return;
        }
        this.setState(draft => {
            this.processStreamEvent(draft, streamEvent);
        });
    }

    private handleStatusChange(status: WebSocketStatus): void {
        if (status === WebSocketStatus.Error) {
            this.setState(draft => {
                draft.error = new Error('WebSocket connection error.');
            });
        }
        if (status === WebSocketStatus.Closed) {
            this.isInitialized = false;
        }
    }

    private processStreamEvent(draft: AgentState, event: StreamEvent): void {
        const { event: eventName, data, run_id } = event;
        this.updateMessage(draft, eventName, data, run_id);
    }

    private updateMessage(draft: AgentState, eventName: string, data: any, run_id: string): void {
        let message = draft.messages.find((m) => m.id === run_id);

        if (!message) {
            const newMessage = new ThinkingMessage();
            newMessage.id = run_id;
            draft.messages.push(newMessage);
            message = newMessage;
        }

        if (message.type === 'thinking') {
            if (eventName === 'on_chat_model_stream' && data.chunk?.content) {
                message.type = 'text';
            } else {
                message.type = this.getMessageType(eventName);
            }
        }

        switch (eventName) {
            case 'on_chain_start':
                this.updateStateMessage(message as StateUpdateMessage, data.input);
                break;
            case 'on_chat_model_stream':
                const chunk = data.chunk;
                if (chunk?.tool_call_chunks) {
                    this.updateToolCode(draft.messages, chunk);
                } else if (chunk?.content) {
                    message.content = (message.content || '') + chunk.content;
                }
                break;
            case 'on_tool_start':
                this.updateToolStart(message as ToolStartMessage, data);
                break;
            case 'on_tool_end':
                this.updateToolEnd(message as ToolEndMessage, data);
                break;
            case 'on_chain_end':
                this.updateToolEnd(message as ToolEndMessage, data);
                break;
            case 'update_state':
                this.updateStateMessage(message as StateUpdateMessage, data);
                break;
        }
    }

    private getMessageType(eventName: string): Message['type'] {
        const typeMap: { [key: string]: Message['type'] } = {
            on_chain_start: 'state_update',
            on_chain_end: 'tool_end',
            on_chat_model_stream: 'tool_start',
            on_tool_end: 'tool_end',
            on_tool_start: 'tool_start',
            update_state: 'state_update',
        };
        return typeMap[eventName];
    }

    private updateStateMessage(message: StateUpdateMessage, data: any): void {
        if (data.todo_list) {
            message.state = {
                todo_list: data.todo_list,
                completed_steps: data.completed_steps || [],
            };
        }
    }

    private updateToolStart(message: ToolStartMessage, data: any): void {
        if (data.name) {
            message.tool = data.name;
        }
        if (data.input) {
            message.toolInput = data.input;
        }
    }

    private updateToolCode(messages: Message[], chunk: any): void {
        if (chunk.tool_call_chunks && chunk.tool_call_chunks.length > 0) {
            for (const toolCallChunk of chunk.tool_call_chunks) {
                const existingMessageIndex = messages.findIndex(msg => msg.id === toolCallChunk.id);

                if (existingMessageIndex !== -1) {
                    const existingMessage = messages[existingMessageIndex] as ToolStartMessage;
                    let currentArgs = existingMessage.toolInput || '';
                    if (typeof currentArgs !== 'string') {
                        currentArgs = JSON.stringify(currentArgs);
                    }
                    const newArgsChunk = toolCallChunk.args || '';
                    messages[existingMessageIndex] = {
                        ...existingMessage,
                        toolInput: currentArgs + newArgsChunk,
                    } as ToolStartMessage;
                } else {
                    const newMessage = new ToolStartMessage(`Starting tool ${toolCallChunk.name}...`);
                    newMessage.id = toolCallChunk.id;
                    newMessage.tool = toolCallChunk.name;
                    newMessage.toolInput = toolCallChunk.args || '';
                    messages.push(newMessage);
                }
            }
        }
    }

    private updateToolEnd(message: ToolEndMessage, data: any): void {
        if (data.output) {
            message.tool_outputs = [...(message.tool_outputs || []), {
                tool_call_id: data.run_id,
                content: typeof data.output === 'string' ? data.output : JSON.stringify(data.output),
                is_error: data.is_error || false,
            }];
        }
    }
}

export const agent = new Agent();