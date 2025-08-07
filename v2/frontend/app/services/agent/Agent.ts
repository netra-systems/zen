import { getToken, getUserId } from '../../lib/user';
import { produce } from 'immer';
import { WebSocketClient, WebSocketStatus } from './WebSocketClient';
import { Message, StreamEvent, AnalysisRequest, ToolCallChunk, ToolOutput } from './types'; // Added ToolCallChunk, ToolOutput
import { UserMessage, ThinkingMessage, ToolStartMessage, ToolEndMessage, StateUpdateMessage, TextMessage } from './models';

// --- Type Definitions for Clarity ---
type AgentListener = (state: AgentState) => void;

interface AgentState {
    messages: Message[];
    isThinking: boolean;
    error: Error | null;
    // A map to buffer incomplete tool call arguments
    toolArgBuffers: { [key: string]: string };
}

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

    constructor() {
        this.webSocketClient = new WebSocketClient();
        this.webSocketClient.onMessage = this.handleMessage.bind(this);
        this.webSocketClient.onStatusChange = this.handleStatusChange.bind(this);
    }

    // --- Public API & State Management ---

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
            this.isInitialized = false; // Allow re-initialization
        }
    }

    public start(message: string): void {
        if (!this.isInitialized) {
             this.setState(draft => {
                draft.error = new Error('Agent is not connected. Please initialize first.');
             });
             return;
        }
        
        this.setState(draft => {
            draft.messages.push(new UserMessage(message));
            draft.messages.push(new ThinkingMessage()); // Add placeholder
            draft.isThinking = true;
            draft.error = null;
            draft.toolArgBuffers = {}; // Clear previous buffers
        });

        this.sendStartAgentRequest(message);
    }

    public stop(): void {
        this.webSocketClient.disconnect();
        this.setState(draft => {
            draft.isThinking = false;
        });
    }

    // --- WebSocket Event Handlers ---

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
            // Optionally, update state to reflect disconnection
            this.setState(draft => {
                if (draft.isThinking) {
                   draft.isThinking = false;
                   draft.error = new Error("Connection closed unexpectedly.");
                }
            });
        }
    }
    
    private handleMessage(eventData: StreamEvent): void {
        try {
            console.log("Received Event: ", eventData); // For debugging
            this.setState(draft => {
                this.processStreamEvent(draft, eventData);
            });
        } catch (error) {
            console.error("Failed to handle WebSocket message:", { eventData, error });
            this.setState(draft => {
                draft.error = new Error("Failed to process a server event.");
                draft.isThinking = false;
            });
        }
    }

    // --- Core Event Processing Logic ---

    private processStreamEvent(draft: AgentState, streamEvent: StreamEvent): void {
        const { event, data, run_id } = JSON.parse(streamEvent);
        //console.log(event, data, run_id)
        // Ensure a message exists for the current run to attach data to
        this.findOrCreateRunMessage(draft, run_id);

        switch (event) {
            case 'on_chat_model_stream':
                if (data.chunk?.content) {
                    this.processTextChunk(draft, run_id, data.chunk.content);
                }
                if (data.chunk?.tool_calls) {
                    // This event signals the *start* of tools, but chunks provide the content
                }
                if (data.chunk?.tool_call_chunks) {
                    data.chunk.tool_call_chunks.forEach((chunk: ToolCallChunk) => {
                        this.processToolChunk(draft, chunk);
                    });
                }
                break;

            case 'on_tool_end':
                if (data.output) {
                    this.processToolOutput(draft, data.output as ToolOutput);
                }
                break;

            case 'update_state':
            case 'on_chain_start': // Grouping similar state updates
                const stateData = event === 'update_state' ? data : data?.input;
                if (stateData) {
                    this.processStateUpdate(draft, run_id, stateData);
                }
                break;

            case 'run_complete':
                draft.isThinking = false;
                // Clean up any remaining thinking placeholders
                draft.messages = draft.messages.filter(m => m.type !== 'thinking');
                break;
            
            // Gracefully ignore events we don't handle
            case 'on_prompt_end':
            case 'on_chain_end':
                break;

            default:
                console.warn(`Unhandled event type: ${event}`);
                break;
        }
    }
    
    // --- Helper Functions for Processing Stream Data ---
    
    /** Finds the primary message associated with a run, or the last thinking message. */
    private findOrCreateRunMessage(draft: AgentState, run_id: string): Message {
        let message = draft.messages.find(m => m.id === run_id);
        if (message) return message;
        
        // If no message with run_id, find the last 'thinking' placeholder and assign the id
        const thinkingMessage = draft.messages.slice().reverse().find(m => m.type === 'thinking');
        if (thinkingMessage) {
            thinkingMessage.id = run_id;
            return thinkingMessage;
        }

        // Fallback: create a new message if none exists (should be rare)
        const newMessage = new ThinkingMessage();
        newMessage.id = run_id;
        draft.messages.push(newMessage);
        return newMessage;
    }

    private processTextChunk(draft: AgentState, run_id: string, content: string): void {
        let message = this.findOrCreateRunMessage(draft, run_id);

        // Morph the 'thinking' message into the first 'text' message
        if (message.type !== 'text') {
            Object.assign(message, new TextMessage(content));
            message.id = run_id; // Ensure ID is preserved
        } else {
            message.content += content;
        }
    }

    private processToolChunk(draft: AgentState, chunk: ToolCallChunk): void {
        if (!chunk.id) return; // Ignore chunks without an ID

        // Buffer the raw argument string
        draft.toolArgBuffers[chunk.id] = (draft.toolArgBuffers[chunk.id] || '') + chunk.args;

        // Find or create the message for this tool call
        let toolMessage = draft.messages.find(m => m.id === chunk.id) as ToolStartMessage;
        if (!toolMessage) {
            toolMessage = new ToolStartMessage(`Calling tool: ${chunk.name}`);
            toolMessage.id = chunk.id;
            toolMessage.tool = chunk.name;
            draft.messages.push(toolMessage);
        }
        
        // Attempt to parse the buffered string to create a nicely formatted input for display
        try {
            const parsedArgs = JSON.parse(draft.toolArgBuffers[chunk.id]);
            toolMessage.toolInput = JSON.stringify(parsedArgs, null, 2); // Pretty print
        } catch (e) {
            // If it fails to parse, it's incomplete. Display the raw buffer.
            toolMessage.toolInput = draft.toolArgBuffers[chunk.id];
        }
    }
    
    private processToolOutput(draft: AgentState, output: ToolOutput): void {
        const toolMessage = draft.messages.find(m => m.id === output.tool_call_id);
        if (toolMessage && toolMessage.type === 'tool_start') {
             // Morph the message into a ToolEndMessage
            Object.assign(toolMessage, new ToolEndMessage(
                toolMessage.content,
                (toolMessage as ToolStartMessage).tool,
                (toolMessage as ToolStartMessage).toolInput
            ));
            (toolMessage as ToolEndMessage).tool_outputs = [{
                tool_call_id: output.tool_call_id,
                content: typeof output.content === 'string' ? output.content : JSON.stringify(output.content, null, 2),
                is_error: false // Assuming success, can be extended for errors
            }];
            toolMessage.type = 'tool_end'; // Ensure type is correctly set
        }
    }

    private processStateUpdate(draft: AgentState, run_id: string, stateData: any): void {
        if (!stateData.todo_list) return;

        let message = this.findOrCreateRunMessage(draft, run_id);
        if (message.type !== 'state_update') {
             Object.assign(message, new StateUpdateMessage(''));
             message.id = run_id;
        }

        (message as StateUpdateMessage).state = {
            todo_list: stateData.todo_list,
            completed_steps: stateData.completed_steps || [],
        };
    }
}

export const agent = new Agent();