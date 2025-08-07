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
    ToolStartMessage,
    StateData,
    StateUpdateMessage
} from '@/app/types/index';

// --- Agent Class ---

type AgentListener = (state: AgentState) => void;

interface AgentState {
    messages: Message[];
    isThinking: boolean;
    error: Error | null;
    // A map to buffer incomplete tool call arguments as they stream in
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
            draft.messages.push(MessageFactory.createUserMessage(message));
            draft.messages.push(MessageFactory.createThinkingMessage()); // Add placeholder for the agent's response
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
            this.setState(draft => {
                if (draft.isThinking) {
                   draft.isThinking = false;
                   draft.error = new Error("Connection closed unexpectedly.");
                }
            });
        }
    }
    
    private handleMessage(eventData: string): void {
        try {
            const event: StreamEvent = JSON.parse(eventData);
            console.log("Received Event: ", event); // For debugging
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

    // --- Core Event Processing Logic ---

    private processStreamEvent(draft: AgentState, streamEvent: StreamEvent): void {
        const { event, data } = streamEvent;
        const run_id = data.run_id; // The run_id is often nested inside the data object

        switch (event) {
            // --- Agent Lifecycle ---
            case 'on_chain_start':
                // This event can contain initial state like a to-do list.
                if (data?.input?.todo_list) {
                    this.processStateUpdate(draft, run_id, data.input);
                }
                break;

            case 'run_complete':
                draft.isThinking = false;
                // Clean up any "thinking" placeholders that were not used.
                draft.messages = draft.messages.filter(m => m.type !== 'thinking' || m.content);
                break;

            // --- Model Streaming ---
            case 'on_chat_model_stream':
                const chunk = data.chunk;
                // 1. Process streamed text content.
                if (chunk?.content) {
                    this.processTextChunk(draft, run_id, chunk.content);
                }
                // 2. Process the model's decision to call a tool.
                if (chunk?.tool_calls) {
                    chunk.tool_calls.forEach((toolCall: ToolCall) => {
                        this.processToolStart(draft, toolCall.id, toolCall.name);
                    });
                }
                // 3. Process streamed arguments for a tool call.
                if (chunk?.tool_call_chunks) {
                    chunk.tool_call_chunks.forEach((toolChunk: ToolCallChunk) => {
                        this.processToolChunk(draft, toolChunk);
                    });
                }
                break;
            
            // --- Generic Stream for Tool Outputs & Other Messages ---
            case 'on_chain_stream':
                if (data.chunk?.messages) {
                    data.chunk.messages.forEach((msg: ToolOutputMessage) => {
                        if (msg.type === 'tool') {
                            // This is the crucial event carrying the result of a tool execution.
                            this.processToolOutput(draft, msg);
                        }
                    });
                }
                break;

            // --- Gracefully Ignored Events ---
            // These events are useful for debugging but do not require a state update in this client design.
            // The essential data they carry is captured by other events like `on_chat_model_stream`.
            case 'on_prompt_start':
            case 'on_prompt_end':
            case 'on_chat_model_start':
            case 'on_chat_model_end':
            case 'on_tool_start': // The UI message is created earlier via `on_chat_model_stream`.
            case 'on_tool_end':   // The result is handled via the `on_chain_stream` 'tool' message.
            case 'on_chain_end':
                break;

            default:
                console.warn(`Unhandled event type: ${event}`);
                break;
        }
    }
    
    // --- Helper Functions for Processing Stream Data ---
    
    /** Finds or creates the primary response message associated with a run. */
    private findOrCreateRunMessage(draft: AgentState, run_id: string): Message {
        const message = draft.messages.find(m => m.id === run_id);
        if (message) return message;
        
        // Find the last 'thinking' placeholder and assign it this run's ID.
        const thinkingMessage = draft.messages.slice().reverse().find(m => m.type === 'thinking');
        if (thinkingMessage) {
            thinkingMessage.id = run_id;
            return thinkingMessage;
        }

        // Fallback: create a new message (should be rare).
        const newMessage = MessageFactory.createThinkingMessage();
        newMessage.id = run_id;
        draft.messages.push(newMessage);
        return newMessage;
    }

    /** Appends streamed text to the current agent response message. */
    private processTextChunk(draft: AgentState, run_id: string, content: string): void {
        const message = this.findOrCreateRunMessage(draft, run_id);

        // If the current message is a 'thinking' placeholder, morph it into a 'text' message.
        if (message.type === 'thinking') {
            const index = draft.messages.findIndex(m => m.id === message.id);
            const newMessage = MessageFactory.createTextMessage(content, run_id);
            if (index !== -1) draft.messages[index] = newMessage;
        } else if (message.type === 'text') {
            // Otherwise, just append the content.
            message.content += content;
        }
    }

    /** Creates a new 'tool_start' message when the model decides to use a tool. */
    private processToolStart(draft: AgentState, toolCallId: string, toolName: string): void {
        if (draft.messages.some(m => m.id === toolCallId)) return; // Avoid duplicates

        const toolMessage = MessageFactory.createToolStartMessage(`Calling tool: ${toolName}`, toolName, {}, toolCallId);
        draft.messages.push(toolMessage);
    }
    
    /** Buffers and parses streamed arguments for a tool call. */
    private processToolChunk(draft: AgentState, chunk: ToolCallChunk): void {
        if (!chunk.id) return;

        draft.toolArgBuffers[chunk.id] = (draft.toolArgBuffers[chunk.id] || '') + chunk.args;

        const toolMessage = draft.messages.find(m => m.id === chunk.id) as ToolStartMessage;
        if (!toolMessage || toolMessage.type !== 'tool_start') return;
        
        // Attempt to parse the buffered JSON for pretty-printing.
        try {
            const parsedArgs = JSON.parse(draft.toolArgBuffers[chunk.id]);
            toolMessage.toolInput = JSON.stringify(parsedArgs, null, 2); // Pretty print
        } catch (err) {
            // If JSON is incomplete, just show the raw buffer.
            toolMessage.toolInput = draft.toolArgBuffers[chunk.id];
        }
    }
    
    /** Processes the final output of a tool and updates the corresponding message. */
    private processToolOutput(draft: AgentState, output: ToolOutputMessage): void {
        const index = draft.messages.findIndex(m => m.id === output.tool_call_id);
        const startMessage = draft.messages[index] as ToolStartMessage;

        if (index !== -1 && startMessage?.type === 'tool_start') {
            // Morph the 'tool_start' message into a 'tool_end' message.
            const endMessage = MessageFactory.createToolEndMessage(
                startMessage.content,
                startMessage.tool,
                startMessage.toolInput,
                {
                    tool_call_id: output.tool_call_id,
                    content: typeof output.content === 'string' ? output.content : JSON.stringify(output.content, null, 2),
                    is_error: false
                },
                startMessage.id
            );
            
            // Replace the start message with the final end message.
            draft.messages[index] = endMessage;
        }
    }

    /** Updates a message to show a to-do list or other state information. */
    private processStateUpdate(draft: AgentState, run_id: string, stateData: StateData): void {
        if (!stateData.todo_list) return;

        let message = this.findOrCreateRunMessage(draft, run_id);
        
        // Morph or create a state update message.
        if (message.type !== 'state_update') {
             const index = draft.messages.findIndex(m => m.id === message.id);
             const newMessage = MessageFactory.createStateUpdateMessage('Updating plan...', {
                todo_list: stateData.todo_list,
                completed_steps: stateData.completed_steps || [],
            }, run_id);
             if (index !== -1) draft.messages[index] = newMessage;
             message = newMessage;
        }

        (message as StateUpdateMessage).state = {
            todo_list: stateData.todo_list,
            completed_steps: stateData.completed_steps || [],
        };
    }
}

export const agent = new Agent();