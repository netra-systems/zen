
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

        if (draft.messages.some(m => m.type === 'thinking')) {
            draft.messages = draft.messages.filter(m => m.type !== 'thinking');
        }

        switch (event) {
            case 'on_agent_start':
                draft.messages.push(MessageFactory.createAgentMessage(data.name, [], [], []));
                break;

            case 'on_chain_start':
                if (data?.input?.todo_list) {
                    this.updateTodoList(draft, data.input as StateData);
                }
                break;

            case 'on_tool_start':
                this.startTool(draft, data.name, data.input as Record<string, unknown>);
                break;

            case 'on_tool_end':
                this.endTool(draft, data.name, data.output as Record<string, unknown>);
                break;

            case 'on_error':
                this.handleError(draft, data.error as string);
                break;

            case 'run_complete':
                draft.isThinking = false;
                break;

            case 'on_chat_model_stream':
                const chunk = data.chunk;
                if (chunk?.content) {
                    this.updateAgentContent(draft, chunk.content);
                }
                if (chunk?.tool_call_chunks) {
                    chunk.tool_call_chunks.forEach((toolChunk: ToolCallChunk) => {
                        this.updateToolInput(draft, toolChunk);
                    });
                }
                break;

            default:
                break;
        }
    }
    
    private findOrCreateAgentMessage(draft: AgentState, subAgentName?: string): AgentMessage {
        let agentMessage = draft.messages.slice().reverse().find(m => m.type === 'agent') as AgentMessage | undefined;
        
        if (!agentMessage) {
            agentMessage = MessageFactory.createAgentMessage(subAgentName || "Agent", [], [], []);
            draft.messages.push(agentMessage);
        }
        return agentMessage;
    }

    private updateAgentContent(draft: AgentState, content: string): void {
        const agentMessage = this.findOrCreateAgentMessage(draft);
        agentMessage.content = (agentMessage.content || '') + content;
    }

    private startTool(draft: AgentState, toolName: string, toolInput: Record<string, unknown>): void {
        const agentMessage = this.findOrCreateAgentMessage(draft);
        agentMessage.tools.push({ name: toolName, input: toolInput });
    }
    
    private endTool(draft: AgentState, toolName: string, toolOutput: Record<string, unknown>): void {
        const agentMessage = this.findOrCreateAgentMessage(draft);
        const tool = agentMessage.tools.find(t => t.name === toolName && !t.output);
        if (tool) {
            tool.output = toolOutput;
        }
    }

    private updateToolInput(draft: AgentState, chunk: ToolCallChunk): void {
        if (!chunk.id) return;

        draft.toolArgBuffers[chunk.id] = (draft.toolArgBuffers[chunk.id] || '') + chunk.args;

        const agentMessage = this.findOrCreateAgentMessage(draft);
        const tool = agentMessage.tools.find(t => t.name === chunk.name && !t.output);
        if (tool) {
            try {
                const parsedArgs = JSON.parse(draft.toolArgBuffers[chunk.id]);
                tool.input = parsedArgs;
            } catch (err) {
                // Incomplete JSON, wait for more chunks
            }
        }
    }

    private updateTodoList(draft: AgentState, stateData: StateData): void {
        const agentMessage = this.findOrCreateAgentMessage(draft);
        if (stateData.todo_list) {
            agentMessage.todos = stateData.todo_list.map(item => ({ description: item, state: 'pending' }));
        }
    }

    private handleError(draft: AgentState, error: string): void {
        const agentMessage = this.findOrCreateAgentMessage(draft);
        agentMessage.toolErrors.push(error);
    }
}

export const agent = new Agent();
