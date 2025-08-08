
import { getToken, getUserId } from '@/lib/user';
import { produce } from 'immer';
import { WebSocketClient, WebSocketStatus } from './WebSocketClient';
import { MessageFactory } from './MessageFactory';
import { 
    Message, 
    StreamEvent, 
    AnalysisRequest, 
    ToolCall, 
    ToolCallChunk, 
    ToolOutputMessage, 
    StateData,
    AgentState,
    AgentListener,
    AgentMessage,
    Tool,
    Todo,
    Reference
} from '@/app/types/index';

class Agent {
    private webSocketClient: WebSocketClient;
    private listeners: AgentListener[] = [];
    private state: AgentState = {
        messages: [],
        isThinking: false,
        error: null,
        toolArgBuffers: {},
    };
    private isInitialized = false;
    private reconnectTimer: NodeJS.Timeout | null = null;

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

        try {
            const token = await getToken();
            if (!token) {
                throw new Error('Authentication token not found.');
            }
            const runId = `run_${Date.now()}`;
            this.webSocketClient.connect(token, runId);
        } catch (error) {
            this.setState(draft => {
                draft.error = error instanceof Error ? error : new Error('Initialization failed.');
                draft.isThinking = false;
            });
            this.isInitialized = false; 
        }
    }

    public start(message: string, references?: Reference[]): void {
        if (!this.isInitialized) {
             this.setState(draft => {
                 draft.error = new Error('Agent is not connected. Please initialize first.');
             });
             return;
        }
        
        this.setState(draft => {
            draft.messages.push(MessageFactory.createUserMessage(message, references));
            draft.messages.push(MessageFactory.createThinkingMessage());
            draft.isThinking = true;
            draft.error = null;
            draft.toolArgBuffers = {};
        });

        this.sendStartAgentRequest(message, references);
    }

    public stop(): void {
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
        this.webSocketClient.disconnect();
        this.setState(draft => {
            draft.isThinking = false;
        });
    }

    private sendStartAgentRequest(message: string, references?: Reference[]): void {
        const userId = getUserId();
        if (!userId) {
            this.setState(draft => {
                draft.error = new Error('User ID not found.');
            });
            return;
        }
        const analysisRequest: AnalysisRequest = {
            settings: { debug_mode: false },
            request: { user_id: userId, query: message, workloads: [], references: references || [] },
        };
        this.webSocketClient.sendMessage({ action: 'start_agent', payload: analysisRequest });
    }

    private handleStatusChange(status: WebSocketStatus): void {
        if (status === WebSocketStatus.Error) {
            this.setState(draft => {
                draft.error = new Error('WebSocket connection error.');
                draft.isThinking = false;
            });
        }
        if (status === WebSocketStatus.Closed) {
            this.isInitialized = false;
            this.setState(draft => {
                if (draft.isThinking) {
                   draft.isThinking = false;
                   draft.error = new Error("Connection closed unexpectedly. Reconnecting...");
                }
            });
            this.reconnect();
        }
    }

    private reconnect(): void {
        if (this.reconnectTimer) return;
        this.reconnectTimer = setTimeout(() => {
            this.initialize();
            this.reconnectTimer = null;
        }, 5000);
    }
    
    private handleMessage(eventData: string): void {
        try {
            const event: StreamEvent = JSON.parse(eventData);
            this.setState(draft => {
                this.processStreamEvent(draft, event);
            });
        } catch (error) {
            console.error("Failed to handle WebSocket message:", { eventData, error });
            this.setState(draft => {
                draft.error = new Error("Failed to process a server event.");
                draft.isThinking = false;
            });
        }
    }

    private processStreamEvent(draft: AgentState, streamEvent: StreamEvent): void {
        const { event, data } = streamEvent;

        switch (event) {
            case 'on_agent_start':
                const agentMessage = MessageFactory.createAgentMessage(data.name, [], [], []);
                draft.messages.push(agentMessage);
                break;

            case 'on_chain_start':
                if (data?.input?.todo_list) {
                    this.processStateUpdate(draft, data.run_id, data.input);
                }
                break;

            case 'run_complete':
                draft.isThinking = false;
                draft.messages = draft.messages.filter(m => m.type !== 'thinking');
                break;

            case 'on_chat_model_stream':
                const chunk = data.chunk;
                if (chunk?.content) {
                    this.processTextChunk(draft, data.run_id, chunk.content);
                }
                if (chunk?.tool_calls) {
                    chunk.tool_calls.forEach((toolCall: ToolCall) => {
                        this.processToolStart(draft, toolCall.id, toolCall.name);
                    });
                }
                if (chunk?.tool_call_chunks) {
                    chunk.tool_call_chunks.forEach((toolChunk: ToolCallChunk) => {
                        this.processToolChunk(draft, toolChunk);
                    });
                }
                break;
            
            case 'on_chain_stream':
                if (data.chunk?.messages) {
                    data.chunk.messages.forEach((msg: ToolOutputMessage) => {
                        if (msg.type === 'tool') {
                            this.processToolOutput(draft, msg);
                        }
                    });
                }
                break;

            default:
                break;
        }
    }
    
    private findOrCreateAgentMessage(draft: AgentState): AgentMessage {
        let agentMessage = draft.messages.find(m => m.type === 'agent') as AgentMessage;
        if (!agentMessage) {
            agentMessage = MessageFactory.createAgentMessage("Agent", [], [], []);
            draft.messages.push(agentMessage);
        }
        return agentMessage;
    }

    private processTextChunk(draft: AgentState, run_id: string, content: string): void {
        const agentMessage = this.findOrCreateAgentMessage(draft);
        agentMessage.content = (agentMessage.content || '') + content;
    }

    private processToolStart(draft: AgentState, toolCallId: string, toolName: string): void {
        const agentMessage = this.findOrCreateAgentMessage(draft);
        agentMessage.tools.push({ name: toolName, input: {} });
    }
    
    private processToolChunk(draft: AgentState, chunk: ToolCallChunk): void {
        if (!chunk.id) return;

        draft.toolArgBuffers[chunk.id] = (draft.toolArgBuffers[chunk.id] || '') + chunk.args;

        const agentMessage = this.findOrCreateAgentMessage(draft);
        const tool = agentMessage.tools.find(t => t.name === chunk.name);
        if (tool) {
            try {
                const parsedArgs = JSON.parse(draft.toolArgBuffers[chunk.id]);
                tool.input = parsedArgs;
            } catch (err) {
                tool.input = { raw: draft.toolArgBuffers[chunk.id] };
            }
        }
    }
    
    private processToolOutput(draft: AgentState, output: ToolOutputMessage): void {
        const agentMessage = this.findOrCreateAgentMessage(draft);
        const tool = agentMessage.tools.find(t => t.name === output.tool_call_id);
        if (tool) {
            tool.output = typeof output.content === 'string' ? { content: output.content } : output.content;
        }
    }

    private processStateUpdate(draft: AgentState, run_id: string, stateData: StateData): void {
        const agentMessage = this.findOrCreateAgentMessage(draft);
        if (stateData.todo_list) {
            agentMessage.todos = stateData.todo_list.map(item => ({ description: item, state: 'pending' }));
        }
    }
}

export const agent = new Agent();
