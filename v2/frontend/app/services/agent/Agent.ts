import { getToken, getUserId } from '../../lib/user';
import { produce } from 'immer';
import { WebSocketClient, WebSocketStatus } from './WebSocketClient';
import { Message, StreamEvent, AnalysisRequest } from './types';
import { UserMessage, ThinkingMessage, ToolStartMessage, ToolEndMessage, StateUpdateMessage, TextMessage } from './models';

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
            // Add a temporary thinking message for the main run
            draft.messages.push(new ThinkingMessage());
        });
    }

    private handleMessage(event_json_already_parsed: MessageEvent): void {
        try {
            const streamEvent: StreamEvent = event_json_already_parsed
            console.log(streamEvent); // For debugging

            if (streamEvent.event === 'run_complete') {
                this.setState(draft => {
                    draft.isThinking = false;
                });
                return;
            }

            this.setState(draft => {
                this.processStreamEvent(draft, streamEvent);
            });

        } catch (error) {
            console.error("Failed to handle WebSocket message this is NOT a JSON issue probably:", event_json_already_parsed, error);
            this.setState(draft => {
                draft.error = new Error("Failed to process server event.");
            });
        }
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
        }
    }

    private processStreamEvent(draft: AgentState, streamEvent: StreamEvent): void {
        const { event, data, run_id } = streamEvent;

        // Find the main message for this run, which might still be a 'thinking' message
        let mainMessage = draft.messages.find(m => m.id === run_id || (m.type === 'thinking' && !m.id));
        if (mainMessage && !mainMessage.id) {
            mainMessage.id = run_id; // Assign the run_id to the initial 'thinking' message
        }

        // --- Event Handlers ---

        // 1. Text Stream: Handles generating a standard text response.
        if (event === 'on_chat_model_stream' && data.chunk?.content) {
            if (!mainMessage) {
                mainMessage = new TextMessage(data.chunk.content);
                mainMessage.id = run_id;
                draft.messages.push(mainMessage);
            } else if (mainMessage.type !== 'text') {
                // Morph the 'thinking' message into a 'text' message
                mainMessage.type = 'text';
                mainMessage.content = data.chunk.content;
            } else {
                mainMessage.content = (mainMessage.content || '') + data.chunk.content;
            }
            return;
        }

        // 2. Tool Call Initiation: Creates new messages for each tool the agent decides to use.
        if (event === 'on_chat_model_stream' && data.chunk?.tool_calls) {
            for (const toolCall of data.chunk.tool_calls) {
                if (!draft.messages.some(m => m.id === toolCall.id)) {
                    const newMessage = new ToolStartMessage(`Calling tool: ${toolCall.name}`);
                    newMessage.id = toolCall.id; // Use the unique tool_call_id
                    newMessage.tool = toolCall.name;
                    newMessage.toolInput = toolCall.args ? JSON.stringify(toolCall.args, null, 2) : '';
                    draft.messages.push(newMessage);
                }
            }
            return;
        }
        
        // 3. Tool Argument Streaming: Streams arguments to a tool call message.
        if (event === 'on_chat_model_stream' && data.chunk?.tool_call_chunks) {
            this.updateToolCode(draft.messages, data.chunk);
            return;
        }

        // 4. Tool Call Completion: Finds a tool message by its ID and updates it with the result.
        const toolOutputMessages = data.output?.messages || data.chunk?.messages;
        if (Array.isArray(toolOutputMessages)) {
            for (const msg of toolOutputMessages) {
                if (msg.type === 'tool' && msg.tool_call_id) {
                    const toolMessage = draft.messages.find(m => m.id === msg.tool_call_id) as ToolStartMessage;
                    if (toolMessage) {
                        // Update the existing message with the result.
                        toolMessage.type = 'tool_end';
                        (toolMessage as ToolEndMessage).tool_outputs = [{
                            tool_call_id: msg.tool_call_id,
                            content: msg.content,
                            is_error: false
                        }];
                    }
                }
            }
            return;
        }

        // 5. State/Plan Updates: Updates a message with the agent's current plan.
        if ((event === 'on_chain_start' && data?.input?.todo_list) || event === 'update_state') {
            const stateData = event === 'update_state' ? data : data.input;
            if (!mainMessage) {
                mainMessage = new StateUpdateMessage('');
                mainMessage.id = run_id;
                draft.messages.push(mainMessage);
            } else if (mainMessage.type !== 'state_update') {
                mainMessage.type = 'state_update';
            }
            this.updateStateMessage(mainMessage as StateUpdateMessage, stateData);
        }
    }

    private updateStateMessage(message: StateUpdateMessage, data: any): void {
        if (data.todo_list) {
            message.state = {
                todo_list: data.todo_list,
                completed_steps: data.completed_steps || [],
            };
        }
    }
    
    private updateToolCode(messages: Message[], chunk: any): void {
        if (chunk.tool_call_chunks) {
            for (const toolCallChunk of chunk.tool_call_chunks) {
                let toolMessage = messages.find(msg => msg.id === toolCallChunk.id) as ToolStartMessage;

                // Create the message if it doesn't exist yet
                if (!toolMessage) {
                    const newMessage = new ToolStartMessage('');
                    newMessage.id = toolCallChunk.id;
                    newMessage.tool = toolCallChunk.name;
                    newMessage.toolInput = toolCallChunk.args || '';
                    messages.push(newMessage);
                } else {
                    // Otherwise, append the streamed arguments
                    let currentArgs = toolMessage.toolInput || '';
                    toolMessage.toolInput = currentArgs + (toolCallChunk.args || '');
                }
            }
        }
    }
}

export const agent = new Agent();